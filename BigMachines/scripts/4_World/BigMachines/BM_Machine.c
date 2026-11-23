//! Shared by the Big Machines: a CarScript that drives on four roller wheels fitted for good
//! (the vanilla car simulation; the rollers sit at a crawler's idlers and sprockets), runs on
//! a truck battery and fuel, and has up to four hydraulic joints the driver works.
//!
//! A joint is a "user" animation source. The server steps its phase on a timer and applies it
//! at once (SetAnimationPhaseNow, so the collision moves too) and syncs it; clients animate
//! towards the synced phase (config animPeriod = 1 / speed, the same rate). Phases are saved.
class BM_Machine extends CarScript
{
	static const int MAX_JOINTS = 4;
	static const int STORE_VERSION = 1;

	protected ref array<string> m_JointSources = new array<string>();
	protected ref array<ref array<string>> m_JointLinked = new array<ref array<string>>();	//!< its cylinders' sources
	protected ref array<float> m_JointSpeeds = new array<float>();		//!< phase per second
	protected ref array<bool> m_JointWraps = new array<bool>();			//!< turns all the way round (slew)
	protected ref array<float> m_JointShown = new array<float>();		//!< client: last phase applied

	// Net-synced joint state (fixed fields: sync variables are registered by name)
	protected float m_J0, m_J1, m_J2, m_J3;
	protected int m_D0, m_D1, m_D2, m_D3;
	protected int m_JointLastTick;

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

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(STORE_VERSION);
		ctx.Write(JointCount());
		for (int j = 0; j < JointCount(); j++)
			ctx.Write(GetJointPhase(j));
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
		return true;
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		ApplyJoints();
		SetSynchDirty();
	}

	override void EEInit()
	{
		super.EEInit();
		if (GetGame().IsServer())
		{
			ApplyJoints();
			// After a load the rollers are already there; FitRollers only fills empty slots
			GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(FitRollers, 100, false);
		}
	}

	override void EEDelete(EntityAI parent)
	{
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
