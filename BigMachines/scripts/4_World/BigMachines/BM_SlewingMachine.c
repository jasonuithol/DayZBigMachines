//! A machine whose upper part slews: the excavator's house, the tower crane's top. DayZ keeps a
//! seated player where the seat is in the modelled pose, so the part with the seat can't turn
//! on the model: the whole machine turns instead (an excavator then turns its tracks back, see
//! GetSlewSource). m_Slew is the angle turned. The server turns the machine and syncs m_Slew;
//! the driver's client turns it in step (see SlewSpin).
//!
//! Moving. The physics wheels have next to no grip and only hold the machine up. Each physics
//! step TrackDrive sets the ground speed along the tracks from the driver's throttle, brake and
//! gear, stops any sideways slide, and turns the machine on the spot when steering; a machine
//! that can't drive (CanDrive) is held still.
class BM_SlewingMachine extends BM_Machine
{
	static const float TRACK_SPEED = 1.53;			//!< m/s flat out forwards (5.5 km/h)
	static const float TRACK_SPEED_REVERSE = 1.2;	//!< m/s flat out backwards
	static const float TRACK_ACCEL = 1.5;			//!< m/s^2 speeding up
	static const float TRACK_COAST = 2.0;			//!< m/s^2 slowing down off the throttle
	static const float TRACK_BRAKE = 4.0;			//!< m/s^2 slowing down on full brake
	static const float TRACK_TURN_RATE = 20;		//!< degrees a second, steering full lock
	static const float LEVEL_RATE = 4;				//!< a machine that can't drive levels itself: 1/s

	static const float SLEW_RATE = 36;			//!< degrees a second
	static const float SLEW_SETTLE_SECS = 0.5;	//!< after letting go, heading changes still count

	protected float m_Slew;				//!< synced: degrees, -180 .. 180, + = turned right
	protected int m_SlewDir;			//!< synced: 1 left, -1 right, 0 still (server's view)
	protected int m_SlewLocalDir;		//!< the driver's own client: what its keys say, at once
	protected float m_SlewShown;		//!< last slew applied to the slew animation here
	protected float m_SlewSettle;		//!< driver's client: seconds before following the server again
	protected int m_SlewLastTick;		//!< server, nobody driving: last timer tick
	protected float m_SlewLastYaw;		//!< driver's client: heading at the last step
	protected bool m_SlewTurning;		//!< spinning at the last step
	protected float m_SlewCounting;		//!< seconds left counting heading changes as slew

	void BM_SlewingMachine()
	{
		RegisterNetSyncVariableFloat("m_Slew", -180, 180, 2);
		RegisterNetSyncVariableInt("m_SlewDir", -1, 1);
		SetEventMask(EntityEvent.SIMULATE);
	}

	override bool HasControl(int control)
	{
		return control == BM_Control.SLEW || super.HasControl(control);
	}

	//! Degrees a second
	float GetSlewRate()
	{
		return SLEW_RATE;
	}

	// --- slew ---

	float GetSlew()
	{
		return m_Slew;
	}

	static float WrapDegrees(float deg)
	{
		while (deg > 180)
			deg -= 360;
		while (deg < -180)
			deg += 360;
		return deg;
	}

	//! The animation source that turns something back by the slew ("" for none: the tower
	//! crane's top just turns on its mast); phase 0.5 = no slew
	string GetSlewSource()
	{
		return "";
	}

	protected void ShowSlew(bool now)
	{
		string source = GetSlewSource();
		if (source == "")
			return;
		float phase = 0.5 + m_Slew / 360;
		// across the wrap point, -180 and 180 look the same: jump rather than swing round
		if (now || Math.AbsFloat(m_Slew - m_SlewShown) > 180)
			SetAnimationPhaseNow(source, phase);
		else
			SetAnimationPhase(source, phase);
		m_SlewShown = m_Slew;
	}

	//! Nobody aboard: turn the machine (house) by dir * rate * dt with a transform change
	protected void SlewStep(int dir, float dt)
	{
		float delta = -dir * GetSlewRate() * dt;	// left (+1) lowers the heading
		vector ori = GetOrientation();
		ori[0] = ori[0] + delta;
		SetOrientation(ori);
		m_Slew = WrapDegrees(m_Slew + delta);
		ShowSlew(true);
	}

	//! A driver aboard: the server owns the physics and the driver's client predicts them, so
	//! both spin the body with the same angular velocity (a transform change would be undone)
	//! and count the heading change that actually happened as slew.
	protected void SlewSpin(int dir, float dt)
	{
		float yaw = GetOrientation()[0];
		if (m_SlewCounting > 0)
		{
			m_Slew = WrapDegrees(m_Slew + WrapDegrees(yaw - m_SlewLastYaw));
			ShowSlew(true);
			m_SlewCounting -= dt;
		}
		m_SlewLastYaw = yaw;
		if (dir != 0)
		{
			dBodySetAngularVelocity(this, Vector(0, -dir * GetSlewRate() * Math.DEG2RAD, 0));	// + = right
			m_SlewCounting = SLEW_SETTLE_SECS;
			m_SlewTurning = true;
		}
		else if (m_SlewTurning)
		{
			// let go: stop the spin dead, and go on counting while it settles
			dBodySetAngularVelocity(this, vector.Zero);
			m_SlewTurning = false;
		}
	}

