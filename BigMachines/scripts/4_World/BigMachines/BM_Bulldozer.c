//! Crawler bulldozer. Drives on four hidden car wheels (BM_DozerRoller, fitted for good at
//! the idlers and sprockets) with the MS3 truck's sounds; one open-cab driver seat; a blade
//! the driver raises and lowers (PageUp / PageDown, see 5_Mission).
class BM_Bulldozer extends CarScript
{
	static const string BLADE = "bladeLift";	//!< animation source, 0 = down, 1 = up
	static const float BLADE_SPEED = 0.25;		//!< phase per second: full travel in 4 s
	static ref array<string> ROLLER_SLOTS = {"BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};

	//! Blade: the server steps the phase and applies it at once (so the collision moves);
	//! clients get it synced and animate towards it at the same speed
	protected float m_BladePhase = 0.25;
	protected int m_BladeDir;
	protected int m_BladeLastTick;

	void BM_Bulldozer()
	{
		m_enginePtcPos 			= "0 1.95 1.0";

		m_EngineStartOK 		= "Truck_01_engine_start_SoundSet";
		m_EngineStartBattery	= "Truck_01_engine_failed_start_battery_SoundSet";
		m_EngineStartPlug 		= "Truck_01_engine_failed_start_sparkplugs_SoundSet";
		m_EngineStartFuel 		= "Truck_01_engine_failed_start_fuel_SoundSet";
		m_EngineStop 			= "Truck_01_engine_stop_SoundSet";
		m_EngineStopFuel 		= "Truck_01_engine_stop_fuel_SoundSet";

		m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Truck_01_Horn_Short_SoundSet");
		m_HornComponent.RegisterSound(VehicleHornMode.LONG, "Truck_01_Horn_SoundSet");

		SetEnginePos("0 1.6 0.8");

		RegisterNetSyncVariableFloat("m_BladePhase", 0, 1, 3);
		RegisterNetSyncVariableInt("m_BladeDir", -1, 1);
	}

	override void EEInit()
	{
		super.EEInit();
		// After a load the rollers are already there; FitRollers only fills empty slots
		if (GetGame().IsServer())
			GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(FitRollers, 100, false);
	}

	//! The four physics wheels, if any slot is empty
	void FitRollers()
	{
		foreach (string slot : ROLLER_SLOTS)
		{
			if (!FindAttachmentBySlotName(slot))
				GetInventory().CreateAttachmentEx("BM_DozerRoller", InventorySlots.GetSlotIdFromString(slot));
		}
	}

	static bool IsRollerSlot(int slotId)
	{
		foreach (string slot : ROLLER_SLOTS)
		{
			if (InventorySlots.GetSlotIdFromString(slot) == slotId)
				return true;
		}
		return false;
	}

	override bool CanReleaseAttachment(EntityAI attachment)
	{
		if (attachment && attachment.IsKindOf("BM_DozerRoller"))
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

	// --- Blade ---

	float GetBladePhase()
	{
		return m_BladePhase;
	}

	//! Server: start the blade moving up (1), down (-1), or stop it where it is (0)
	void BladeCommand(int dir)
	{
		m_BladeDir = Math.Clamp(dir, -1, 1);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(BladeTick);
		if (m_BladeDir != 0)
		{
			m_BladeLastTick = GetGame().GetTime();
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(BladeTick, 50, true);
		}
		SetSynchDirty();
	}

	protected void BladeTick()
	{
		int now = GetGame().GetTime();
		float dt = (now - m_BladeLastTick) * 0.001;
		m_BladeLastTick = now;
		m_BladePhase = Math.Clamp(m_BladePhase + m_BladeDir * BLADE_SPEED * dt, 0, 1);
		SetAnimationPhaseNow(BLADE, m_BladePhase);
		if ((m_BladeDir > 0 && m_BladePhase >= 1) || (m_BladeDir < 0 && m_BladePhase <= 0))
			BladeCommand(0);
		SetSynchDirty();
	}

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();
		if (!GetGame().IsServer())
			SetAnimationPhase(BLADE, m_BladePhase);
	}

	override void EEDelete(EntityAI parent)
	{
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(BladeTick);
		super.EEDelete(parent);
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);
		if (rpc_type != BM_RPC.BLADE || !GetGame().IsServer())
			return;
		Param1<int> param = new Param1<int>(0);
		if (!ctx.Read(param))
			return;
		// Only the driver works the controls
		Human driver = CrewMember(0);
		if (!driver || !sender || !driver.GetIdentity() || driver.GetIdentity().GetId() != sender.GetId())
			return;
		BladeCommand(param.param1);
	}

	// --- Seat and camera ---

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
		return true;	// open canopy, no doors
	}

	override bool CanReachSeatFromSeat(int currentSeat, int nextSeat)
	{
		return false;
	}

	override bool CanReachDoorsFromSeat(string pDoorsSelection, int pCurrentSeat)
	{
		return false;
	}

	override float GetTransportCameraDistance()
	{
		return 9.0;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 3.5 0";
	}

	override float GetWeightCoef()
	{
		return 3.0;
	}

	// --- Engine: a diesel that needs a truck battery and fuel, nothing else ---

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
