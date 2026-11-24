//! Shared by the Big Machines: a CarScript that drives on four roller wheels fitted for good
//! (the vanilla car simulation; the rollers sit at a crawler's idlers and sprockets), runs on
//! a truck battery and fuel, and has up to four hydraulic joints the driver works.
//!
//! Driving is scripted (TrackDrive), as tracks: the physics wheels have next to no grip and
//! only hold the machine up. Each physics step sets the ground speed along the tracks from the
//! driver's throttle, brake and gear (GetTrackSpeeds), whatever the slope, stops any sideways
//! slide, and turns the machine on the spot when steering. Parked, it holds still.
//!
//! A joint is a "user" animation source. The server steps its phase on a timer and applies it
//! at once (SetAnimationPhaseNow, so the collision moves too) and syncs it; clients animate
//! towards the synced phase (config animPeriod = 1 / speed, the same rate). Phases are saved.
class BM_Machine extends CarScript
{
	static const int MAX_JOINTS = 4;
	static ref array<float> TRACK_SPEEDS = {1.5};		//!< m/s flat out per forward gear (GetTrackSpeeds)
	static const float TRACK_ACCEL = 1.5;			//!< m/s^2 speeding up
	static const float TRACK_COAST = 2.0;			//!< m/s^2 slowing down off the throttle
	static const float TRACK_BRAKE = 4.0;			//!< m/s^2 slowing down on full brake
	static const float TRACK_TURN_RATE = 20;		//!< degrees a second, steering full lock
	static const float TRACK_TRACTION = 8.0;		//!< m/s^2 the tracks can change its speed by (0.8 g)
	static const float CLIMB_PROBE = 1.0;			//!< m up: an obstacle ahead lower than this is climbed
	static const float CLIMB_SPEED = 1.0;			//!< m/s up while climbing onto one
	static const float CLIMB_AFTER = 0.15;			//!< s pushing without getting anywhere first
	static const float CLIMB_HOLD = 0.5;			//!< s it goes on climbing once it has started
	static const float CLIMB_MAX = 0.8;				//!< m it may be lifted onto one obstacle
	static const float CLIMB_TILT = 0.866;			//!< no lifting tilted more than 30 deg (its up . world up)
	static const float FALLING = 2.0;				//!< m/s down, no roller on the ground: falling, not driving
	static const float CONTACT_DMG_MASS = 1000;		//!< knocks hurt like a car of this weight's (CarScript)
	static const int STORE_VERSION = 2;		//!< 2: the wreck it replaced (BM_Wrecks)
	static const int LIFETIME = 3888000;		//!< seconds unused before the CE removes it (45 days, as vanilla cars)

	protected static ref array<BM_Machine> s_All = new array<BM_Machine>();		//!< server: every machine

	protected ref array<string> m_JointSources = new array<string>();
	protected ref array<ref array<string>> m_JointLinked = new array<ref array<string>>();	//!< its cylinders' sources
	protected ref array<float> m_JointSpeeds = new array<float>();		//!< phase per second
	protected ref array<bool> m_JointWraps = new array<bool>();			//!< turns all the way round (slew)
	protected ref array<float> m_JointShown = new array<float>();		//!< client: last phase applied

	// Net-synced joint state (fixed fields: sync variables are registered by name)
	protected float m_J0, m_J1, m_J2, m_J3;
	protected int m_D0, m_D1, m_D2, m_D3;
	protected int m_JointLastTick;

	// Clients: the treads (TreadFrame), per side (0 = wheel_1_*, 1 = wheel_2_*)
	static const float TREAD_SHOW_DIST = 250;	//!< m from the camera: no tread animation further off
	static ref array<string> TREAD_SOURCES_1 = {"treadTop1", "treadBottom1", "treadFront1", "treadRear1"};
	static ref array<string> TREAD_SOURCES_2 = {"treadTop2", "treadBottom2", "treadFront2", "treadRear2"};
	protected float m_TreadPhase[2];
	protected float m_TreadShown[2];
	protected vector m_TreadLast[2];
	protected bool m_TreadReady;

	// The map wreck this machine took the place of (BM_Wrecks): its class or model, where it
	// was, where the machine was put down and facing which way. None for one spawned otherwise.
	protected string m_HomeMatch;
	protected vector m_HomePos;
	protected vector m_HomeBase;
	protected float m_HomeYaw;

