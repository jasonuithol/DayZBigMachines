//! Server settings, loaded from $profile:BigMachines/BigMachinesSettings.json (written with
//! the defaults on first start). Only the server reads them.
class BMSettings
{
	static const string DIR = "$profile:BigMachines";
	static const string PATH = DIR + "/BigMachinesSettings.json";
	static const int VERSION = 2;		//!< 2: CombinePercent

	int Version;
	//! Percentage of the map's wrecks of each kind that are working machines instead (like
	//! some of the cars being drivable). Checked at every server start: if fewer are left
	//! (destroyed ones are cleared away at the start), new ones take the place of other wrecks.
	//! Lowering it doesn't remove machines already out there. 0 = none.
	float BulldozerPercent;
	float ExcavatorPercent;
	float TowerCranePercent;
	float CombinePercent;
	//! A new bulldozer, excavator or combine's fuel tank: a random fill between these, percent
	float FuelPercentMin;
	float FuelPercentMax;
	//! A new bulldozer, excavator or combine comes with a truck battery (if not, bring one to start it)
	bool SpawnWithBattery;

	protected static ref BMSettings s_Instance;

	void BMSettings()
	{
		Version = VERSION;
		BulldozerPercent = 25;
		ExcavatorPercent = 25;
		TowerCranePercent = 25;
		CombinePercent = 25;
		FuelPercentMin = 5;
		FuelPercentMax = 30;
		SpawnWithBattery = false;
	}

	static BMSettings Get()
	{
		if (!s_Instance)
			s_Instance = new BMSettings();
		return s_Instance;
	}

	static void LoadServer()
	{
		BMSettings settings = new BMSettings();
		string error;
		if (FileExist(PATH))
		{
			if (!JsonFileLoader<BMSettings>.LoadFile(PATH, settings, error))
			{
				ErrorEx("[BigMachines] " + error + " - using the defaults");
				settings = new BMSettings();
			}
			else if (settings.Version < VERSION)
			{
				// Fields added since the file was written keep their defaults; save so they show up
				settings.Version = VERSION;
				JsonFileLoader<BMSettings>.SaveFile(PATH, settings, error);
			}
		}
		else
		{
			MakeDirectory(DIR);
			JsonFileLoader<BMSettings>.SaveFile(PATH, settings, error);
		}
		s_Instance = settings;
		Print("[BigMachines] settings: bulldozers " + settings.BulldozerPercent + "%, excavators " + settings.ExcavatorPercent + "%, tower cranes " + settings.TowerCranePercent + "%, combines " + settings.CombinePercent + "%");
	}

	//! The percentage for a kind of site (BM_WreckSite.DOZER etc.)
	float PercentFor(int kind)
	{
		switch (kind)
		{
		case 0:	return BulldozerPercent;
		case 1:	return ExcavatorPercent;
		case 2:	return TowerCranePercent;
		case 3:	return CombinePercent;
		}
		return 0;
	}
}
