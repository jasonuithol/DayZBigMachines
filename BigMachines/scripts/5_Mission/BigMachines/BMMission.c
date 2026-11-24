//! Server: settings, and some of the map's wrecks swapped for working machines once the stored
//! world has loaded (BM_Wrecks); players joining are told which wrecks are hidden
modded class MissionServer
{
	override void OnInit()
	{
		super.OnInit();
		BMSettings.LoadServer();
	}

	override void OnMissionStart()
	{
		super.OnMissionStart();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(BM_Wrecks.ServerStart, 1000, false);
	}

	override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
	{
		super.InvokeOnConnect(player, identity);
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(BM_Wrecks.SendAll, 3000, false, identity);
	}
}

//! Client: hide the wrecks the server says are working machines now
modded class MissionGameplay
{
	void MissionGameplay()
	{
		DayZGame.Event_OnRPC.Insert(BM_Wrecks.OnGameRPC);
	}
}
