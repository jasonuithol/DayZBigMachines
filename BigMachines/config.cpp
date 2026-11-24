class CfgPatches
{
	class BigMachines
	{
		units[] = {"BM_Bulldozer", "BM_Excavator", "BM_TowerCrane", "BM_TowerCraneMast"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts", "DZ_Vehicles_Wheeled", "DZ_Vehicles_Parts", "DZ_Sounds_Effects"};
	};
};

class CfgMods
{
	class BigMachines
	{
		dir = "BigMachines";
		name = "Big Machines";
		type = "mod";
		inputs = "BigMachines/data/inputs.xml";
		dependencies[] = {"Game", "World", "Mission"};

		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"BigMachines/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"BigMachines/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"BigMachines/scripts/5_Mission"};
			};
		};
	};
};

// Each machine drives on four physics wheels at its idlers and sprockets. Each slot's
// selection is the proxy in the model that draws the wheel item.
class CfgSlots
{
	class Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_1_1";
		displayName = "Idler, left";
		selection = "wheel_1_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Dozer_Roller_1_2: Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_1_2";
		displayName = "Sprocket, left";
		selection = "wheel_1_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Dozer_Roller_2_1: Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_2_1";
		displayName = "Idler, right";
		selection = "wheel_2_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Dozer_Roller_2_2: Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_2_2";
		displayName = "Sprocket, right";
		selection = "wheel_2_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Exc_Roller_1_1
	{
		name = "BM_Exc_Roller_1_1";
		displayName = "Idler, left";
		selection = "wheel_1_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Exc_Roller_1_2: Slot_BM_Exc_Roller_1_1
	{
		name = "BM_Exc_Roller_1_2";
		displayName = "Sprocket, left";
		selection = "wheel_1_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Exc_Roller_2_1: Slot_BM_Exc_Roller_1_1
	{
		name = "BM_Exc_Roller_2_1";
		displayName = "Idler, right";
		selection = "wheel_2_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Exc_Roller_2_2: Slot_BM_Exc_Roller_1_1
	{
		name = "BM_Exc_Roller_2_2";
		displayName = "Sprocket, right";
		selection = "wheel_2_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	// The tower crane's top stands on its mast on four small hidden wheels
	class Slot_BM_Crane_Roller_1_1
	{
		name = "BM_Crane_Roller_1_1";
		displayName = "Slewing ring roller, left front";
		selection = "wheel_1_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Crane_Roller_1_2: Slot_BM_Crane_Roller_1_1
	{
		name = "BM_Crane_Roller_1_2";
		displayName = "Slewing ring roller, left back";
		selection = "wheel_1_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Crane_Roller_2_1: Slot_BM_Crane_Roller_1_1
	{
		name = "BM_Crane_Roller_2_1";
		displayName = "Slewing ring roller, right front";
		selection = "wheel_2_1";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
	class Slot_BM_Crane_Roller_2_2: Slot_BM_Crane_Roller_1_1
	{
		name = "BM_Crane_Roller_2_2";
		displayName = "Slewing ring roller, right back";
		selection = "wheel_2_2";
		ghostIcon = "set:dayz_inventory image:wheel";
	};
};

class CfgNonAIVehicles
{
	class ProxyAttachment;
	class ProxyVehiclePart: ProxyAttachment
	{
		scope = 1;
		simulation = "ProxyInventory";
		autocenter = 0;
		animated = 0;
		shadow = 1;
		reversed = 0;
	};
	class Proxybm_dozer_roller: ProxyVehiclePart
	{
		model = "BigMachines\bulldozer\proxy\bm_dozer_roller.p3d";
		inventorySlot[] = {"BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};
	};
	class Proxybm_exc_roller: ProxyVehiclePart
	{
		model = "BigMachines\excavator\proxy\bm_exc_roller.p3d";
		inventorySlot[] = {"BM_Exc_Roller_1_1", "BM_Exc_Roller_1_2", "BM_Exc_Roller_2_1", "BM_Exc_Roller_2_2"};
	};
	class Proxybm_crane_roller: ProxyVehiclePart
	{
		model = "BigMachines\tower_crane\proxy\bm_crane_roller.p3d";
		inventorySlot[] = {"BM_Crane_Roller_1_1", "BM_Crane_Roller_1_2", "BM_Crane_Roller_2_1", "BM_Crane_Roller_2_2"};
	};
};

class CfgVehicles
{
	class CarWheel;
	// A track end: a wheel that only holds the machine up. Next to no grip: the tracks are
	// scripted (BM_Machine.TrackDrive). Fitted for good when the machine is created.
	class BM_DozerRoller: CarWheel
	{
		scope = 2;
		displayName = "Bulldozer track roller";
		descriptionShort = "An idler or drive sprocket from a crawler bulldozer.";
		model = "BigMachines\bulldozer\proxy\bm_dozer_roller.p3d";
		weight = 150000;
		itemSize[] = {10, 10};
		inventorySlot[] = {"BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};
		rotationFlags = 12;
		radiusByDamage[] = {0, 0.49, 0.3, 0.49, 0.9998, 0.49, 0.9999, 0.45};
		radius = 0.49;
		width = 0.56;
		tyreType = 0;
		tyreOffroadResistance = 1.0;
		tyreRollResistance = 0.01;
		tyreGrip = 0.02;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 0.05;
		tyreLateralFriction = 0.05;
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 5000;
					healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
				};
			};
		};
	};
	// Vanilla's CarWheelType looks up a "<wheel>_Ruined" class; a ruined roller still rolls
	class BM_DozerRoller_Ruined: BM_DozerRoller
	{
		scope = 1;
	};
	// A track end: the wheel the car simulation drives on. Fitted for good when the machine
	// is created (BM_Machine.c) and can't be taken off.
	class BM_ExcavatorRoller: CarWheel
	{
		scope = 2;
		displayName = "Excavator track roller";
		descriptionShort = "An idler or drive sprocket from a crawler excavator.";
		model = "BigMachines\excavator\proxy\bm_exc_roller.p3d";
		weight = 150000;
		itemSize[] = {10, 10};
		inventorySlot[] = {"BM_Exc_Roller_1_1", "BM_Exc_Roller_1_2", "BM_Exc_Roller_2_1", "BM_Exc_Roller_2_2"};
		rotationFlags = 12;
		radiusByDamage[] = {0, 0.43, 0.3, 0.43, 0.9998, 0.43, 0.9999, 0.39};
		radius = 0.43;
		width = 0.6;
		tyreType = 0;
		tyreOffroadResistance = 1.0;
		// next to no grip: the wheels only hold the machine up, TrackDrive
		// (BM_SlewingMachine.c) moves it along the tracks
		tyreRollResistance = 0.01;
		tyreGrip = 0.02;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 0.05;
		tyreLateralFriction = 0.05;
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 5000;
					healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
				};
			};
		};
	};
	// Vanilla's CarWheelType looks up a "<wheel>_Ruined" class; a ruined roller still rolls
	class BM_ExcavatorRoller_Ruined: BM_ExcavatorRoller
	{
		scope = 1;
	};
	//! The tower crane's top stands on its mast on four of these; like the excavator's, they
	//! have next to no grip (BM_SlewingMachine holds the top still) and an invisible model
	class BM_CraneRoller: BM_ExcavatorRoller
	{
		displayName = "Slewing ring roller";
		descriptionShort = "A roller from a tower crane's slewing ring.";
		model = "BigMachines\tower_crane\proxy\bm_crane_roller.p3d";
		weight = 20000;
		itemSize[] = {4, 4};
		inventorySlot[] = {"BM_Crane_Roller_1_1", "BM_Crane_Roller_1_2", "BM_Crane_Roller_2_1", "BM_Crane_Roller_2_2"};
		radiusByDamage[] = {0, 0.15, 0.3, 0.15, 0.9998, 0.15, 0.9999, 0.13};
		radius = 0.15;
		width = 0.12;
	};
	class BM_CraneRoller_Ruined: BM_CraneRoller
	{
		scope = 1;
	};

	//! The tower crane's mast: a building, because ladders only work on buildings. The
	//! ladder is memory points in the model (blender/build_tower_crane.py); the top is a
	//! BM_TowerCrane standing on the walkway
	class HouseNoDestruct;
	class BM_TowerCraneMast: HouseNoDestruct
	{
		scope = 1;
		displayName = "Tower crane mast";
		model = "BigMachines\tower_crane\bm_crane_mast.p3d";
	};

	// What the machines share: a slow diesel on one gear, four roller wheels on two locked
	// axles, one driver's seat, a truck battery, the MS3's sounds. Written out in full rather
	// than inherited from CarScript's inner classes: Binarize only sees this file.
	class CarScript;
	class BM_Machine: CarScript
	{
		scope = 0;
		displayName = "Big machine";
		attachments[] = {"TruckBattery"};
		fuelCapacity = 200;
		fuelConsumption = 40;
		hiddenSelections[] = {};
		hiddenSelectionsTextures[] = {};
		hiddenSelectionsMaterials[] = {};

		class Crew
		{
			class Driver
			{
				actionSel = "seat_driver";
				proxyPos = "crewDriver";
				getInPos = "pos_driver";
				getInDir = "pos_driver_dir";
				isDriver = 1;
			};
		};

		class SimulationModule
		{
			class Steering
			{
				maxSteeringAngle = 30;
				increaseSpeed[] = {0, 20, 15, 10};
				decreaseSpeed[] = {0, 40, 15, 20};
				centeringSpeed[] = {0, 25, 15, 15};
			};
			class Throttle
			{
				reactionTime = 0.4;
				defaultThrust = 0.9;
				gentleThrust = 0.6;
				turboCoef = 1.1;
				gentleCoef = 0.5;
				slopeCoef = 0.9;
			};
			class Brake
			{
				pressureBySpeed[] = {0, 0.8, 5, 0.7, 10, 0.6, 20, 0.6};
				gentleCoef = 0.6;
				minPressure = 0.3;
				reactionTime = 0.3;
				driverless = 0.4;
			};
			class Aerodynamics
			{
				frontalArea = 7.0;
				dragCoefficient = 0.9;
			};
			drive = "DRIVE_AWD";
			class Engine
			{
				// Strong at idle (with 140 Nm at 650 rpm it stalled in neutral), and falling to
				// nothing below the redline: over it CarScript damages the engine every tick
				torqueCurve[] = {500, 0, 650, 250, 1000, 450, 1400, 480, 1900, 440, 2200, 250, 2350, 0};
				inertia = 3.5;
				frictionTorque = 100;
				rollingFriction = 3;
				viscousFriction = 2.5;
				rpmIdle = 650;
				rpmMin = 750;
				rpmClutch = 850;
				rpmRedline = 2400;
			};
			class Clutch
			{
				maxTorqueTransfer = 900;
				uncoupleTime = 0.2;
				coupleTime = 0.6;
			};
			// One forward gear: the automatic box never upshifted a 3-speed and held first gear
			// past the redline. Machines set the ratios.
			class Gearbox
			{
				type = "GEARBOX_AUTOMATIC";
				reverse = 2.6;
				ratios[] = {2.0};
			};
			class CentralDifferential
			{
				ratio = 1.0;
				type = "DIFFERENTIAL_LOCKED";
			};
			class Axles
			{
				class Front
				{
					maxBrakeTorque = 40000;
					maxHandbrakeTorque = 50000;
					wheelHubMass = 60;
					// the rim a missing wheel leaves: the rollers never come off, and a hub
					// bigger than the tower crane's 0.15 m rollers loses them (WheelCountPresent 0)
					wheelHubRadius = 0.12;
					class Differential
					{
						ratio = 20;
						type = "DIFFERENTIAL_LOCKED";
					};
					class Suspension
					{
						stiffness = 1800000;
						compression = 25000;
						damping = 35000;
						travelMaxUp = 0.08;
						travelMaxDown = 0.04;
					};
					class Wheels
					{
						class Left
						{
							inventorySlot = "";
							animTurn = "turnfrontleft";
							animRotation = "wheelfrontleft";
							animDamper = "damper_1_1";
							wheelHub = "wheel_1_1_damper_land";
						};
						class Right
						{
							inventorySlot = "";
							animTurn = "turnfrontright";
							animRotation = "wheelfrontright";
							animDamper = "damper_2_1";
							wheelHub = "wheel_2_1_damper_land";
						};
					};
				};
				class Rear: Front
				{
					class Wheels
					{
						class Left
						{
							inventorySlot = "";
							animTurn = "turnbackleft";
							animRotation = "wheelbackleft";
							animDamper = "damper_1_2";
							wheelHub = "wheel_1_2_damper_land";
						};
						class Right
						{
							inventorySlot = "";
							animTurn = "turnbackright";
							animRotation = "wheelbackright";
							animDamper = "damper_2_2";
							wheelHub = "wheel_2_2_damper_land";
						};
					};
				};
			};
		};

		class Cargo
		{
			itemsCargoSize[] = {6, 4};
			allowOwnedCargoManipulation = 1;
			openable = 0;
		};

		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 4000;
					healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
				};
			};
			class DamageZones
			{
				class Chassis
				{
					displayName = "$STR_CfgVehicleDmg_Chassis0";
					fatalInjuryCoef = -1;
					memoryPoints[] = {};
					componentNames[] = {"dmgZone_chassis"};
					class Health
					{
						hitpoints = 8000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
				class Engine
				{
					displayName = "$STR_CfgVehicleDmg_Engine0";
					fatalInjuryCoef = 0.001;
					memoryPoints[] = {"dmgZone_engine"};
					componentNames[] = {"dmgZone_engine"};
					class Health
					{
						hitpoints = 2000;
						transferToGlobalCoef = 1;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {"TruckBattery"};
					inventorySlotsCoefs[] = {0.3};
				};
				class FuelTank
				{
					displayName = "$STR_CfgVehicleDmg_FuelTank0";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_fueltank"};
					componentNames[] = {"dmgZone_fueltank"};
					class Health
					{
						hitpoints = 1500;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
			};
		};

		class ObstacleGenerator
		{
			carve = 1;
			timeToStationary = 5.0;
			moveThreshold = 0.5;
			class Shapes
			{
				class Cylindric
				{
					class Cyl1
					{
						radius = 1.8;
						height = 3.0;
						center[] = {0, 0, 1.2};
					};
					class Cyl2
					{
						radius = 1.8;
						height = 3.0;
						center[] = {0, 0, -1.0};
					};
				};
			};
		};

		class GUIInventoryAttachmentsProps
		{
			class Engine
			{
				name = "$STR_attachment_Engine0";
				description = "";
				icon = "set:dayz_inventory image:cat_vehicle_engine";
				attachmentSlots[] = {"TruckBattery"};
			};
		};

		// The MS3 truck's engine and running gear sounds (sounds_hpp, Truck_01_Base)
		class Sounds
		{
			thrust = 0.6;
			thrustTurbo = 1;
			thrustGentle = 0.3;
			thrustSmoothCoef = 0.02;
			camposSmoothCoef = 0.03;
			soundSetsFilter[] = {"Truck_01_Engine_Offload_Ext_Rpm1_SoundSet", "Truck_01_Engine_Offload_Ext_Rpm2_SoundSet", "Truck_01_Engine_Offload_Ext_Rpm3_SoundSet", "Truck_01_Engine_Offload_Ext_Rpm4_SoundSet", "Truck_01_Engine_Ext_Rpm0_SoundSet", "Truck_01_Engine_Ext_Rpm1_SoundSet", "Truck_01_Engine_Ext_Rpm2_SoundSet", "Truck_01_Engine_Ext_Rpm3_SoundSet", "Truck_01_Engine_Ext_Rpm4_SoundSet", "Truck_01_Engine_Ext_Broken_SoundSet", "Truck_01_Tires_rock_slow_Ext_SoundSet", "Truck_01_Tires_rock_fast_Ext_SoundSet", "Truck_01_Tires_ice_slow_Ext_SoundSet", "Truck_01_Tires_ice_fast_Ext_SoundSet", "Truck_01_Tires_snow_slow_Ext_SoundSet", "Truck_01_Tires_snow_fast_Ext_SoundSet", "Truck_01_Tires_grass_slow_Ext_SoundSet", "Truck_01_Tires_grass_fast_Ext_SoundSet", "Truck_01_Tires_gravel_slow_Ext_SoundSet", "Truck_01_Tires_gravel_fast_Ext_SoundSet", "Truck_01_Tires_gravel_dust_fast_EXT_SoundSet", "Truck_01_Tires_asphalt_slow_Ext_SoundSet", "Truck_01_Tires_asphalt_fast_Ext_SoundSet", "Truck_01_Tires_water_slow_Ext_SoundSet", "Truck_01_Tires_water_fast_Ext_SoundSet", "offroad_skid_dirt_SoundSet", "offroad_dirt_turn_SoundSet", "offroad_damper_left_SoundSet", "offroad_damper_right_SoundSet", "Truck_01_Rain_Ext_SoundSet"};
			soundSetsInt[] = {"Truck_01_Tires_Asphalt_Slow_Ext_SoundSet", "Truck_01_Wind_SoundSet", "Truck_01_Rattle_Int_SoundSet"};
		};
	};

	class BM_Bulldozer: BM_Machine
	{
		scope = 2;
		displayName = "Bulldozer";
		descriptionShort = "A crawler bulldozer. Slow, heavy and very hard to stop.";
		model = "BigMachines\bulldozer\bm_bulldozer.p3d";
		attachments[] = {"TruckBattery", "BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};

		// Three gears; the speed in each is scripted (BM_Bulldozer.DOZER_SPEEDS: 4, 7, 10.6 km/h),
		// the ratios only set the engine's revs
		class SimulationModule: SimulationModule
		{
			class Gearbox
			{
				type = "GEARBOX_MANUAL";
				reverse = 2.6;
				ratios[] = {3.0, 2.0, 1.4};
			};
			class Axles: Axles
			{
				class Front: Front
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Dozer_Roller_1_1";
						};
						class Right: Right
						{
							inventorySlot = "BM_Dozer_Roller_2_1";
						};
					};
				};
				class Rear: Rear
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Dozer_Roller_1_2";
						};
						class Right: Right
						{
							inventorySlot = "BM_Dozer_Roller_2_2";
						};
					};
				};
			};
		};

		class AnimationSources
		{
			// Blade lift, 0 = down, 1 = up; driven by BM_Machine.c, full travel in 4 s
			class bladeLift
			{
				source = "user";
				initPhase = 0.25;
				animPeriod = 4;
			};
			class bladeCyl: bladeLift {};	// the lift cylinders and their rods, in step
			class bladeRod: bladeLift {};	// (BM_Machine.AddJoint)
			// The treads (model.cfg Tread*): set on each client from the ground speed
			// (BM_Machine.TreadFrame), one source per animation
			class treadTop1
			{
				source = "user";
				initPhase = 0;
				animPeriod = 0.01;
			};
			class treadBottom1: treadTop1 {};
			class treadFront1: treadTop1 {};
			class treadRear1: treadTop1 {};
			class treadTop2: treadTop1 {};
			class treadBottom2: treadTop1 {};
			class treadFront2: treadTop1 {};
			class treadRear2: treadTop1 {};
		};

		class DamageSystem: DamageSystem
		{
			class DamageZones: DamageZones
			{
				class Blade
				{
					displayName = "Blade";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_blade"};
					componentNames[] = {"dmgZone_blade"};
					class Health
					{
						hitpoints = 10000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
			};
		};
	};

	class BM_Excavator: BM_Machine
	{
		scope = 2;
		displayName = "Excavator";
		descriptionShort = "A crawler excavator. The upper house turns all the way round.";
		model = "BigMachines\excavator\bm_excavator.p3d";
		attachments[] = {"TruckBattery", "BM_Exc_Roller_1_1", "BM_Exc_Roller_1_2", "BM_Exc_Roller_2_1", "BM_Exc_Roller_2_2"};

		// About 5.5 km/h flat out: 3.4 x 20, rollers 0.43 m. (The car simulation ignored an
		// axle Differential ratio overridden here, though script config reads saw it.)
		class SimulationModule: SimulationModule
		{
			// Three gears; the speed in each is scripted (BM_Excavator.EXC_SPEEDS: 5.5, 9,
			// 12 km/h), the ratios only set the engine's revs
			class Gearbox
			{
				type = "GEARBOX_MANUAL";
				reverse = 4.4;
				ratios[] = {3.4, 2.2, 1.6};
			};
			class Axles: Axles
			{
				class Front: Front
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Exc_Roller_1_1";
						};
						class Right: Right
						{
							inventorySlot = "BM_Exc_Roller_2_1";
						};
					};
				};
				class Rear: Rear
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Exc_Roller_1_2";
						};
						class Right: Right
						{
							inventorySlot = "BM_Exc_Roller_2_2";
						};
					};
				};
			};
		};

		// Driven by BM_Machine.c; initPhase is the modelled pose (blender/build_excavator.py),
		// animPeriod = 1 / the joint's speed in BM_Excavator.c
		class AnimationSources
		{
			class slew
			{
				source = "user";
				initPhase = 0.5;
				animPeriod = 10;
			};
			class boom
			{
				source = "user";
				initPhase = 0.5385;
				animPeriod = 5;
			};
			class dipper		// the stick
			{
				source = "user";
				initPhase = 0.5294;
				animPeriod = 5;
			};
			class bucket
			{
				source = "user";
				initPhase = 0.2692;
				animPeriod = 4;
			};
			// Each joint's cylinder, in step with it (BM_Machine.AddJoint): two model.cfg
			// animations sharing a source scramble the sources after them
			class boomCyl: boom {};
			class boomRod: boom {};
			class dipperCyl: dipper {};
			class dipperRod: dipper {};
			class bucketCyl: bucket {};
			class bucketRod: bucket {};
			// The treads (model.cfg Tread*): set on each client from the ground speed
			// (BM_Machine.TreadFrame), one source per animation
			class treadTop1
			{
				source = "user";
				initPhase = 0;
				animPeriod = 0.01;
			};
			class treadBottom1: treadTop1 {};
			class treadFront1: treadTop1 {};
			class treadRear1: treadTop1 {};
			class treadTop2: treadTop1 {};
			class treadBottom2: treadTop1 {};
			class treadFront2: treadTop1 {};
			class treadRear2: treadTop1 {};
		};

		class DamageSystem: DamageSystem
		{
			class DamageZones: DamageZones
			{
				class Arm
				{
					displayName = "Arm";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_arm"};
					componentNames[] = {"dmgZone_arm"};
					class Health
					{
						hitpoints = 10000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
			};
		};

		class ObstacleGenerator: ObstacleGenerator
		{
			class Shapes: Shapes
			{
				class Cylindric: Cylindric
				{
					class Cyl1: Cyl1
					{
						radius = 2.4;
					};
					class Cyl2: Cyl2
					{
						radius = 2.4;
					};
				};
			};
		};
	};

	//! The tower crane's top: cab, jib, trolley, hook, counter-jib. It stands on a
	//! BM_TowerCraneMast and only slews (BM_TowerCrane.c)
	class BM_TowerCrane: BM_Machine
	{
		scope = 2;
		displayName = "Tower crane";
		descriptionShort = "The working top of a tower crane: climb the mast, sit in the cab, slew the jib, run the trolley and the hook.";
		model = "BigMachines\tower_crane\bm_tower_crane.p3d";
		attachments[] = {"TruckBattery", "BM_Crane_Roller_1_1", "BM_Crane_Roller_1_2", "BM_Crane_Roller_2_1", "BM_Crane_Roller_2_2"};

		class SimulationModule: SimulationModule
		{
			class Axles: Axles
			{
				class Front: Front
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Crane_Roller_1_1";
						};
						class Right: Right
						{
							inventorySlot = "BM_Crane_Roller_2_1";
						};
					};
				};
				class Rear: Rear
				{
					class Wheels: Wheels
					{
						class Left: Left
						{
							inventorySlot = "BM_Crane_Roller_1_2";
						};
						class Right: Right
						{
							inventorySlot = "BM_Crane_Roller_2_2";
						};
					};
				};
			};
		};

		// Driven by BM_Machine.c; offsets and phases: blender/build_tower_crane.py.
		// trolley: 0 in, 1 out (24 m); hook: 0 down (27.3 m), 1 up. The cable pieces move
		// with the hook, each on its own source (never share one: see BM_Machine.AddJoint)
		class AnimationSources
		{
			class trolley
			{
				source = "user";
				initPhase = 0.25;
				animPeriod = 10;
			};
			class hook
			{
				source = "user";
				initPhase = 1.0;
				animPeriod = 16.7;
			};
			class cable2: hook {};
			class cable3: hook {};
			class cable4: hook {};
			class cable5: hook {};
			class cable6: hook {};
			class cable7: hook {};
		};

		class DamageSystem: DamageSystem
		{
			class DamageZones: DamageZones
			{
				class Jib
				{
					displayName = "Jib";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_jib"};
					componentNames[] = {"dmgZone_jib"};
					class Health
					{
						hitpoints = 20000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
					};
					transferToZonesNames[] = {};
					transferToZonesCoefs[] = {};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
			};
		};

		class ObstacleGenerator: ObstacleGenerator
		{
			class Shapes: Shapes
			{
				class Cylindric: Cylindric
				{
					class Cyl1: Cyl1
					{
						radius = 0.5;
					};
					class Cyl2: Cyl2
					{
						radius = 0.5;
					};
				};
			};
		};
	};
};