	void BM_Machine()
	{
		m_EngineStartOK 		= "Truck_01_engine_start_SoundSet";
		m_EngineStartBattery	= "Truck_01_engine_failed_start_battery_SoundSet";
		m_EngineStartPlug 		= "Truck_01_engine_failed_start_sparkplugs_SoundSet";
		m_EngineStartFuel 		= "Truck_01_engine_failed_start_fuel_SoundSet";
		m_EngineStop 			= "Truck_01_engine_stop_SoundSet";
		m_EngineStopFuel 		= "Truck_01_engine_stop_fuel_SoundSet";

		m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Truck_01_Horn_Short_SoundSet");
		m_HornComponent.RegisterSound(VehicleHornMode.LONG, "Truck_01_Horn_SoundSet");

		RegisterNetSyncVariableFloat("m_J0", 0, 1, 3);
		RegisterNetSyncVariableFloat("m_J1", 0, 1, 3);
		RegisterNetSyncVariableFloat("m_J2", 0, 1, 3);
		RegisterNetSyncVariableFloat("m_J3", 0, 1, 3);
		RegisterNetSyncVariableInt("m_D0", -1, 1);
		RegisterNetSyncVariableInt("m_D1", -1, 1);
		RegisterNetSyncVariableInt("m_D2", -1, 1);
		RegisterNetSyncVariableInt("m_D3", -1, 1);
		SetEventMask(EntityEvent.SIMULATE);
		if (!GetGame().IsDedicatedServer())
			SetEventMask(EntityEvent.FRAME);		// the treads (TreadFrame)
	}

	//! Subclass constructors: declare joints in order (0, 1, ...). initPhase must match the
	//! source's initPhase in config.cpp. linked: sources set in step with it (its hydraulic
	//! cylinder's swing and rod slide). Two model.cfg animations must never share a source:
	//! the engine then mixes up which phase goes to which source for every source after them.
	protected void AddJoint(string source, float speed, float initPhase, bool wraps = false, array<string> linked = null)
	{
		int j = m_JointSources.Count();
		m_JointSources.Insert(source);
		ref array<string> sources = new array<string>();
		if (linked)
			sources.Copy(linked);
		m_JointLinked.Insert(sources);
		m_JointSpeeds.Insert(speed);
		m_JointWraps.Insert(wraps);
		m_JointShown.Insert(initPhase);
		SetJointPhase(j, initPhase);
	}

	// --- per machine ---

	//! The roller item class and its four slots
	string GetRollerType()
	{
		return "";
	}

	array<string> GetRollerSlots()
	{
		return null;
	}

	//! Which joint a driver's control (BM_Control) works, or -1 if it doesn't work a joint
	int ControlJoint(int control)
	{
		return -1;
	}

	//! Whether this machine has a control (BM_Control) at all
	bool HasControl(int control)
	{
		return ControlJoint(control) >= 0;
	}

	//! Server: the driver pressed (1 / -1) or let go of (0) a control
	void OnControl(int control, int dir)
	{
		JointCommand(ControlJoint(control), dir);
	}

	//! The driver's own client, as it sends a control to the server
	void OnControlLocal(int control, int dir)
	{
	}

	//! The driver is this client's player
	bool IsLocalDriver()
	{
		return !GetGame().IsDedicatedServer() && CrewMember(0) && CrewMember(0) == GetGame().GetPlayer();
	}

	// --- joints ---

	int JointCount()
	{
		return m_JointSources.Count();
	}

	float GetJointPhase(int j)
	{
		switch (j)
		{
		case 0: return m_J0;
		case 1: return m_J1;
		case 2: return m_J2;
		case 3: return m_J3;
		}
		return 0;
	}

	protected void SetJointPhase(int j, float phase)
	{
		switch (j)
		{
		case 0: m_J0 = phase; break;
		case 1: m_J1 = phase; break;
		case 2: m_J2 = phase; break;
		case 3: m_J3 = phase; break;
		}
	}

	int GetJointDir(int j)
	{
		switch (j)
		{
		case 0: return m_D0;
		case 1: return m_D1;
		case 2: return m_D2;
		case 3: return m_D3;
		}
		return 0;
	}