	override void OnControl(int control, int dir)
	{
		if (control != BM_Control.SLEW)
		{
			super.OnControl(control, dir);
			return;
		}
		m_SlewDir = Math.Clamp(dir, -1, 1);
		SetSynchDirty();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(ServerSlewTick);
		m_SlewLastTick = GetGame().GetTime();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ServerSlewTick, 20, true);
	}

	//! Server, while slewing and until the last step after letting go
	protected void ServerSlewTick()
	{
		int now = GetGame().GetTime();
		float dt = (now - m_SlewLastTick) * 0.001;
		m_SlewLastTick = now;
		if (CrewMember(0))
		{
			SlewSpin(m_SlewDir, dt);
		}
		else
		{
			m_SlewTurning = false;
			m_SlewCounting = 0;
			if (m_SlewDir != 0)
				SlewStep(m_SlewDir, dt);
		}
		SetSynchDirty();
		if (m_SlewDir == 0 && m_SlewCounting <= 0)
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(ServerSlewTick);
	}

	override void OnControlLocal(int control, int dir)
	{
		if (control == BM_Control.SLEW)
			m_SlewLocalDir = Math.Clamp(dir, -1, 1);
	}

	//! The driver's client: spin as the server does, at once (its physics predict the server's)
	override void OnInput(float dt)
	{
		super.OnInput(dt);
		if (!GetGame().IsServer() && IsLocalDriver())
		{
			SlewSpin(m_SlewLocalDir, dt);
			if (m_SlewLocalDir != 0)
				m_SlewSettle = 1.0;
			else if (m_SlewSettle > 0)
				m_SlewSettle -= dt;
		}
	}

	// --- driving ---

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

	//! Whether the driver drives it about (the excavator) or it only slews (the tower crane)
	bool CanDrive()
	{
		return true;
	}

	//! The direction the tracks point, in world space (the house's forward turned back by m_Slew)
	vector GetTrackDirection()
	{
		float s = m_Slew * Math.DEG2RAD;
		return VectorToParent(Vector(-Math.Sin(s), 0, Math.Cos(s)));
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
		int contact = 0;
		for (int w = 0; w < WheelCount(); w++)
		{
			if (WheelHasContact(w))
				contact++;
		}
		if (contact < 2)
			return;		// in the air: leave it to the physics

		bool crewed = CrewMember(0) != null && CanDrive();
		float throttle = 0;
		float brake = 1;	// nobody aboard (or nothing to drive): hold it where it is
		float steer = 0;
		int dir = 0;
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
			}
		}

		vector up = VectorToParent("0 1 0");
		vector track = GetTrackDirection();
		vector vel = GetVelocity(this);
		// Speed along the tracks, less what gravity added last step: the drive holds its speed
		// on a slope, and holds it still there
		float speed = vector.Dot(vel, track) + 9.81 * track[1] * dt;
		float target = throttle * TRACK_SPEED;
		if (dir < 0)
			target = -throttle * TRACK_SPEED_REVERSE;
		else if (dir == 0)
			target = 0;
		float rate = TRACK_COAST;
		if (brake > 0.05)
		{
			target = 0;
			rate = TRACK_BRAKE * brake;
		}
		else if (target * speed >= 0 && Math.AbsFloat(target) > Math.AbsFloat(speed))
		{
			rate = TRACK_ACCEL;
		}
		speed = MoveTowards(speed, target, rate * dt);
		// along the tracks, plus whatever the suspension is doing; nothing sideways
		vector newVel = track * speed + up * vector.Dot(vel, up);
		if (vector.DistanceSq(newVel, vel) > 0.000001)
			SetVelocity(this, newVel);

		vector spin = dBodyGetAngularVelocity(this);
		if (!CanDrive())
		{
			// A machine that only slews (the tower crane's top, on its mast) stays level: turn
			// it back upright, keeping only the slew's turn about the vertical
			vector worldUp = "0 1 0";
			vector level = (up * worldUp) * LEVEL_RATE;		// cross product: the axis to tip back about
			if (m_SlewTurning || m_SlewCounting > 0)
				level = level + worldUp * vector.Dot(spin, worldUp);
			if (vector.DistanceSq(level, spin) > 0.000001)
				dBodySetAngularVelocity(this, level);
			return;
		}

		// Turning: the tracks don't skid round by themselves, and steer like a car's wheels
		// (backing up, right swings the front left). Slewing turns the machine itself.
		if (m_SlewTurning || m_SlewCounting > 0)
			return;
		float yaw = steer * TRACK_TURN_RATE * Math.DEG2RAD;
		if (speed < -0.05 || target < 0)
			yaw = -yaw;
		float spinUp = vector.Dot(spin, up);
		if (Math.AbsFloat(spinUp - yaw) > 0.0001)
			dBodySetAngularVelocity(this, spin + up * (yaw - spinUp));
	}

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();
		// The driver's client shows its own count while turning; then it, like everyone else,
		// follows the server
		if (!GetGame().IsServer() && (!IsLocalDriver() || m_SlewSettle <= 0))
			ShowSlew(false);
	}

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(m_Slew);
	}

	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;
		return ctx.Read(m_Slew);
	}

	override void EEInit()
	{
		super.EEInit();
		ShowSlew(true);
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		ShowSlew(true);
	}

	override void EEDelete(EntityAI parent)
	{
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(ServerSlewTick);
		super.EEDelete(parent);
	}

}
