//! Crawler excavator: the driver sits in the cab and works the boom (BM_Control.RAISE:
//! PageUp / PageDown), stick (STICK: Home / End) and bucket (BUCKET: Insert / Delete), and
//! slews (SLEW: left / right arrows). Driving: BM_Machine.
//!
//! Slewing. DayZ keeps a seated player where the seat is in the modelled pose, so the house
//! (cab, driver, arm) can't turn on the model. Instead the whole machine turns, and the
//! undercarriage bone (tracks, rollers) turns back by the same angle so the tracks stay where
//! they were. m_Slew is that angle: the house's heading minus the tracks'. The server turns
//! the machine and syncs m_Slew; the driver's client turns it in step (see SlewSpin).
//! The physics wheels stay under the house, so after a slew it drives the way the cab faces.
class BM_Excavator extends BM_Machine
{
	static const float SLEW_RATE = 36;			//!< degrees a second
	static const float SLEW_SETTLE_SECS = 0.5;	//!< after letting go, heading changes still count
	static const string SLEW_SOURCE = "slew";	//!< undercarriage animation: phase 0.5 = no slew
	static ref array<string> ROLLER_SLOTS = {"BM_Exc_Roller_1_1", "BM_Exc_Roller_1_2", "BM_Exc_Roller_2_1", "BM_Exc_Roller_2_2"};

	protected float m_Slew;				//!< synced: degrees, -180 .. 180, + = house turned right of the tracks
	protected int m_SlewDir;			//!< synced: 1 left, -1 right, 0 still (server's view)
	protected int m_SlewLocalDir;		//!< the driver's own client: what its keys say, at once
	protected float m_SlewShown;		//!< last slew applied to the undercarriage here
	protected float m_SlewSettle;		//!< driver's client: seconds before following the server again
	protected int m_SlewLastTick;		//!< server, nobody driving: last timer tick
	protected float m_SlewLastYaw;		//!< driver's client: heading at the last step
	protected bool m_SlewTurning;		//!< spinning at the last step
	protected float m_SlewCounting;		//!< seconds left counting heading changes as slew

	void BM_Excavator()
	{
		m_enginePtcPos = "0 2.1 -1.0";
		SetEnginePos("0 1.6 -1.0");
		// Speeds and starting phases: blender/build_excavator.py (JOINTS) and config.cpp
		AddJoint("boom", 0.20, 0.5385);
		AddJoint("stick", 0.20, 0.5294);
		AddJoint("bucket", 0.25, 0.56);
		RegisterNetSyncVariableFloat("m_Slew", -180, 180, 2);
		RegisterNetSyncVariableInt("m_SlewDir", -1, 1);
	}

	override string GetRollerType()
	{
		return "BM_ExcavatorRoller";
	}

	override array<string> GetRollerSlots()
	{
		return ROLLER_SLOTS;
	}

	override int ControlJoint(int control)
	{
		switch (control)
		{
		case BM_Control.RAISE:	return 0;
		case BM_Control.STICK:	return 1;
		case BM_Control.BUCKET:	return 2;
		}
		return -1;
	}

	override bool HasControl(int control)
	{
		return control == BM_Control.SLEW || super.HasControl(control);
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

	protected void ShowSlew(bool now)
	{
		float phase = 0.5 + m_Slew / 360;
		// across the wrap point, -180 and 180 look the same: jump rather than swing round
		if (now || Math.AbsFloat(m_Slew - m_SlewShown) > 180)
			SetAnimationPhaseNow(SLEW_SOURCE, phase);
		else
			SetAnimationPhase(SLEW_SOURCE, phase);
		m_SlewShown = m_Slew;
	}

	//! Nobody aboard: turn the machine (house) by dir * rate * dt with a transform change
	protected void SlewStep(int dir, float dt)
	{
		float delta = -dir * SLEW_RATE * dt;	// left (+1) lowers the heading
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
			dBodySetAngularVelocity(this, Vector(0, -dir * SLEW_RATE * Math.DEG2RAD, 0));	// + = right
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

	override float GetTransportCameraDistance()
	{
		return 12.0;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 4 0";
	}
}
