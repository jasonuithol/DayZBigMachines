//! Combine harvester: drives on its own big front wheels on the car simulation (no scripted
//! tracks). It steers with its back wheels, which the car simulation can't do (a negative
//! steering angle crashes the game): SteerBack turns the machine each physics step as back-wheel
//! steering would, and every client turns the back wheels for show.
//!
//! The driver raises and lowers the header (BM_Control.RAISE: PageUp / PageDown), swings the
//! unloading auger out and in (STICK: Home / End) and starts and stops the header (BUCKET:
//! Insert / Delete; only with the engine running).
//!
//! While the header runs, the reel and the header's auger spin on every client, and anything
//! alive the lowered header reaches - zombies, animals, players other than the driver - is
//! killed (CatchTick, on the server).
class BM_Combine extends BM_Machine
{
	static ref array<string> WHEEL_SLOTS = {"BM_Combine_Wheel_1_1", "BM_Combine_Wheel_2_1", "BM_Combine_Wheel_1_2", "BM_Combine_Wheel_2_2"};
	static const float REEL_TURNS = 0.7;			//!< turns a second, header running
	static const float HEADER_AUGER_TURNS = 2.5;
	static const float CATCH_INTERVAL = 0.1;		//!< s between the server's checks
	static const float CATCH_LOWERED = 0.6;			//!< header phase: lower than this catches
	static const float CATCH_BEHIND = 1.9;			//!< m back from the cutter bar the header reaches
	static const float CATCH_AHEAD = 0.5;			//!< m in front of it (the reel's tines)
	static const float CATCH_BELOW = 0.6;			//!< m below the catch line...
	static const float CATCH_ABOVE = 1.4;			//!< ...and above it
	static const float STEER_MAX = 35;			//!< degrees the back wheels turn, full lock
	static const float WHEELBASE = 4.0;			//!< m, front axle to back (blender/build_combine.py)
	static const float SIDE_GRIP = 0.5;			//!< of the sideways slide taken out each step

	protected bool m_HeaderOn;			//!< synced: the header is running
	protected float m_ReelPhase;		//!< clients
	protected float m_HeaderAugerPhase;

	void BM_Combine()
	{
		m_enginePtcPos = "0 2.9 -2.8";
		SetEnginePos("0 2.9 -2.8");
		// Speeds and starting phases: blender/build_combine.py (JOINTS) and config.cpp
		AddJoint("header", 0.30, 1.0);
		AddJoint("auger", 0.12, 0.0);
		RegisterNetSyncVariableBool("m_HeaderOn");
	}

	override bool HasTracks()
	{
		return false;
	}

	override string GetRollerType()
	{
		return "BM_CombineWheelFront";
	}

	override string GetRollerTypeFor(string slot)
	{
		if (slot.Substring(slot.Length() - 2, 2) == "_2")		// the back wheels: wheel_<side>_2
			return "BM_CombineWheelRear";
		return "BM_CombineWheelFront";
	}

	override bool IsRoller(EntityAI item)
	{
		return item && (item.IsKindOf("BM_CombineWheelFront") || item.IsKindOf("BM_CombineWheelRear"));
	}

	override array<string> GetRollerSlots()
	{
		return WHEEL_SLOTS;
	}

	override int ControlJoint(int control)
	{
		switch (control)
		{
		case BM_Control.RAISE:	return 0;
		case BM_Control.STICK:	return 1;
		}
		return -1;
	}

	override bool HasControl(int control)
	{
		return control == BM_Control.BUCKET || super.HasControl(control);
	}

	override void OnControl(int control, int dir)
	{
		if (control != BM_Control.BUCKET)
		{
			super.OnControl(control, dir);
			return;
		}
		if (dir > 0)
			SetHeaderOn(true);
		else if (dir < 0)
			SetHeaderOn(false);
	}

	// --- steering with the back wheels ---

	override void EOnSimulate(IEntity other, float dt)
	{
		super.EOnSimulate(other, dt);
		if (!IsProxy() && dt > 0)
			SteerBack(dt);
	}

