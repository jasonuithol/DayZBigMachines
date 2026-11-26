//! A machine wreck on the map (BM_WreckSites lists them)
class BM_WreckSite
{
	static const int DOZER = 0;
	static const int DIGGER = 1;
	static const int CRANE = 2;
	static const int COMBINE = 3;
	static const int KINDS = 4;

	int Kind;
	string Match;		//!< its class name or model file, lower case
	vector Pos;

	void BM_WreckSite(int kind, string match, vector pos)
	{
		Kind = kind;
		Match = match;
		Pos = pos;
	}

	static string MachineType(int kind)
	{
		switch (kind)
		{
		case DOZER:		return "BM_Bulldozer";
		case DIGGER:	return "BM_Excavator";
		case CRANE:		return "BM_TowerCrane";
		case COMBINE:	return "BM_Combine";
		}
		return "";
	}

	//! Degrees from the wreck's heading to the machine's (the wreck models face other ways)
	static float YawOffset(int kind)
	{
		switch (kind)
		{
		case DOZER:		return 180;		// the wreck's blade is at its back (checked in game)
		case DIGGER:	return 0;
		case CRANE:		return 0;
		case COMBINE:	return 0;		// faces its +Z, the header end, like the machine
		}
		return 0;
	}
}

//! Some of the map's bulldozer, digger and combine harvester wrecks and tower cranes are working machines
//! instead, the way some of the cars are drivable: BMSettings says what percentage of each.
//! At every server start, machines that were destroyed are cleared away and, while there are
//! fewer than that, new ones take the place of other wrecks, chosen at random. A machine
//! remembers the wreck it replaced (BM_Machine.SetHome), which stays hidden as long as the
//! machine is there, wherever it has been driven since.
//!
//! Hidden = sunk out of sight underground, on the server and on every client (map objects
//! aren't networked). The engine streams map objects back in from the map whenever their area
//! reloads, so each side keeps the list and sinks them again every second (as DayZMolotov's
//! MolotovGone; deleting, clearing flags and scaling all leave a map object standing).
class BM_Wrecks
{
	static const int RPC_HIDE = 26437003;
	static const int SWEEP_MS = 1000;
	static const vector SINK = "0 300 0";	//!< a tower crane is tall
	static const float CLAIM_RADIUS = 1.0;	//!< a machine's home within this of a site is that site
	static const string LOOSE_HEADER = "wreck_harvester_head.p3d";	//!< a combine wreck's header, lying by it
	static const float LOOSE_HEADER_RADIUS = 15;	//!< ...this close: a working combine brings its own

	protected static ref array<string> s_Matches = new array<string>();
	protected static ref array<vector> s_Positions = new array<vector>();
	protected static bool s_Sweeping;

	// --- hiding (server and clients) ---

	static bool Matches(Object o, string match)
	{
		string type = o.GetType();
		type.ToLower();
		if (type == match)
			return true;
		string shape = o.GetShapeName();
		shape.ToLower();
		return shape != "" && shape.Contains(match);
	}

	//! The map object `match` at pos (where the scan found it)
	static Object FindWreck(string match, vector pos)
	{
		array<Object> objs = new array<Object>();
		GetGame().GetObjectsAtPosition(pos, 1, objs, null);
		foreach (Object o : objs)
		{
			if (Matches(o, match) && vector.Distance(o.GetPosition(), pos) < 0.3)
				return o;
		}
		return null;
	}

	//! Sink it now, and again whenever it streams back in
	static void Hide(string match, vector pos)
	{
		for (int i = 0; i < s_Matches.Count(); i++)
		{
			if (s_Matches[i] == match && vector.Distance(s_Positions[i], pos) < 0.1)
				return;
		}
		s_Matches.Insert(match);
		s_Positions.Insert(pos);
		Sink(match, pos);
		if (!s_Sweeping)
		{
			s_Sweeping = true;
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(Sweep, SWEEP_MS, true);
		}
	}

	static bool IsHidden(string match, vector pos)
	{
		for (int i = 0; i < s_Matches.Count(); i++)
		{
			if (s_Matches[i] == match && vector.Distance(s_Positions[i], pos) < 0.1)
				return true;
		}
		return false;
	}

