// Big Machines test mission (Chernarus). A bulldozer and an excavator, fuelled and with
// batteries, stand on open ground beside the Balota airfield; players spawn next to them.
// -missiontest: checks the machines headless, logs [BMTest] lines, then quits. Driving isn't
// checked here: car physics run on the driver's client, and without one the engine won't
// start. DayZAutobot drives them with a real client.

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
	static const vector EXCAVATOR_POS = "5048 0 2408";
	static const float HEADING = 70;	//!< degrees, roughly along the runway

	protected BM_Bulldozer m_Dozer;
	protected BM_Excavator m_Excavator;
	protected float m_Before;

	override void OnInit()
	{
		super.OnInit();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(SpawnMachines, 2000, false);

		string value;
		if (GetGame().CommandlineGetParam("missiontest", value))
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestStart, 12000, false);
	}

	void SpawnMachines()
	{
		m_Dozer = BM_Bulldozer.Cast(SpawnMachine("BM_Bulldozer", DOZER_POS));
		m_Excavator = BM_Excavator.Cast(SpawnMachine("BM_Excavator", EXCAVATOR_POS));
	}

	//! The saved one of this type near `pos`, else a new one (two in one spot throw each other about)
	BM_Machine SpawnMachine(string type, vector pos)
	{
		array<Object> nearby = new array<Object>();
		GetGame().GetObjectsAtPosition(pos, 60, nearby, null);
		foreach (Object o : nearby)
		{
			if (o.GetType() == type)
			{
				Print("[BMTest] using the saved " + type + " at " + o.GetPosition());
				return BM_Machine.Cast(o);
			}
		}
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]) + 0.3;
		BM_Machine machine = BM_Machine.Cast(GetGame().CreateObjectEx(type, pos, ECE_PLACE_ON_SURFACE | ECE_CREATEPHYSICS));
		if (!machine)
		{
			Print("[BMTest] FAIL could not create " + type);
			return null;
		}
		machine.SetOrientation(Vector(HEADING, 0, 0));
		machine.OnDebugSpawn();
		// Script-spawned vehicles get a 3 s lifetime and the CE cleanup deletes them
		machine.SetLifetimeMax(3888000);
		machine.SetLifetime(3888000);
		Print("[BMTest] spawned " + type + " at " + machine.GetPosition());
		return machine;
	}

	override void StartingEquipSetup(PlayerBase player, bool clothesChosen)
	{
		super.StartingEquipSetup(player, clothesChosen);
		// beside the bulldozer's left track, where its driver gets in
		vector side = Vector(Math.Sin((HEADING - 90) * Math.DEG2RAD), 0, Math.Cos((HEADING - 90) * Math.DEG2RAD));
		vector pos = DOZER_POS + side * 4;
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
		player.SetPosition(pos);
	}

	// --- headless checks (-missiontest) ---

	//! Height (model space) of the first hit straight down through a model-space point, -99 if none
	float HitHeight(BM_Machine m, vector modelPos)
	{
		vector from = m.ModelToWorld(Vector(modelPos[0], 8, modelPos[2]));
		vector to = m.ModelToWorld(Vector(modelPos[0], -1, modelPos[2]));
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		if (DayZPhysics.RaycastRV(from, to, hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectGeom) && results.Find(m) >= 0)
			return m.WorldToModel(hitPos)[1];
		return -99;
	}

	void Check(bool ok, string what)
	{
		if (ok)
			Print("[BMTest] ok   " + what);
		else
			Print("[BMTest] FAIL " + what);
	}

	//! What every machine must pass. seatRay: model-space start of a ray towards the model's
	//! x = 0 that should hit the driver's get-in target.
	void CheckMachine(BM_Machine m, vector seatRay)
	{
		string t = m.GetType() + ": ";
		Print("[BMTest] " + t + "at " + m.GetPosition() + " ori " + m.GetOrientation() + " mass " + dBodyGetMass(m) + " centre of mass " + dBodyGetCenterOfMass(m));
		Check(m.WheelCountPresent() == 4, t + "4 wheels fitted (" + m.WheelCountPresent() + ")");
		int onGround = 0;
		for (int w = 0; w < m.WheelCount(); w++)
		{
			if (m.WheelHasContact(w))
				onGround++;
		}
		Check(onGround == 4, t + "4 wheels on the ground (" + onGround + ")");
		Check(Math.AbsFloat(m.GetOrientation()[1]) < 4 && Math.AbsFloat(m.GetOrientation()[2]) < 4, t + "standing level");
		Check(m.GetFluidFraction(CarFluid.FUEL) > 0.99, t + "fuelled");

		int rollers = 0;
		for (int i = 0; i < m.GetInventory().AttachmentCount(); i++)
		{
			EntityAI att = m.GetInventory().GetAttachmentFromIndex(i);
			if (att.IsKindOf(m.GetRollerType()) && !m.CanReleaseAttachment(att))
				rollers++;
		}
		Check(rollers == 4, t + "4 rollers fitted for good (" + rollers + ")");
		Check(m.GetInventory().FindAttachment(TruckBattery.SLOT_ID) != null, t + "battery fitted");

		vector from = m.ModelToWorld(seatRay);
		vector to = m.ModelToWorld(Vector(0, seatRay[1], seatRay[2]));
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		DayZPhysics.RaycastRV(from, to, hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectView);
		Check(results.Find(m) >= 0 && m.CrewPositionIndex(comp) == 0, t + "aiming at the seat gets you in (component " + comp + ")");
		Check(m.MemoryPointExists("seat_con_1_1"), t + "get-in point beside the left track");
	}

	void TestStart()
	{
		if (!m_Dozer || !m_Excavator)
		{
			Print("[BMTest] FAIL machines missing");
			GetGame().RequestExit(0);
			return;
		}
		CheckMachine(m_Dozer, "-3 1.6 -0.85");
		CheckMachine(m_Excavator, "-3 2.2 0.3");

		// Bulldozer: raise the blade; its collision must move up
		m_Before = HitHeight(m_Dozer, "0 0 2.45");
		m_Dozer.BladeCommand(1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBladeUp, 4500, false);
	}

	void TestBladeUp()
	{
		float top = HitHeight(m_Dozer, "0 0 2.45");
		Check(m_Dozer.GetBladePhase() > 0.99, "bulldozer: blade raised (phase " + m_Dozer.GetBladePhase() + ")");
		Check(top > m_Before + 0.1, "bulldozer: blade collision moved up (" + m_Before + " -> " + top + ")");
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
		Check(stoppedAt > 0.3 && stoppedAt < 0.7 && Math.AbsFloat(m_Dozer.GetBladePhase() - stoppedAt) < 0.01, "bulldozer: blade stops where it is (" + stoppedAt + ")");

		// Excavator: raise the boom; the bucket (over the ground 6.6 m ahead) must go up with it
		m_Before = HitHeight(m_Excavator, "0 0 6.6");
		Print("[BMTest] excavator: bucket top at rest " + m_Before);
		ExcavatorControl(BM_Control.RAISE, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBoomUp, 2000, false);
	}

	void ExcavatorControl(int control, int dir)
	{
		m_Excavator.OnControl(control, dir);
	}

	//! Height of the first hit on the excavator straight down through a world point (x, z), -99 if none
	float WorldHit(vector p)
	{
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		if (DayZPhysics.RaycastRV(Vector(p[0], p[1] + 8, p[2]), Vector(p[0], p[1] - 1, p[2]), hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectGeom) && results.Find(m_Excavator) >= 0)
			return hitPos[1] - p[1];
		return -99;
	}

	//! Distance along a world-space ray to its first hit on the excavator, -1 if none
	float RayHit(vector from, vector to)
	{
		vector hitPos, hitNormal;
		int comp;
		set<Object> results = new set<Object>();
		if (DayZPhysics.RaycastRV(from, to, hitPos, hitNormal, comp, results, null, null, false, false, ObjIntersectGeom) && results.Find(m_Excavator) >= 0)
			return vector.Distance(from, hitPos);
		return -1;
	}

	protected vector m_Ahead;		//!< world point under the boom before slewing
	protected vector m_TrackRay;	//!< world point in front of the left track, at track height
	protected vector m_TrackRayEnd;	//!< and one under the machine: the ray between hits the track's front
	protected float m_TrackBefore;
	protected float m_HeadingBefore;

	void TestBoomUp()
	{
		ExcavatorControl(BM_Control.RAISE, 0);
		int boom = m_Excavator.ControlJoint(BM_Control.RAISE);
		float top = HitHeight(m_Excavator, "0 0 6.6");
		Check(m_Excavator.GetJointPhase(boom) > 0.85, "excavator: boom raised (phase " + m_Excavator.GetJointPhase(boom) + ")");
		Check(top > m_Before + 0.3 || (m_Before > -99 && top == -99), "excavator: bucket collision moved up with the boom (" + m_Before + " -> " + top + ")");

		// Slew a quarter turn left: the house (and arm) turn with the machine, the tracks stay put
		m_Ahead = m_Excavator.ModelToWorld("0 0 4.0");
		m_TrackRay = m_Excavator.ModelToWorld("-1.2 0.6 5");
		m_TrackRayEnd = m_Excavator.ModelToWorld("-1.2 0.6 0");
		m_Before = WorldHit(m_Ahead);
		m_TrackBefore = RayHit(m_TrackRay, m_TrackRayEnd);
		m_HeadingBefore = m_Excavator.GetOrientation()[0];
		ExcavatorControl(BM_Control.SLEW, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestSlewed, 2500, false);
	}

	void TestSlewed()
	{
		ExcavatorControl(BM_Control.SLEW, 0);
		float slew = m_Excavator.GetSlew();
		float turned = BM_Excavator.WrapDegrees(m_Excavator.GetOrientation()[0] - m_HeadingBefore);
		Check(Math.AbsFloat(slew + 90) < 8, "excavator: slewed a quarter turn left (" + slew + " deg)");
		Check(Math.AbsFloat(turned - slew) < 3, "excavator: the machine turned with the slew (" + turned + " deg)");
		float ahead = WorldHit(m_Ahead);
		Check(m_Before > 1 && ahead < 1, "excavator: arm swung away from where it was (" + m_Before + " -> " + ahead + ")");
		// Turned with the house, the tracks would meet this ray 0.2 m later (their side, not their end)
		float track = RayHit(m_TrackRay, m_TrackRayEnd);
		Check(m_TrackBefore > 0 && Math.AbsFloat(track - m_TrackBefore) < 0.05, "excavator: tracks stayed put (front of the track " + m_TrackBefore + " m along the ray -> " + track + ")");
		// Stick and bucket move and stop at their ends; slew on round past the wrap
		ExcavatorControl(BM_Control.STICK, 1);
		ExcavatorControl(BM_Control.BUCKET, -1);
		ExcavatorControl(BM_Control.SLEW, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestJointsEnd, 4000, false);
	}

	void TestJointsEnd()
	{
		ExcavatorControl(BM_Control.SLEW, 0);
		int stick = m_Excavator.ControlJoint(BM_Control.STICK);
		int bucket = m_Excavator.ControlJoint(BM_Control.BUCKET);
		Check(m_Excavator.GetJointPhase(stick) > 0.99 && m_Excavator.GetJointDir(stick) == 0, "excavator: stick out to its end and stopped (" + m_Excavator.GetJointPhase(stick) + ")");
		Check(m_Excavator.GetJointPhase(bucket) < 0.01 && m_Excavator.GetJointDir(bucket) == 0, "excavator: bucket dumped to its end and stopped (" + m_Excavator.GetJointPhase(bucket) + ")");
		float slew = m_Excavator.GetSlew();
		Check(slew > 90 && slew < 160, "excavator: slew wrapped past half a turn (" + slew + " deg)");
		Check(Math.AbsFloat(m_Excavator.GetOrientation()[1]) < 6 && Math.AbsFloat(m_Excavator.GetOrientation()[2]) < 6, "excavator: still upright " + m_Excavator.GetOrientation());
		Check(Math.AbsFloat(m_Dozer.GetOrientation()[1]) < 6 && Math.AbsFloat(m_Dozer.GetOrientation()[2]) < 6, "bulldozer: still upright " + m_Dozer.GetOrientation());
		Print("[BMTest] done");
		GetGame().RequestExit(0);
	}
};

Mission CreateCustomMission(string path)
{
	return new CustomMission();
}