	//! Server and the driver's client (which predicts it), each physics step: turn at the rate
	//! the back wheels' angle gives at this speed (a bicycle model: speed x tan(angle) /
	//! wheelbase; + yaw = right), and stop the tyres sliding sideways. Only on the ground.
	protected void SteerBack(float dt)
	{
		bool contact = false;
		for (int w = 0; w < WheelCount(); w++)
		{
			if (WheelHasContact(w))
				contact = true;
		}
		if (!contact)
			return;
		vector vel = GetVelocity(this);
		vector forward = VectorToParent("0 0 1");
		vector up = VectorToParent("0 1 0");
		vector side = VectorToParent("1 0 0");
		float speed = vector.Dot(vel, forward);
		float yaw = GetSteering() * speed * Math.Tan(STEER_MAX * Math.DEG2RAD) / WHEELBASE;
		vector spin = dBodyGetAngularVelocity(this);
		spin = spin + up * (yaw - vector.Dot(spin, up));
		dBodySetAngularVelocity(this, spin);
		float slide = vector.Dot(vel, side);
		SetVelocity(this, vel - side * (slide * SIDE_GRIP));
	}

	// --- the header running ---

	bool IsHeaderOn()
	{
		return m_HeaderOn;
	}

	//! Server: start (with the engine running) or stop the header
	void SetHeaderOn(bool on)
	{
		on = on && EngineIsOn();
		if (on == m_HeaderOn)
			return;
		m_HeaderOn = on;
		SetSynchDirty();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(CatchTick);
		if (on)
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(CatchTick, CATCH_INTERVAL * 1000, true);
	}

	override void OnEngineStop()
	{
		super.OnEngineStop();
		if (GetGame().IsServer())
			SetHeaderOn(false);
	}

	//! Server, while the header runs: kill whatever alive the lowered header reaches
	protected void CatchTick()
	{
		if (!m_HeaderOn || IsRuined())
		{
			SetHeaderOn(false);
			return;
		}
		if (GetJointPhase(0) > CATCH_LOWERED)
			return;
		vector left = GetMemoryPointPos("header_catch_l");
		vector right = GetMemoryPointPos("header_catch_r");
		float x0 = Math.Min(left[0], right[0]);
		float x1 = Math.Max(left[0], right[0]);
		float bar = left[2];				// the cutter bar, along the machine (+ forwards)
		float line = left[1];
		vector centre = ModelToWorld(Vector(0, line, bar - CATCH_BEHIND * 0.5));
		array<Object> objects = new array<Object>();
		GetGame().GetObjectsAtPosition3D(centre, (x1 - x0) * 0.5 + CATCH_BEHIND, objects, null);
		foreach (Object o : objects)
		{
			EntityAI victim = EntityAI.Cast(o);
			if (!victim || !victim.IsAlive() || !CanCatch(victim))
				continue;
			vector p = WorldToModel(victim.GetPosition());
			if (p[0] < x0 || p[0] > x1)
				continue;
			if (p[2] < bar - CATCH_BEHIND || p[2] > bar + CATCH_AHEAD)
				continue;
			if (p[1] < line - CATCH_BELOW - CATCH_ABOVE || p[1] > line + CATCH_ABOVE)
				continue;
			Catch(victim);
		}
	}

	//! Zombies, animals, and players other than those aboard
	protected bool CanCatch(EntityAI e)
	{
		if (e.IsInherited(DayZInfected) || e.IsInherited(AnimalBase))
			return true;
		PlayerBase player = PlayerBase.Cast(e);
		return player && player.GetParent() != this;
	}

	protected void Catch(EntityAI victim)
	{
		Print("[BigMachines] the combine's header caught " + victim.GetType() + " at " + victim.GetPosition());
		victim.SetHealth("", "", 0);
	}

	// --- clients: the reel and the header's auger spin while it runs ---

	override void EOnFrame(IEntity other, float timeSlice)
	{
		super.EOnFrame(other, timeSlice);
		// the back wheels: turned the other way to the turn
		float steer = GetSteering();
		SetAnimationPhaseNow("steerBackLeft", steer);
		SetAnimationPhaseNow("steerBackRight", steer);
		if (!m_HeaderOn)
			return;
		m_ReelPhase = m_ReelPhase + REEL_TURNS * timeSlice;
		m_ReelPhase = m_ReelPhase - Math.Floor(m_ReelPhase);
		m_HeaderAugerPhase = m_HeaderAugerPhase + HEADER_AUGER_TURNS * timeSlice;
		m_HeaderAugerPhase = m_HeaderAugerPhase - Math.Floor(m_HeaderAugerPhase);
		SetAnimationPhaseNow("reel", m_ReelPhase);
		SetAnimationPhaseNow("headerAuger", m_HeaderAugerPhase);
	}

	override void EEDelete(EntityAI parent)
	{
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(CatchTick);
		super.EEDelete(parent);
	}

	override float GetTransportCameraDistance()
	{
		return 14.0;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 4 0";
	}
}
