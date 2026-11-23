//! Crawler bulldozer: one open-cab driver seat and a blade the driver raises and lowers
//! (BM_Control.RAISE: PageUp / PageDown). Driving, rollers and engine: BM_Machine.
class BM_Bulldozer extends BM_Machine
{
	static const string BLADE = "bladeLift";	//!< animation source, 0 = down, 1 = up
	static ref array<string> ROLLER_SLOTS = {"BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};

	void BM_Bulldozer()
	{
		m_enginePtcPos = "0 1.95 1.0";
		SetEnginePos("0 1.6 0.8");
		array<string> linked = {"bladeCyl", "bladeRod"};	// the lift cylinders' swing and rod slide
		AddJoint(BLADE, 0.25, 0.25, false, linked);		// full travel in 4 s
	}

	override string GetRollerType()
	{
		return "BM_DozerRoller";
	}

	override array<string> GetRollerSlots()
	{
		return ROLLER_SLOTS;
	}

	override int ControlJoint(int control)
	{
		if (control == BM_Control.RAISE)
			return 0;
		return -1;
	}

	float GetBladePhase()
	{
		return GetJointPhase(0);
	}

	//! Server: start the blade moving up (1), down (-1), or stop it where it is (0)
	void BladeCommand(int dir)
	{
		JointCommand(0, dir);
	}

	override float GetTransportCameraDistance()
	{
		return 9.0;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 3.5 0";
	}
}