	protected static bool Sink(string match, vector pos)
	{
		Object o = FindWreck(match, pos);
		if (!o)
			return false;
		o.SetPosition(pos - SINK);
		o.Update();
		return true;
	}

	//! On a client, one outside the area the player has loaded can't be moved and is "found"
	//! every time: harmless (it is sunk once it streams in near them), so only the server logs
	static void Sweep()
	{
		bool server = GetGame().IsServer();
		for (int i = 0; i < s_Matches.Count(); i++)
		{
			if (Sink(s_Matches[i], s_Positions[i]) && server)
				Print("[BigMachines] " + s_Matches[i] + " at " + s_Positions[i] + " streamed back in: sunk again");
		}
	}

	//! Server: tell one client (or all, identity null) what's hidden
	static void SendAll(PlayerIdentity identity)
	{
		if (!GetGame().IsMultiplayer() || s_Matches.Count() == 0)
			return;
		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(s_Matches);
		rpc.Write(s_Positions);
		rpc.Send(null, RPC_HIDE, true, identity);
	}

	//! Client: the server's list (DayZGame.Event_OnRPC, hooked in 5_Mission)
	static void OnGameRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
	{
		if (rpc_type != RPC_HIDE || GetGame().IsServer())
			return;
		array<string> matches = new array<string>();
		array<vector> positions = new array<vector>();
		if (!ctx.Read(matches) || !ctx.Read(positions) || matches.Count() != positions.Count())
			return;
		for (int i = 0; i < matches.Count(); i++)
			Hide(matches[i], positions[i]);
	}

	// --- replacing (server) ---

	//! Server, once the stored world has loaded: clear away destroyed machines, hide the wrecks
	//! the rest replaced, and make up the numbers BMSettings asks for
	static void ServerStart()
	{
		string world = GetGame().GetWorldName();
		array<ref BM_WreckSite> sites = new array<ref BM_WreckSite>();
		BM_WreckSites.Get(world, sites);
		if (sites.Count() == 0)
		{
			Print("[BigMachines] no wreck sites known on " + world + ": no machines placed");
			return;
		}

		// what's out there already
		array<int> have = {0, 0, 0, 0};		// per BM_WreckSite kind
		array<BM_WreckSite> claimed = new array<BM_WreckSite>();
		array<BM_Machine> machines = new array<BM_Machine>();
		machines.Copy(BM_Machine.GetMachines());
		foreach (BM_Machine m : machines)
		{
			if (!m || !m.HasHome())
				continue;
			if (m.IsRuined())
			{
				Print("[BigMachines] clearing away a destroyed " + m.GetType() + " at " + m.GetPosition());
				GetGame().ObjectDelete(m);
				continue;
			}
			Hide(m.GetHomeMatch(), m.GetHomePos());
			HideLooseHeaders(m);
			foreach (BM_WreckSite s : sites)
			{
				if (s.Match == m.GetHomeMatch() && vector.Distance(s.Pos, m.GetHomePos()) < CLAIM_RADIUS)
				{
					claimed.Insert(s);
					have[s.Kind] = have[s.Kind] + 1;
					break;
				}
			}
		}

		BMSettings settings = BMSettings.Get();
		for (int kind = 0; kind < BM_WreckSite.KINDS; kind++)
		{
			array<BM_WreckSite> candidates = new array<BM_WreckSite>();
			int total = 0;
			foreach (BM_WreckSite site : sites)
			{
				if (site.Kind != kind)
					continue;
				total++;
				if (claimed.Find(site) < 0)
					candidates.Insert(site);
			}
			int want = Math.Round(total * settings.PercentFor(kind) / 100.0);
			int placed = 0;
			while (have[kind] < want && candidates.Count() > 0)
			{
				int pick = Math.RandomInt(0, candidates.Count());
				BM_WreckSite chosen = candidates[pick];
				candidates.Remove(pick);
				if (Replace(chosen))
				{
					have[kind] = have[kind] + 1;
					placed++;
				}
			}
			Print("[BigMachines] " + BM_WreckSite.MachineType(kind) + ": " + have[kind] + " of " + total + " wrecks are machines (" + placed + " new, " + settings.PercentFor(kind) + "% wanted)");
		}
		SendAll(null);
	}

