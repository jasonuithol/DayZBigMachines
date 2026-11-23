// Test hooks for DayZAutobot (~/Projects/DayZAutobot). Compiled only when that mod is loaded,
// so the released mod has no dependency on it. Autobot can't press keys that a mod reads with
// GetUApi() directly (the machine controls), so bm_control sends the same RPC the keys do.
#ifdef DayZAutobot
class BM_AB
{
	//! The machine the player drives, else the nearest within 30 m (on a server: of the
	//! first connected player)
	static BM_Machine Find()
	{
		Man player = GetGame().GetPlayer();
		if (!player && GetGame().IsServer())
		{
			array<Man> players = new array<Man>();
			GetGame().GetPlayers(players);
			if (players.Count() > 0)
				player = players[0];
		}
		if (player && BM_Machine.Cast(player.GetParent()))
			return BM_Machine.Cast(player.GetParent());
		vector from = "0 0 0";
		if (player)
			from = player.GetPosition();
		array<Object> objects = new array<Object>();
		GetGame().GetObjectsAtPosition(from, 30, objects, null);
		BM_Machine best;
		float bestDist = 1e9;
		foreach (Object o : objects)
		{
			BM_Machine m = BM_Machine.Cast(o);
			if (m && vector.Distance(from, m.GetPosition()) < bestDist)
			{
				best = m;
				bestDist = vector.Distance(from, m.GetPosition());
			}
		}
		return best;
	}
}

class BM_Cmd_Control : AB_Command
{
	override bool Start()
	{
		int control = BM_Control.FromName(c.Str("control", "raise"));
		int dir = c.Num("dir", 0);
		BM_Machine machine = BM_AB.Find();
		if (!machine)
			return Fail("no big machine nearby");
		if (!machine.HasControl(control))
			return Fail(machine.GetType() + " has no control " + control);
		if (GetGame().IsServer())
			machine.OnControl(control, dir);
		else
		{
			// as the keys do (BMControls.c)
			GetGame().RPCSingleParam(machine, BM_RPC.CONTROL, new Param2<int, int>(control, dir), true);
			machine.OnControlLocal(control, dir);
		}
		c.R.Int("control", control).Int("joint", machine.ControlJoint(control)).Int("dir", dir);
		return true;
	}
}

class BM_Cmd_State : AB_Command
{
	override bool Start()
	{
		BM_Machine machine = BM_AB.Find();
		if (!machine)
			return Fail("no big machine nearby");
		AB_JArr joints = new AB_JArr();
		for (int j = 0; j < machine.JointCount(); j++)
		{
			string source = machine.GetJointSource(j);
			AB_JObj o = new AB_JObj();
			o.Str("source", source).Num("phase", machine.GetJointPhase(j));
			o.Num("anim", machine.GetAnimationPhase(source)).Int("dir", machine.GetJointDir(j));
			joints.Obj(o);
		}
		c.R.Str("type", machine.GetType()).Arr("joints", joints);
		BM_Excavator excavator = BM_Excavator.Cast(machine);
		if (excavator)
			c.R.Num("slew", excavator.GetSlew()).Num("slew_anim", excavator.GetAnimationPhase(BM_Excavator.SLEW_SOURCE));
		c.R.Int("wheels_present", machine.WheelCountPresent()).Num("speed_kmh", machine.GetSpeedometer());
		int contact = 0;
		for (int w = 0; w < machine.WheelCount(); w++)
		{
			if (machine.WheelHasContact(w))
				contact++;
		}
		c.R.Int("wheels_on_ground", contact).Vec("ori", machine.GetOrientation()).Vec("pos", machine.GetPosition());
		return true;
	}
}

modded class AB_WorldCommands
{
	override void Register(AB_Registry reg)
	{
		super.Register(reg);
		reg.Add("bm_control", BM_Cmd_Control, "bm_control control=raise|slew|stick|bucket dir=1|-1|0 - Big Machines: work a control (client: sends the key RPC; server: direct)");
		reg.Add("bm_blade", BM_Cmd_Control, "bm_blade dir=1|-1|0 - Big Machines: the blade or boom (bm_control control=raise)");
		reg.Add("bm_state", BM_Cmd_State, "bm_state - Big Machines: the nearest machine's joints, wheels, speed");
	}
}
#endif
