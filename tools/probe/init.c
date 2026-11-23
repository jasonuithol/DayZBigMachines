// One-off probe: list every construction-machinery object on the map, plus named places.
void main()
{
	Hive ce = CreateHive();
	if (ce)
		ce.InitOffline();
}

class CustomMission: MissionServer
{
	override void OnInit()
	{
		super.OnInit();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(Probe, 8000, false);
	}

	void Probe()
	{
		array<string> keys = new array<string>();
		keys.Insert("excavat"); keys.Insert("dozer"); keys.Insert("digger"); keys.Insert("roller");
		keys.Insert("forklift"); keys.Insert("loader"); keys.Insert("crane"); keys.Insert("mixer");
		keys.Insert("hopper"); keys.Insert("haul"); keys.Insert("tractor"); keys.Insert("harv");
		keys.Insert("baler"); keys.Insert("mining"); keys.Insert("hoist"); keys.Insert("construction");
		keys.Insert("grader"); keys.Insert("backhoe"); keys.Insert("dump");

		float size = 20480;
		float tile = 1024;
		int found = 0;
		set<Object> seen = new set<Object>();
		for (float z = tile * 0.5; z < size; z += tile)
		{
			for (float x = tile * 0.5; x < size; x += tile)
			{
				array<Object> objects = new array<Object>();
				GetGame().GetObjectsAtPosition(Vector(x, 0, z), tile * 0.75, objects, null);
				for (int i = 0; i < objects.Count(); i++)
				{
					string name = objects[i].GetDebugName();
					name.ToLower();
					bool hit = false;
					for (int k = 0; k < keys.Count() && !hit; k++)
						hit = name.IndexOf(keys[k]) >= 0;
					if (!hit || seen.Find(objects[i]) >= 0)
						continue;
					seen.Insert(objects[i]);
					found++;
					vector p = objects[i].GetPosition();
					Print("[BM] obj|" + objects[i].GetType() + "|" + objects[i].GetDebugName() + "|" + p[0] + "|" + p[1] + "|" + p[2]);
				}
			}
		}
		Print("[BM] total " + found);

		string path = "CfgWorlds " + GetGame().GetWorldName() + " Names";
		int count = GetGame().ConfigGetChildrenCount(path);
		for (int n = 0; n < count; n++)
		{
			string cls, type, pname;
			GetGame().ConfigGetChildName(path, n, cls);
			GetGame().ConfigGetText(path + " " + cls + " type", type);
			GetGame().ConfigGetText(path + " " + cls + " name", pname);
			TFloatArray pos = new TFloatArray();
			GetGame().ConfigGetFloatArray(path + " " + cls + " position", pos);
			if (pos.Count() == 2)
				Print("[BM] name|" + type + "|" + pname + "|" + pos[0] + "|" + pos[1]);
		}
		Print("[BM] done");
		GetGame().RequestExit(0);
	}
};

Mission CreateCustomMission(string path)
{
	return new CustomMission();
}
