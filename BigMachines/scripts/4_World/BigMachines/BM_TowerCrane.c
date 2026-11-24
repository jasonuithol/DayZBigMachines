//! Tower crane, the working top (cab, jib, trolley, hook, counter-jib). It stands on a
//! BM_TowerCraneMast, a building with the ladder inside it: climb up, get in from the walkway
//! under the cab. Controls: slew (SLEW: left / right arrows; the whole top turns, see
//! BM_SlewingMachine), trolley out / in (STICK: Home / End), hook up / down (RAISE: PageUp /
//! PageDown), latch / let go of a load (BUCKET: Insert / Delete). It doesn't drive.
//!
//! Loads: items and crates. Latching takes the nearest loose item within LATCH_RADIUS of the
//! hook's tip; it then hangs under the hook (the server moves it every LOAD_TICK_MS). Letting
//! go sets it down on the first surface under it.
class BM_TowerCrane extends BM_SlewingMachine
{
	// blender/build_tower_crane.py (TROLLEY_TRAVEL, HOOK_TRAVEL) and config.cpp
	static const float TROLLEY_TRAVEL = 24.0;
	static const float HOOK_TRAVEL = 27.3;
	static const int TROLLEY = 0;
	static const int HOOK = 1;
	static const float LATCH_RADIUS = 1.5;		//!< m round the hook's tip
	static const int LOAD_TICK_MS = 25;
	static const float MAST_HEIGHT = 30.0;		//!< walkway above the mast's origin (build_tower_crane.py DECK_Z)
	static ref array<string> ROLLER_SLOTS = {"BM_Crane_Roller_1_1", "BM_Crane_Roller_1_2", "BM_Crane_Roller_2_1", "BM_Crane_Roller_2_2"};

	protected EntityAI m_Load;			//!< server: what hangs on the hook
	protected vector m_LoadOffset;		//!< from the hook's tip to the load's origin
	protected bool m_Loaded;			//!< synced: something hangs on the hook
	protected BM_TowerCraneMast m_Mast;	//!< server: the mast it stands on, if it put it there

	void BM_TowerCrane()
	{
		array<string> cables = {"cable2", "cable3", "cable4", "cable5", "cable6", "cable7"};
		AddJoint("trolley", 0.1, 0.25);
		AddJoint("hook", 0.06, 1.0, false, cables);		// the cable pieces telescope with it
		RegisterNetSyncVariableBool("m_Loaded");
	}

	//! Server: a crane on a new mast, its foot at base, the jib towards yaw (degrees)
	static BM_TowerCrane Place(vector base, float yaw)
	{
		BM_TowerCraneMast mast = BM_TowerCraneMast.Place(base, yaw);
		if (!mast)
			return null;
		vector pos = base + Vector(0, MAST_HEIGHT + 0.1, 0);
		BM_TowerCrane crane = BM_TowerCrane.Cast(GetGame().CreateObjectEx("BM_TowerCrane", pos, ECE_CREATEPHYSICS));
		if (!crane)
		{
			GetGame().ObjectDelete(mast);
			return null;
		}
		crane.SetOrientation(Vector(yaw, 0, 0));
		crane.SetPosition(pos);		// created with its centre of mass there, not its origin
		crane.FitRollers();
		crane.KeepAround();
		crane.m_Mast = mast;
		return crane;
	}

