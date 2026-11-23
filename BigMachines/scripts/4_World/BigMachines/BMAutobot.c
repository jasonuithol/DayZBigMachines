// Test hooks for DayZAutobot (~/Projects/DayZAutobot). Compiled only when that mod is loaded,
// so the released mod has no dependency on it. Autobot can't press keys that a mod reads with
// GetUApi() directly (the blade keys), so bm_blade sends the same RPC the keys do.
#ifdef DayZAutobot
class BM_AB
{
	//! The bulldozer the player drives, else the nearest within 30 m
	static BM_Bulldozer Find()
	{
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		if (player && player.GetCommand_Vehicle())
		{
			BM_Bulldozer mine = BM_Bulldozer.Cast(player.GetCommand_Vehicle().GetTransport());
			if (mine)
				return mine;
		}
		vector from = "0 0 0";
		if (player)
			from = player.GetPosition();
		else if (GetGame().IsServer())
		{
			// a server has no player of its own: search round the first connected one
			array<Man> players = new array<Man>();
			GetGame().GetPlayers(players);
			if (players.Count() > 0)
			{
				from = players[0].GetPosition();
				Transport t = Transport.Cast(players[0].GetParent());
				if (BM_Bulldozer.Cast(t))
					return BM_Bulldozer.Cast(t);
			}
		}
		array<Object> objects = new array<Object>();
		GetGame().GetObjectsAtPosition(from, 30, objects, null);
		BM_Bulldozer best;
		float bestDist = 1e9;
		foreach (Object o : objects)
		{
			BM_Bulldozer d = BM_Bulldozer.Cast(o);
			if (d && vector.Distance(from, d.GetPosition()) < bestDist)
			{
				best = d;
				bestDist = vector.Distance(from, d.GetPosition());
			}
		}
		return best;
	}
}

class BM_Cmd_Blade : AB_Command
{
	override bool Start()
	{
		int dir = c.Num("dir", 0);
		BM_Bulldozer dozer = BM_AB.Find();
		if (!dozer)
			return Fail("no bulldozer nearby");
		if (GetGame().IsServer())
			dozer.BladeCommand(dir);
		else
			GetGame().RPCSingleParam(dozer, BM_RPC.BLADE, new Param1<int>(dir), true);	// as the keys do
		c.R.Int("dir", dir).Num("phase", dozer.GetBladePhase());
		return true;
	}
}

class BM_Cmd_State : AB_Command
{
	override bool Start()
	{
		BM_Bulldozer dozer = BM_AB.Find();
		if (!dozer)
			return Fail("no bulldozer nearby");
		c.R.Num("blade_phase", dozer.GetBladePhase()).Num("blade_anim", dozer.GetAnimationPhase(BM_Bulldozer.BLADE));
		c.R.Int("wheels_present", dozer.WheelCountPresent()).Num("speed_kmh", dozer.GetSpeedometer());
		int contact = 0;
		for (int w = 0; w < dozer.WheelCount(); w++)
		{
			if (dozer.WheelHasContact(w))
				contact++;
		}
		c.R.Int("wheels_on_ground", contact).Vec("ori", dozer.GetOrientation()).Vec("pos", dozer.GetPosition());
		return true;
	}
}

modded class AB_WorldCommands
{
	override void Register(AB_Registry reg)
	{
		super.Register(reg);
		reg.Add("bm_blade", BM_Cmd_Blade, "bm_blade dir=1|-1|0 - Big Machines: raise / lower / stop the blade (client: sends the key RPC; server: direct)");
		reg.Add("bm_state", BM_Cmd_State, "bm_state - Big Machines: the nearest bulldozer's blade, wheels, speed");
	}
}
#endif
