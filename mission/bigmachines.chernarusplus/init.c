// Big Machines test mission (Chernarus). A bulldozer, fuelled and with a battery, stands on
// open ground beside the Balota airfield; players spawn next to it.
// -missiontest: checks the machine headless, logs [BMTest] lines, then quits.

void main()
{
	Hive ce = CreateHive();
	if (ce)
		ce.InitOffline();

	GetGame().GetWorld().SetDate(2026, 9, 20, 10, 0);
}

class CustomMission: MissionServer
{
	static const vector DOZER_POS = "5060 0 2390";
	static const float DOZER_HEADING = 70;	//!< degrees, roughly along the runway

	protected BM_Bulldozer m_Dozer;
	protected float m_BladeTop0;

	override void OnInit()
	{
		super.OnInit();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(SpawnDozer, 2000, false);

		string value;
		if (GetGame().CommandlineGetParam("missiontest", value))
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestStart, 12000, false);
	}

	void SpawnDozer()
	{
		// After a restart the saved one is still there: two in one spot throw each other about
		array<Object> nearby = new array<Object>();
		GetGame().GetObjectsAtPosition(DOZER_POS, 60, nearby, null);
		foreach (Object o : nearby)
		{
			if (Class.CastTo(m_Dozer, o))
			{
				Print("[BMTest] using the saved bulldozer at " + m_Dozer.GetPosition());
				return;
			}
		}

		vector pos = DOZER_POS;
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]) + 0.3;
		m_Dozer = BM_Bulldozer.Cast(GetGame().CreateObjectEx("BM_Bulldozer", pos, ECE_PLACE_ON_SURFACE | ECE_CREATEPHYSICS));
		if (!m_Dozer)
		{
			Print("[BMTest] FAIL could not create BM_Bulldozer");
			return;
		}
		m_Dozer.SetOrientation(Vector(DOZER_HEADING, 0, 0));
		m_Dozer.OnDebugSpawn();
		// Script-spawned vehicles get a 3 s lifetime and the CE cleanup deletes them
		m_Dozer.SetLifetimeMax(3888000);
		m_Dozer.SetLifetime(3888000);
		Print("[BMTest] spawned bulldozer at " + m_Dozer.GetPosition());
	}

	override void StartingEquipSetup(PlayerBase player, bool clothesChosen)
	{
		super.StartingEquipSetup(player, clothesChosen);
		// beside the left track, where the driver gets in
		vector side = Vector(Math.Sin((DOZER_HEADING - 90) * Math.DEG2RAD), 0, Math.Cos((DOZER_HEADING - 90) * Math.DEG2RAD));
		vector pos = DOZER_POS + side * 4;
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
		player.SetPosition(pos);
	}

	// --- headless checks (-missiontest) ---

	//! Height (model space) of the first hit straight down through a model-space point
	float HitHeight(vector modelPos)
	{
		vector from = m_Dozer.ModelToWorld(Vector(modelPos[0], 6, modelPos[2]));
		vector to = m_Dozer.ModelToWorld(Vector(modelPos[0], -1, modelPos[2]));
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		if (DayZPhysics.RaycastRV(from, to, hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectGeom) && results.Find(m_Dozer) >= 0)
			return m_Dozer.WorldToModel(hitPos)[1];
		return -99;
	}

	void Check(bool ok, string what)
	{
		if (ok)
			Print("[BMTest] ok   " + what);
		else
			Print("[BMTest] FAIL " + what);
	}

	void TestStart()
	{
		if (!m_Dozer)
		{
			Print("[BMTest] FAIL no bulldozer");
			GetGame().RequestExit(0);
			return;
		}
		vector pos = m_Dozer.GetPosition();
		Print("[BMTest] at " + pos + " ori " + m_Dozer.GetOrientation() + " mass " + dBodyGetMass(m_Dozer) + " centre of mass " + dBodyGetCenterOfMass(m_Dozer));
		Check(m_Dozer.WheelCountPresent() == 4, "4 wheels fitted (" + m_Dozer.WheelCountPresent() + ")");
		for (int w = 0; w < m_Dozer.WheelCount(); w++)
		{
			vector contact = m_Dozer.WheelGetContactPosition(w);
			Check(m_Dozer.WheelHasContact(w), "wheel " + w + " on the ground, contact at model " + m_Dozer.WorldToModel(contact) + ", " + (contact[1] - GetGame().SurfaceY(contact[0], contact[2])) + " above the terrain");
		}
		Check(Math.AbsFloat(m_Dozer.GetOrientation()[1]) < 4 && Math.AbsFloat(m_Dozer.GetOrientation()[2]) < 4, "standing level");
		Check(m_Dozer.GetFluidFraction(CarFluid.FUEL) > 0.99, "fuelled");

		int rollers = 0;
		for (int i = 0; i < m_Dozer.GetInventory().AttachmentCount(); i++)
		{
			EntityAI att = m_Dozer.GetInventory().GetAttachmentFromIndex(i);
			if (att.IsKindOf("BM_DozerRoller"))
			{
				rollers++;
				Check(!m_Dozer.CanReleaseAttachment(att), "roller can't be taken off");
			}
		}
		Check(rollers == 4, "4 rollers attached");
		Check(m_Dozer.GetInventory().FindAttachment(TruckBattery.SLOT_ID) != null, "battery fitted");

		// Get-in target: a ray from the left at seat height hits the seat, which is the driver's
		vector from = m_Dozer.ModelToWorld("-3 1.6 -0.85");
		vector to = m_Dozer.ModelToWorld("0 1.6 -0.85");
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		DayZPhysics.RaycastRV(from, to, hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectView);
		Check(m_Dozer.CrewPositionIndex(comp) == 0, "seat is the driver's get-in target");
		Check(m_Dozer.MemoryPointExists("seat_con_1_1"), "get-in point beside the left track");

		m_BladeTop0 = HitHeight("0 0 2.45");
		m_Dozer.BladeCommand(1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBladeUp, 4500, false);
	}

	void TestBladeUp()
	{
		float top = HitHeight("0 0 2.45");
		Check(m_Dozer.GetBladePhase() > 0.99, "blade raised (phase " + m_Dozer.GetBladePhase() + ")");
		Check(top > m_BladeTop0 + 0.1, "blade collision moved up (" + m_BladeTop0 + " -> " + top + ")");
		m_Dozer.BladeCommand(-1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBladeDown, 2000, false);
	}

	void TestBladeDown()
	{
		m_Dozer.BladeCommand(0);	// stop part-way down
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBladeStopped, 1500, false, m_Dozer.GetBladePhase());
	}

	void TestBladeStopped(float stoppedAt)
	{
		Check(stoppedAt > 0.3 && stoppedAt < 0.7 && Math.AbsFloat(m_Dozer.GetBladePhase() - stoppedAt) < 0.01, "blade stops where it is (" + stoppedAt + ")");

		// Driving isn't checked here: car physics run on the driver's client, and without one
		// the engine won't start. DayZAutobot drives it with a real client (see the README).
		TestEnd();
	}

	void TestEnd()
	{
		Check(Math.AbsFloat(m_Dozer.GetOrientation()[1]) < 6 && Math.AbsFloat(m_Dozer.GetOrientation()[2]) < 6, "still upright " + m_Dozer.GetOrientation());
		Print("[BMTest] done");
		GetGame().RequestExit(0);
	}
};

Mission CreateCustomMission(string path)
{
	return new CustomMission();
}