	//! A saved crane that replaced a map crane puts its mast back (buildings aren't saved)
	//! as it loads, before anything moves, so it has something to stand on
	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		if (!GetGame().IsServer() || !HasHome() || IsRuined())
			return;
		if (!m_Mast)
			m_Mast = BM_TowerCraneMast.Place(GetHomeBase(), GetHomeYaw());
		// back on the mast's axis, should it have shifted (it keeps its slew and height)
		vector pos = GetPosition();
		vector base = GetHomeBase();
		if (Math.AbsFloat(pos[0] - base[0]) > 0.02 || Math.AbsFloat(pos[2] - base[2]) > 0.02)
			SetPosition(Vector(base[0], pos[1], base[2]));
	}

	override string GetRollerType()
	{
		return "BM_CraneRoller";
	}

	override array<string> GetRollerSlots()
	{
		return ROLLER_SLOTS;
	}

	override int ControlJoint(int control)
	{
		switch (control)
		{
		case BM_Control.STICK:	return TROLLEY;
		case BM_Control.RAISE:	return HOOK;
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
			LatchLoad();
		else if (dir < 0)
			ReleaseLoad();
	}

	override bool CanDrive()
	{
		return false;
	}

	override float GetSlewRate()
	{
		return 12;
	}

	// --- the hook ---

	//! World position of the hook's tip, from the trolley's and hook's phases
	vector GetHookTip()
	{
		vector tip = GetMemoryPointPos("hook_point");
		tip[1] = tip[1] - HOOK_TRAVEL * (1 - GetJointPhase(HOOK));
		tip[2] = tip[2] + TROLLEY_TRAVEL * GetJointPhase(TROLLEY);
		return ModelToWorld(tip);
	}

	EntityAI GetLoad()
	{
		return m_Load;
	}

	bool IsLoaded()
	{
		return m_Loaded;
	}

	//! Server: take the nearest loose item within reach of the hook
	void LatchLoad()
	{
		if (m_Load)
			return;
		vector tip = GetHookTip();
		array<Object> nearby = new array<Object>();
		GetGame().GetObjectsAtPosition3D(tip, LATCH_RADIUS, nearby, null);
		ItemBase best;
		float bestDist = 1e9;
		foreach (Object o : nearby)
		{
			ItemBase item = ItemBase.Cast(o);
			if (!item || item.GetHierarchyParent() || item.IsInherited(CarWheel))
				continue;
			float d = vector.Distance(tip, item.GetPosition());
			if (d < bestDist)
			{
				best = item;
				bestDist = d;
			}
		}
		if (!best)
			return;
		m_Load = best;
		// hang it just under the hook: its top 10 cm below the tip
		vector box[2];
		best.ClippingInfo(box);
		float top = best.GetBoundingCenter()[1] + box[1][1];
		m_LoadOffset = Vector(0, -0.1 - top, 0);
		m_Loaded = true;
		SetSynchDirty();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(LoadTick);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(LoadTick, LOAD_TICK_MS, true);
		LoadTick();
	}

	//! Server: set the load down on the first surface under it
	void ReleaseLoad()
	{
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(LoadTick);
		if (m_Load)
		{
			vector from = m_Load.GetPosition();
			vector to = from - Vector(0, 80, 0);
			vector hit, normal;
			int comp;
			set<Object> results = new set<Object>();
			if (DayZPhysics.RaycastRV(from, to, hit, normal, comp, results, null, m_Load, false, false, ObjIntersectGeom))
			{
				vector box[2];
				m_Load.ClippingInfo(box);
				float bottom = m_Load.GetBoundingCenter()[1] + box[0][1];
				m_Load.SetPosition(hit - Vector(0, bottom, 0));
			}
			else
			{
				m_Load.PlaceOnSurface();
			}
		}
		m_Load = null;
		m_Loaded = false;
		SetSynchDirty();
	}

	protected void LoadTick()
	{
		if (!m_Load || m_Load.GetHierarchyParent())
		{
			// gone, or someone took it off the hook
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(LoadTick);
			m_Load = null;
			m_Loaded = false;
			SetSynchDirty();
			return;
		}
		m_Load.SetPosition(GetHookTip() + m_LoadOffset);
	}

	override void EEDelete(EntityAI parent)
	{
		if (GetGame() && GetGame().IsServer())
		{
			ReleaseLoad();
			if (m_Mast)
				GetGame().ObjectDelete(m_Mast);
		}
		super.EEDelete(parent);
	}

	override float GetTransportCameraDistance()
	{
		return 25.0;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 3 0";
	}
}

//! The tower crane's mast: a building, because the game's ladders only work on buildings (the
//! ladder is memory points in its model). A BM_TowerCrane stands on its walkway.
class BM_TowerCraneMast extends House
{
	//! Server: a mast with its foot at base, turned yaw degrees
	static BM_TowerCraneMast Place(vector base, float yaw)
	{
		BM_TowerCraneMast mast = BM_TowerCraneMast.Cast(GetGame().CreateObjectEx("BM_TowerCraneMast", base, ECE_CREATEPHYSICS));
		if (!mast)
			return null;
		mast.SetOrientation(Vector(yaw, 0, 0));
		mast.SetPosition(base);
		mast.Update();
		return mast;
	}
}