	protected void SetJointDir(int j, int dir)
	{
		switch (j)
		{
		case 0: m_D0 = dir; break;
		case 1: m_D1 = dir; break;
		case 2: m_D2 = dir; break;
		case 3: m_D3 = dir; break;
		}
	}

	string GetJointSource(int j)
	{
		return m_JointSources[j];
	}

	array<string> GetJointLinkedSources(int j)
	{
		return m_JointLinked[j];
	}

	//! Server: start joint j moving (1 / -1) or stop it where it is (0)
	void JointCommand(int j, int dir)
	{
		if (j < 0 || j >= JointCount())
			return;
		SetJointDir(j, Math.Clamp(dir, -1, 1));
		bool moving = false;
		for (int k = 0; k < JointCount(); k++)
		{
			if (GetJointDir(k) != 0)
				moving = true;
		}
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(JointTick);
		if (moving)
		{
			m_JointLastTick = GetGame().GetTime();
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(JointTick, 50, true);
		}
		SetSynchDirty();
	}

	protected void JointTick()
	{
		int now = GetGame().GetTime();
		float dt = (now - m_JointLastTick) * 0.001;
		m_JointLastTick = now;
		for (int j = 0; j < JointCount(); j++)
		{
			int dir = GetJointDir(j);
			if (dir == 0)
				continue;
			float phase = GetJointPhase(j) + dir * m_JointSpeeds[j] * dt;
			if (m_JointWraps[j])
			{
				phase = phase - Math.Floor(phase);
			}
			else if (phase <= 0 || phase >= 1)
			{
				phase = Math.Clamp(phase, 0, 1);
				SetJointPhase(j, phase);
				ShowJoint(j, phase, true);
				JointCommand(j, 0);		// at the end stop
				continue;
			}
			SetJointPhase(j, phase);
			ShowJoint(j, phase, true);
		}
		SetSynchDirty();
	}

	//! Animate joint j (and its cylinder) to `phase`: at once, or over the source's animPeriod
	protected void ShowJoint(int j, float phase, bool now)
	{
		if (now)
		{
			SetAnimationPhaseNow(m_JointSources[j], phase);
			foreach (string linked : m_JointLinked[j])
				SetAnimationPhaseNow(linked, phase);
		}
		else
		{
			SetAnimationPhase(m_JointSources[j], phase);
			foreach (string linkedSource : m_JointLinked[j])
				SetAnimationPhase(linkedSource, phase);
		}
	}

