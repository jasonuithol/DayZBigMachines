//! Crawler excavator: the driver sits in the cab and works the boom (BM_Control.RAISE:
//! PageUp / PageDown), stick (STICK: Home / End) and bucket (BUCKET: Insert / Delete), slews
//! (SLEW: left / right arrows) and drives (BM_SlewingMachine). Slewing turns the whole machine
//! and the undercarriage bone (tracks) turns back by the slew, so the tracks stay where they
//! were: m_Slew is the house's heading minus the tracks', and it drives the way the tracks point.
class BM_Excavator extends BM_SlewingMachine
{
	static const string SLEW_SOURCE = "slew";	//!< undercarriage animation: phase 0.5 = no slew
	static ref array<string> ROLLER_SLOTS = {"BM_Exc_Roller_1_1", "BM_Exc_Roller_1_2", "BM_Exc_Roller_2_1", "BM_Exc_Roller_2_2"};

	void BM_Excavator()
	{
		m_enginePtcPos = "0 2.1 -1.0";
		SetEnginePos("0 1.6 -1.0");
		// Speeds and starting phases: blender/build_excavator.py (JOINTS) and config.cpp
		// each with its cylinder's swing and rod slide (config.cpp AnimationSources)
		array<string> boomLinked = {"boomCyl", "boomRod"};
		array<string> stickLinked = {"dipperCyl", "dipperRod"};
		array<string> bucketLinked = {"bucketCyl", "bucketRod"};
		AddJoint("boom", 0.20, 0.5385, false, boomLinked);
		AddJoint("dipper", 0.20, 0.5294, false, stickLinked);	// the stick
		AddJoint("bucket", 0.25, 0.2692, false, bucketLinked);
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

	override string GetSlewSource()
	{
		return SLEW_SOURCE;
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