	//! A combine in place of a wreck: the wreck's header lying near it goes too (the machine
	//! has its own). Map objects are back where the map has them at every start.
	static void HideLooseHeaders(BM_Machine machine)
	{
		if (!machine.IsInherited(BM_Combine))
			return;
		array<Object> objs = new array<Object>();
		GetGame().GetObjectsAtPosition(machine.GetHomePos(), LOOSE_HEADER_RADIUS, objs, null);
		foreach (Object o : objs)
		{
			if (Matches(o, LOOSE_HEADER) && !IsHidden(LOOSE_HEADER, o.GetPosition()))
				Hide(LOOSE_HEADER, o.GetPosition());
		}
	}

	//! The ground (or floor) under pos, once the wreck is out of the way
	static vector Ground(vector pos)
	{
		vector from = pos + "0 5 0";
		vector to = pos - "0 60 0";
		vector hit, normal;
		int comp;
		set<Object> results = new set<Object>();
		float ground = GetGame().SurfaceY(pos[0], pos[2]);
		if (DayZPhysics.RaycastRV(from, to, hit, normal, comp, results, null, null, false, false, ObjIntersectGeom) && hit[1] > ground)
			ground = hit[1];
		return Vector(pos[0], ground, pos[2]);
	}

	//! Server: a working machine where this wreck was
	static BM_Machine Replace(BM_WreckSite site)
	{
		Object wreck = FindWreck(site.Match, site.Pos);
		if (!wreck)
		{
			Print("[BigMachines] no " + site.Match + " at " + site.Pos + " (the map has changed?)");
			return null;
		}
		float yaw = wreck.GetOrientation()[0] + BM_WreckSite.YawOffset(site.Kind);
		Hide(site.Match, site.Pos);
		vector base = Ground(site.Pos);
		BM_Machine machine;
		if (site.Kind == BM_WreckSite.CRANE)
			machine = BM_TowerCrane.Place(base, yaw);
		else
			machine = PlaceVehicle(BM_WreckSite.MachineType(site.Kind), base, yaw);
		if (!machine)
			return null;
		machine.SetHome(site.Match, site.Pos, base, yaw);
		HideLooseHeaders(machine);
		Print("[BigMachines] " + machine.GetType() + " in place of the " + site.Match + " at " + site.Pos);
		return machine;
	}

	//! A bulldozer, excavator or combine as found: its own wheels, rollers, oil and coolant, a little fuel, a battery if
	//! the settings say so
	static BM_Machine PlaceVehicle(string type, vector base, float yaw)
	{
		vector pos = base + "0 0.2 0";
		BM_Machine machine = BM_Machine.Cast(GetGame().CreateObjectEx(type, pos, ECE_CREATEPHYSICS));
		if (!machine)
			return null;
		machine.SetOrientation(Vector(yaw, 0, 0));
		machine.SetPosition(pos);		// created with its centre of mass there, not its origin
		machine.FitRollers();
		machine.Fill(CarFluid.OIL, machine.GetFluidCapacity(CarFluid.OIL));
		machine.Fill(CarFluid.COOLANT, machine.GetFluidCapacity(CarFluid.COOLANT));
		machine.Fill(CarFluid.BRAKE, machine.GetFluidCapacity(CarFluid.BRAKE));
		BMSettings settings = BMSettings.Get();
		float fuel = Math.RandomFloatInclusive(settings.FuelPercentMin, settings.FuelPercentMax) / 100.0;
		machine.LeakAll(CarFluid.FUEL);
		machine.Fill(CarFluid.FUEL, machine.GetFluidCapacity(CarFluid.FUEL) * Math.Clamp(fuel, 0, 1));
		if (settings.SpawnWithBattery)
			machine.GetInventory().CreateAttachment("TruckBattery");
		machine.KeepAround();
		return machine;
	}
}