	//! Server: put every joint where its phase says, at once (after spawning or loading)
	protected void ApplyJoints()
	{
		for (int j = 0; j < JointCount(); j++)
			ShowJoint(j, GetJointPhase(j), true);
	}

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();
		if (GetGame().IsServer())
			return;
		for (int j = 0; j < JointCount(); j++)
		{
			float phase = GetJointPhase(j);
			// across the slew's wrap point, 1 and 0 look the same: jump rather than swing round
			ShowJoint(j, phase, m_JointWraps[j] && Math.AbsFloat(phase - m_JointShown[j]) > 0.5);
			m_JointShown[j] = phase;
		}
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);
		if (rpc_type != BM_RPC.CONTROL || !GetGame().IsServer())
			return;
		Param2<int, int> param = new Param2<int, int>(0, 0);
		if (!ctx.Read(param))
			return;
		if (!IsDriver(sender))
			return;
		OnControl(param.param1, param.param2);
	}

	//! Server: whether an RPC came from this machine's driver (only the driver works the controls)
	bool IsDriver(PlayerIdentity sender)
	{
		Human driver = CrewMember(0);
		return driver && sender && driver.GetIdentity() && driver.GetIdentity().GetId() == sender.GetId();
	}

	// --- driving ---

	//! m/s flat out in each forward gear (config Gearbox: manual, as many ratios)
	array<float> GetTrackSpeeds()
	{
		return TRACK_SPEEDS;
	}

	//! m/s flat out in reverse
	float GetTrackReverseSpeed()
	{
		return 1.2;
	}

	//! 1 in a forward gear, -1 in reverse, 0 in neutral or park
	protected int DriveDirection()
	{
		if (GearboxGetType() == CarGearboxType.AUTOMATIC)
		{
			CarAutomaticGearboxMode mode = GearboxGetMode();
			if (mode == CarAutomaticGearboxMode.D)
				return 1;
			if (mode == CarAutomaticGearboxMode.R)
				return -1;
			return 0;
		}
		int gear = GetGear();
		if (gear == CarGear.REVERSE)
			return -1;
		if (gear == CarGear.NEUTRAL)
			return 0;
		return 1;
	}

	//! m/s flat out in the gear it's in (forwards; 0 in neutral)
	float GetGearSpeed()
	{
		int dir = DriveDirection();
		if (dir < 0)
			return GetTrackReverseSpeed();
		if (dir == 0)
			return 0;
		array<float> speeds = GetTrackSpeeds();
		int index = 0;
		if (GearboxGetType() == CarGearboxType.MANUAL)
			index = Math.Clamp(GetGear() - CarGear.FIRST, 0, speeds.Count() - 1);
		return speeds[index];
	}

	//! Whether the driver drives it about (not the tower crane, which only slews)
	bool CanDrive()
	{
		return true;
	}

	//! The direction the tracks point, in world space
	vector GetTrackDirection()
	{
		return VectorToParent("0 0 1");
	}

	// --- treads ---

	//! Metres of track each tread animation cycle moves (blender/crawler.py prints it per
	//! machine); 0 for none (the tower crane)
	float GetTreadPitch()
	{
		return 0;
	}

	//! A track's middle in model space (side 0: wheel_1_*, 1: wheel_2_*), where the treads
	//! are now (an excavator's tracks turn back by its slew)
	vector GetTrackCentreLS(int side)
	{
		string s = (side + 1).ToString();
		return (GetMemoryPointPos("wheel_" + s + "_1") + GetMemoryPointPos("wheel_" + s + "_2")) * 0.5;
	}

	override void EOnFrame(IEntity other, float timeSlice)
	{
		super.EOnFrame(other, timeSlice);
		TreadFrame();
	}

	//! Clients, every frame: run each track's treads by how far that side of the machine moved
	//! along the tracks since the last frame, so they keep pace with the ground (and run
	//! opposite ways turning on the spot). The animations loop: phase 1 looks like phase 0.
	protected void TreadFrame()
	{
		float pitch = GetTreadPitch();
		if (pitch <= 0)
			return;
		vector dir = GetTrackDirection();
		bool show = vector.DistanceSq(GetGame().GetCurrentCameraPosition(), GetPosition()) < TREAD_SHOW_DIST * TREAD_SHOW_DIST;
		for (int side = 0; side < 2; side++)
		{
			vector pos = ModelToWorld(GetTrackCentreLS(side));
			if (m_TreadReady)
			{
				float moved = vector.Dot(pos - m_TreadLast[side], dir);
				if (Math.AbsFloat(moved) < 2)		// not a teleport
				{
					float phase = m_TreadPhase[side] + moved / pitch;
					m_TreadPhase[side] = phase - Math.Floor(phase);
				}
			}
			m_TreadLast[side] = pos;
			if (show && Math.AbsFloat(m_TreadPhase[side] - m_TreadShown[side]) > 0.002)
				ShowTread(side, m_TreadPhase[side]);
		}
		m_TreadReady = true;
	}

	float GetTreadPhase(int side)
	{
		return m_TreadPhase[side];
	}

	//! Tests: hold a side's treads at this phase until the machine moves
	void ShowTreadAt(int side, float phase)
	{
		m_TreadPhase[side] = phase;
		ShowTread(side, phase);
	}

	protected void ShowTread(int side, float phase)
	{
		m_TreadShown[side] = phase;
		array<string> sources = TREAD_SOURCES_1;
		if (side == 1)
			sources = TREAD_SOURCES_2;
		for (int i = 0; i < sources.Count(); i++)
			SetAnimationPhaseNow(sources[i], phase);
	}

	//! While true, steering doesn't turn it (an excavator slewing turns the machine itself)
	protected bool TrackTurnHeld()
	{
		return false;
	}

	//! m from the origin to the front (or back) of what leads it along the tracks: the
	//! climbing probe starts there (TrackDrive)
	float GetTrackReach(bool forwards)
	{
		return 2.0;
	}

	//! Whether what the tracks are pushing against is low enough to climb: nothing in the way
	//! CLIMB_PROBE up, just ahead. A wall, a building or a car is pushed, not climbed
	protected bool CanClimbAhead(vector dir, bool forwards)
	{
		vector up = VectorToParent("0 1 0");
		float reach = GetTrackReach(forwards);
		vector from = GetPosition() + dir * (reach - 0.3) + up * CLIMB_PROBE;
		vector to = from + dir * 1.5;
		vector hit, normal;
		int comp;
		set<Object> results = new set<Object>();
		return !DayZPhysics.RaycastRV(from, to, hit, normal, comp, results, null, this, false, false, ObjIntersectGeom);
	}

	//! A machine that can't drive, each step (the tower crane levels itself)
	protected void HoldStill(vector up, vector spin)
	{
	}

	static float MoveTowards(float from, float to, float step)
	{
		if (from < to)
			return Math.Min(from + step, to);
		return Math.Max(from - step, to);
	}

	//! Each physics step, wherever the machine is simulated (the server, and the driver's client
	//! predicting it)
	override void EOnSimulate(IEntity other, float dt)
	{
		super.EOnSimulate(other, dt);
		if (!IsProxy() && dt > 0)
			TrackDrive(dt);
	}

	protected void TrackDrive(float dt)
	{
		// Only a fall is left to the physics. Up on a rock with the rollers off the ground, the
		// tracks still bear on it and drive on (the rollers' contact alone would leave it stuck)
		bool contact = false;
		for (int w = 0; w < WheelCount(); w++)
		{
			if (WheelHasContact(w))
				contact = true;
		}
		vector vel = GetVelocity(this);
		vector track = GetTrackDirection();
		// Speed along the tracks, less what gravity added last step: the drive holds its speed
		// on a slope, and holds it still there
		float speed = vector.Dot(vel, track) + 9.81 * track[1] * dt;
		if (!contact && vel[1] < -FALLING)
		{
			m_Belt = speed;
			return;
		}

		bool crewed = CrewMember(0) != null && CanDrive();
		float throttle = 0;
		float brake = 1;	// nobody aboard (or nothing to drive): hold it where it is
		float steer = 0;
		int dir = 0;
		float flatOut = 0;
		// The controls as they stand now: on the server, OnInput sees the driver's from the
		// step before they arrive
		if (crewed)
		{
			brake = Math.Max(GetBrake(), GetHandbrake());
			steer = GetSteering();
			if (EngineIsOn())
			{
				throttle = GetThrottle();
				dir = DriveDirection();
				flatOut = GetGearSpeed();
			}
		}

		vector up = VectorToParent("0 1 0");
		float target = throttle * flatOut * dir;
		float rate = TRACK_COAST;
		if (brake > 0.05)
		{
			target = 0;
			rate = TRACK_BRAKE * brake;
		}
		else if (target * m_Belt >= 0 && Math.AbsFloat(target) > Math.AbsFloat(m_Belt))
		{
			rate = TRACK_ACCEL;
		}
		// The tracks turn at their own speed, whatever the machine is doing; the machine is
		// pulled towards it with the tracks' grip. Against a rock it shoves hard (and the rock
		// meets the ramped track ends, which lift it over) instead of asking a little more
		// speed of a machine that isn't moving
		m_Belt = MoveTowards(m_Belt, target, rate * dt);
		float moving = speed;
		speed = MoveTowards(speed, m_Belt, TRACK_TRACTION * dt);
		// along the tracks, plus whatever the suspension is doing; nothing sideways
		float rise = vector.Dot(vel, up);
		// Pushing and getting nowhere: tracks ride up onto a rock, a log, a kerb, if it's low
		if (Math.AbsFloat(m_Belt) > 0.3 && Math.AbsFloat(moving) < 0.3 * Math.AbsFloat(m_Belt))
			m_Blocked += dt;
		else
			m_Blocked = 0;
		// Once started it goes on a moment, or it would stop as soon as it moved and stall again.
		// Never more than CLIMB_MAX onto one thing, nor tilted steeply: a rock, not a cliff
		bool lifting = false;
		if ((m_Blocked > CLIMB_AFTER || m_Climbing > 0) && m_Climbed < CLIMB_MAX && up[1] > CLIMB_TILT)
		{
			bool forwards = m_Belt > 0;
			vector ahead = track;
			if (!forwards)
				ahead = -track;
			if (Math.AbsFloat(m_Belt) > 0.3 && CanClimbAhead(ahead, forwards))
			{
				if (m_Blocked > CLIMB_AFTER)
					m_Climbing = CLIMB_HOLD;
				if (rise < CLIMB_SPEED)
				{
					m_Climbed += (CLIMB_SPEED - Math.Max(rise, 0)) * dt;
					rise = CLIMB_SPEED;
				}
				lifting = true;
			}
		}
		if (lifting)
		{
			m_Climbing -= dt;
			m_ClimbRest = 0;
		}
		else
		{
			m_Climbing = 0;
			m_ClimbRest += dt;
			if (m_ClimbRest > 1.0)
				m_Climbed = 0;
		}
		vector newVel = track * speed + up * rise;
		if (vector.DistanceSq(newVel, vel) > 0.000001)
			SetVelocity(this, newVel);

		vector spin = dBodyGetAngularVelocity(this);
		if (!CanDrive())
		{
			HoldStill(up, spin);
			return;
		}

		// Turning on the spot, the way tracks do; steers like a car's wheels (backing up, right
		// swings the front left)
		if (TrackTurnHeld())
			return;
		float yaw = steer * TRACK_TURN_RATE * Math.DEG2RAD;
		if (speed < -0.05 || target < 0)
			yaw = -yaw;
		float spinUp = vector.Dot(spin, up);
		if (Math.AbsFloat(spinUp - yaw) > 0.0001)
			dBodySetAngularVelocity(this, spin + up * (yaw - spinUp));
	}

	// --- knocks ---

	protected float m_Belt;		//!< the tracks' own speed, m/s along them (TrackDrive)
	protected float m_Blocked;	//!< s the tracks have been pushing without the machine moving
	protected float m_Climbing;	//!< s left climbing onto an obstacle
	protected float m_Climbed;	//!< m lifted onto the obstacle in hand (CLIMB_MAX)
	protected float m_ClimbRest;	//!< s since it last climbed: a new obstacle after a while
	protected float m_ContactCoefBase = -1;		//!< vanilla's m_dmgContactCoef, before scaling

	//! Vanilla's crash damage goes by momentum: a 14 t machine nudging a rock at walking pace
	//! counted as a hard crash, damaging it and knocking its driver out (shock 50 a knock).
	//! Scaled to the mass, knocks hurt as they would a car of CONTACT_DMG_MASS at the same
	//! change of speed: real crashes and falls, not rocks.
	override void CheckContactCache()
	{
		float mass = dBodyGetMass(this);
		if (m_ContactCoefBase < 0)
			m_ContactCoefBase = m_dmgContactCoef;
		if (mass > CONTACT_DMG_MASS)
			m_dmgContactCoef = m_ContactCoefBase * CONTACT_DMG_MASS / mass;
		super.CheckContactCache();
	}

	//! Vanilla already scales crew damage to a 1000 kg car's (change of speed), and the scaling
	//! above would make it tiny again: undo that here, so the crew get what a car's would
	override void DamageCrew(float dmg)
	{
		float mass = dBodyGetMass(this);
		if (mass > CONTACT_DMG_MASS)
			dmg = dmg * mass / CONTACT_DMG_MASS;
		super.DamageCrew(dmg);
	}

	// --- home: the wreck it replaced ---

	//! Server: every machine in the world
	static array<BM_Machine> GetAll()
	{
		return s_All;
	}

	void SetHome(string match, vector pos, vector base, float yaw)
	{
		m_HomeMatch = match;
		m_HomePos = pos;
		m_HomeBase = base;
		m_HomeYaw = yaw;
	}

	bool HasHome()
	{
		return m_HomeMatch != "";
	}

	string GetHomeMatch()
	{
		return m_HomeMatch;
	}

	vector GetHomePos()
	{
		return m_HomePos;
	}

	vector GetHomeBase()
	{
		return m_HomeBase;
	}

	float GetHomeYaw()
	{
		return m_HomeYaw;
	}

	//! Server, after spawning one by script: script-spawned vehicles get a 3 s lifetime and
	//! the CE cleanup deletes them
	void KeepAround()
	{
		SetLifetimeMax(LIFETIME);
		SetLifetime(LIFETIME);
	}

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(STORE_VERSION);
		ctx.Write(JointCount());
		for (int j = 0; j < JointCount(); j++)
			ctx.Write(GetJointPhase(j));
		ctx.Write(m_HomeMatch);
		ctx.Write(m_HomePos);
		ctx.Write(m_HomeBase);
		ctx.Write(m_HomeYaw);
	}

	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;
		int ours, count;
		if (!ctx.Read(ours) || !ctx.Read(count))
			return false;
		for (int j = 0; j < count; j++)
		{
			float phase;
			if (!ctx.Read(phase))
				return false;
			if (j < JointCount())
				SetJointPhase(j, phase);
		}
		if (ours >= 2)
		{
			if (!ctx.Read(m_HomeMatch) || !ctx.Read(m_HomePos) || !ctx.Read(m_HomeBase) || !ctx.Read(m_HomeYaw))
				return false;
		}
		return true;
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		// The wreck it replaced is back on the map after a restart, where the machine may still
		// stand: hide it now, before anything moves, or the physics shoves the machine out of it
		if (GetGame().IsServer() && HasHome() && !IsRuined())
			BM_Wrecks.Hide(m_HomeMatch, m_HomePos);
		ApplyJoints();
		SetSynchDirty();
	}

	override void EEInit()
	{
		super.EEInit();
		if (GetGame().IsServer())
		{
			if (s_All.Find(this) < 0)
				s_All.Insert(this);
			ApplyJoints();
			// After a load the rollers are already there; FitRollers only fills empty slots
			GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(FitRollers, 100, false);
		}
	}

	override void EEDelete(EntityAI parent)
	{
		s_All.RemoveItem(this);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(JointTick);
		super.EEDelete(parent);
	}

	// --- rollers ---

	//! The four physics wheels, if any slot is empty
	void FitRollers()
	{
		array<string> slots = GetRollerSlots();
		if (!slots)
			return;
		foreach (string slot : slots)
		{
			if (!FindAttachmentBySlotName(slot))
				GetInventory().CreateAttachmentEx(GetRollerType(), InventorySlots.GetSlotIdFromString(slot));
		}
	}

	bool IsRollerSlot(int slotId)
	{
		array<string> slots = GetRollerSlots();
		if (!slots)
			return false;
		foreach (string slot : slots)
		{
			if (InventorySlots.GetSlotIdFromString(slot) == slotId)
				return true;
		}
		return false;
	}

	override bool CanReleaseAttachment(EntityAI attachment)
	{
		if (attachment && attachment.IsKindOf(GetRollerType()))
			return false;
		if (!super.CanReleaseAttachment(attachment))
			return false;
		if (EngineIsOn() && attachment.GetType() == "TruckBattery")
			return false;
		return true;
	}

	override bool CanDisplayAttachmentSlot(int slot_id)
	{
		if (IsRollerSlot(slot_id))
			return false;
		return super.CanDisplayAttachmentSlot(slot_id);
	}

	// --- seat ---

	override int GetAnimInstance()
	{
		return VehicleAnimInstances.V3S;
	}

	override int GetSeatAnimationType(int posIdx)
	{
		return DayZPlayerConstants.VEHICLESEAT_DRIVER;
	}

	override bool CrewCanGetThrough(int posIdx)
	{
		return true;	// no door items: open canopy, or a cab door that isn't modelled as one
	}

	override bool CanReachSeatFromSeat(int currentSeat, int nextSeat)
	{
		return false;
	}

	override bool CanReachDoorsFromSeat(string pDoorsSelection, int pCurrentSeat)
	{
		return false;
	}

	override float GetWeightCoef()
	{
		return 3.0;
	}

	// --- engine: a diesel that needs a truck battery and fuel, nothing else ---

	override bool NeedElectricitySourceDevice()
	{
		return true;
	}

	override EntityAI GetElectricitySourceDevice()
	{
		super.GetElectricitySourceDevice();
		return GetInventory().FindAttachment(TruckBattery.SLOT_ID);
	}

	override string GetElectricitySourceDeviceType()
	{
		return "TruckBattery";
	}

	override bool IsVitalSparkPlug()
	{
		return false;
	}

	override bool IsVitalGlowPlug()
	{
		return false;
	}

	override bool IsVitalEngineBelt()
	{
		return false;
	}

	override bool IsVitalRadiator()
	{
		return false;
	}

	override void OnDebugSpawn()
	{
		FitRollers();
		if (!GetInventory().FindAttachment(TruckBattery.SLOT_ID))
			GetInventory().CreateAttachment("TruckBattery");
		FillUpCarFluids();
	}
}
