// Big Machines test mission (Chernarus). A bulldozer and an excavator, fuelled and with
// batteries, stand on open ground beside the Balota airfield, and a tower crane with a wooden
// crate to lift; players spawn next to them.
// -missiontest: checks the machines headless, logs [BMTest] lines, then quits. Driving isn't
// checked here: car physics run on the driver's client, and without one the engine won't
// start. DayZAutobot drives them with a real client.

const vector BM_CRANE_POS = "5075 0 2420";
const float BM_CRANE_HEADING = 237;		//!< the jib towards the player spawn
const float BM_MAST_HEIGHT = 30.0;		//!< walkway above the mast's origin (build_tower_crane.py DECK_Z)

//! The tower crane's mast: a building, so it isn't saved and is put back at every start. Before
//! the stored world loads, so a saved crane top has its mast to stand on.
BM_TowerCraneMast BM_SpawnCraneMast()
{
	vector pos = BM_CRANE_POS;
	pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
	return BM_TowerCraneMast.Cast(GetGame().CreateObjectEx("BM_TowerCraneMast", pos, ECE_CREATEPHYSICS));
}

void main()
{
	BM_SpawnCraneMast();
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
	protected BM_TowerCrane m_Crane;
	protected BM_TowerCraneMast m_Mast;
	protected ItemBase m_Crate;
	protected int m_ChainsRunning;		//!< test chains still going: the last one to finish exits
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
		SpawnCrane();
	}

	//! The crane's top on its mast (the saved one if there is one), and a crate to lift
	void SpawnCrane()
	{
		array<Object> nearby = new array<Object>();
		GetGame().GetObjectsAtPosition(BM_CRANE_POS, 40, nearby, null);
		foreach (Object o : nearby)
		{
			if (!m_Mast)
				m_Mast = BM_TowerCraneMast.Cast(o);
			if (!m_Crane)
				m_Crane = BM_TowerCrane.Cast(o);
		}
		if (!m_Mast)
		{
			Print("[BMTest] FAIL no crane mast");
			return;
		}
		if (m_Crane)
		{
			Print("[BMTest] using the saved BM_TowerCrane at " + m_Crane.GetPosition());
		}
		else
		{
			vector pos = m_Mast.GetPosition() + Vector(0, BM_MAST_HEIGHT + 0.1, 0);
			m_Crane = BM_TowerCrane.Cast(GetGame().CreateObjectEx("BM_TowerCrane", pos, ECE_CREATEPHYSICS));
			if (!m_Crane)
			{
				Print("[BMTest] FAIL could not create BM_TowerCrane");
				return;
			}
			m_Crane.SetOrientation(Vector(BM_CRANE_HEADING, 0, 0));
			m_Crane.SetPosition(pos);	// created with its centre of mass there, not its origin
			m_Crane.OnDebugSpawn();
			m_Crane.SetLifetimeMax(3888000);
			m_Crane.SetLifetime(3888000);
			Print("[BMTest] spawned BM_TowerCrane at " + m_Crane.GetPosition());
		}
		// a crate on the ground under the hook (trolley where it starts)
		vector tip = m_Crane.GetHookTip();
		tip[1] = GetGame().SurfaceY(tip[0], tip[2]);
		array<Object> here = new array<Object>();
		GetGame().GetObjectsAtPosition(tip, 3, here, null);
		foreach (Object h : here)
		{
			if (h.GetType() == "WoodenCrate")
				m_Crate = ItemBase.Cast(h);
		}
		if (!m_Crate)
			m_Crate = ItemBase.Cast(GetGame().CreateObjectEx("WoodenCrate", tip, ECE_PLACE_ON_SURFACE));
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

	//! New characters start between the two machines, on the drivers' (left) side, facing them
	override PlayerBase CreateCharacter(PlayerIdentity identity, vector pos, ParamsReadContext ctx, string characterName)
	{
		vector side = Vector(Math.Sin((HEADING - 90) * Math.DEG2RAD), 0, Math.Cos((HEADING - 90) * Math.DEG2RAD));
		pos = (DOZER_POS + EXCAVATOR_POS) * 0.5 + side * 6;
		pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
		Entity playerEnt = GetGame().CreatePlayer(identity, characterName, pos, 0, "NONE");
		Class.CastTo(m_player, playerEnt);	// EquipCharacter dresses m_player
		GetGame().SelectPlayer(identity, m_player);
		m_player.SetOrientation(Vector(HEADING + 90, 0, 0));
		return m_player;
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
		m_ChainsRunning = 2;
		TestCraneStart();
		m_ExcavatorStart = m_Excavator.GetPosition();

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
		m_Before = HitHeight(m_Excavator, "0.3 0 6.4");
		Print("[BMTest] excavator: bucket top at rest " + m_Before);
		ExcavatorControl(BM_Control.RAISE, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestBoomUp, 2000, false);
	}

	//! Every joint's animation sources read back its phase. Two model.cfg animations sharing a
	//! source once made the engine send phases to the wrong sources (the stick key moved the
	//! boom), which nothing else here noticed.
	void CheckSources(BM_Machine m)
	{
		for (int j = 0; j < m.JointCount(); j++)
		{
			float phase = m.GetJointPhase(j);
			string src = m.GetJointSource(j);
			bool ok = Math.AbsFloat(m.GetAnimationPhase(src) - phase) < 0.01;
			string got = "" + m.GetAnimationPhase(src);
			array<string> linkedSources = m.GetJointLinkedSources(j);
			for (int k = 0; k < linkedSources.Count(); k++)
			{
				string linked = linkedSources[k];
				ok = ok && Math.AbsFloat(m.GetAnimationPhase(linked) - phase) < 0.01;
				got += ", " + linked + " " + m.GetAnimationPhase(linked);
			}
			Check(ok, m.GetType() + ": " + src + " animations at the joint's phase " + phase + " (" + got + ")");
		}
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

	protected vector m_ExcavatorStart;	//!< where the excavator stood when the checks began
	protected vector m_Ahead;		//!< world point under the boom before slewing
	protected vector m_TrackRay;	//!< world point in front of the left track, at track height
	protected vector m_TrackRayEnd;	//!< and one under the machine: the ray between hits the track's front
	protected float m_TrackBefore;
	protected float m_HeadingBefore;

	void TestBoomUp()
	{
		ExcavatorControl(BM_Control.RAISE, 0);
		int boom = m_Excavator.ControlJoint(BM_Control.RAISE);
		float top = HitHeight(m_Excavator, "0.3 0 6.4");
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
		float turned = BM_SlewingMachine.WrapDegrees(m_Excavator.GetOrientation()[0] - m_HeadingBefore);
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
		// its wheels have next to no grip: with nobody aboard, TrackDrive holds it there
		float moved = vector.Distance(m_ExcavatorStart, m_Excavator.GetPosition());
		Check(moved < 0.3, "excavator: parked, it stays put while slewing (moved " + moved + " m)");
		Check(Math.AbsFloat(m_Dozer.GetOrientation()[1]) < 6 && Math.AbsFloat(m_Dozer.GetOrientation()[2]) < 6, "bulldozer: still upright " + m_Dozer.GetOrientation());
		CheckSources(m_Dozer);
		CheckSources(m_Excavator);
		ChainDone();
	}

	void ChainDone()
	{
		m_ChainsRunning--;
		if (m_ChainsRunning > 0)
			return;
		Print("[BMTest] done");
		GetGame().RequestExit(0);
	}

	// --- tower crane: a chain of checks of its own, alongside the others ---

	protected float m_CrateLow;
	protected vector m_CrateBeforeSlew;
	protected float m_CraneHeading;

	float CraneOnMast()
	{
		return m_Crane.GetPosition()[1] - m_Mast.GetPosition()[1] - BM_MAST_HEIGHT;
	}

	void TestCraneStart()
	{
		if (!m_Crane || !m_Mast || !m_Crate)
		{
			Print("[BMTest] FAIL crane, mast or crate missing");
			ChainDone();
			return;
		}
		CheckMachine(m_Crane, "4 3.2 1.2");
		Check(Math.AbsFloat(CraneOnMast()) < 0.3, "crane: the top stands on the mast (" + CraneOnMast() + " m off the walkway)");
		Check(m_Mast.MemoryPointExists("ladder1_con") && m_Mast.MemoryPointExists("ladder1"), "crane: the mast has its ladder");
		// hook all the way down, onto the crate
		m_Crane.OnControl(BM_Control.RAISE, -1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestCraneHookDown, 18000, false);
	}

	void TestCraneHookDown()
	{
		int hook = BM_TowerCrane.HOOK;
		Check(m_Crane.GetJointPhase(hook) < 0.01 && m_Crane.GetJointDir(hook) == 0, "crane: hook down to its end and stopped (" + m_Crane.GetJointPhase(hook) + ")");
		float gap = m_Crane.GetHookTip()[1] - GetGame().SurfaceY(m_Crane.GetHookTip()[0], m_Crane.GetHookTip()[2]);
		Check(gap > 0 && gap < 1.0, "crane: the hook reaches the ground (" + gap + " m above it)");
		m_CrateLow = m_Crate.GetPosition()[1];
		m_Crane.OnControl(BM_Control.BUCKET, 1);
		Check(m_Crane.GetLoad() == m_Crate && m_Crane.IsLoaded(), "crane: latched the crate");
		m_Crane.OnControl(BM_Control.RAISE, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestCraneLifted, 5000, false);
	}

	void TestCraneLifted()
	{
		m_Crane.OnControl(BM_Control.RAISE, 0);
		float rose = m_Crate.GetPosition()[1] - m_CrateLow;
		Check(rose > 5, "crane: the crate went up with the hook (" + rose + " m)");
		float under = vector.Distance(Vector(m_Crate.GetPosition()[0], 0, m_Crate.GetPosition()[2]), Vector(m_Crane.GetHookTip()[0], 0, m_Crane.GetHookTip()[2]));
		Check(under < 0.2, "crane: it hangs under the hook (" + under + " m off)");
		m_CrateBeforeSlew = m_Crate.GetPosition();
		m_CraneHeading = m_Crane.GetOrientation()[0];
		m_Crane.OnControl(BM_Control.SLEW, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(TestCraneSlewed, 3000, false);
	}

	void TestCraneSlewed()
	{
		m_Crane.OnControl(BM_Control.SLEW, 0);
		float turned = BM_SlewingMachine.WrapDegrees(m_Crane.GetOrientation()[0] - m_CraneHeading);
		Check(turned < -25 && turned > -50, "crane: slewed left (" + turned + " deg)");
		float carried = vector.Distance(m_CrateBeforeSlew, m_Crate.GetPosition());
		Check(carried > 3, "crane: the crate swung round with the jib (" + carried + " m)");
		Check(Math.AbsFloat(CraneOnMast()) < 0.3 && Math.AbsFloat(m_Crane.GetOrientation()[1]) < 3 && Math.AbsFloat(m_Crane.GetOrientation()[2]) < 3, "crane: still upright on the mast (" + CraneOnMast() + " m, " + m_Crane.GetOrientation() + ")");
		m_Crane.OnControl(BM_Control.BUCKET, -1);
		vector p = m_Crate.GetPosition();
		float above = p[1] - GetGame().SurfaceY(p[0], p[2]);
		Check(!m_Crane.IsLoaded() && Math.AbsFloat(above) < 0.5, "crane: let go, the crate is set down on the ground (" + above + " m)");
		CheckSources(m_Crane);
		ChainDone();
	}
};

Mission CreateCustomMission(string path)
{
	return new CustomMission();
}
