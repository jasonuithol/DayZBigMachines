//! RPC ids used by Big Machines (client -> server control input)
class BM_RPC
{
	static const int CONTROL = 26437002;	//!< Param2<int, int>: control (BM_Control), direction -1 / 0 / 1
}

//! The driver's controls. Each is a pair of keys: the first moves the joint "up" (+1), the
//! second "down" (-1). A machine maps the controls it has onto its joints (BM_Machine.ControlJoint).
class BM_Control
{
	static const int RAISE = 0;		//!< blade / boom: raise, lower
	static const int SLEW = 1;		//!< upper house: left, right
	static const int STICK = 2;		//!< stick: out, in
	static const int BUCKET = 3;	//!< bucket: curl, dump
	static const int COUNT = 4;

	static string KeyUp(int control)
	{
		switch (control)
		{
		case RAISE:		return "UABMBladeUp";
		case SLEW:		return "UABMSlewLeft";
		case STICK:		return "UABMStickOut";
		case BUCKET:	return "UABMBucketCurl";
		}
		return "";
	}

	static string KeyDown(int control)
	{
		switch (control)
		{
		case RAISE:		return "UABMBladeDown";
		case SLEW:		return "UABMSlewRight";
		case STICK:		return "UABMStickIn";
		case BUCKET:	return "UABMBucketDump";
		}
		return "";
	}

	static int FromName(string name)
	{
		name.ToLower();
		if (name == "raise" || name == "blade" || name == "boom")
			return RAISE;
		if (name == "slew")
			return SLEW;
		if (name == "stick" || name == "arm")
			return STICK;
		if (name == "bucket")
			return BUCKET;
		return name.ToInt();
	}
}
