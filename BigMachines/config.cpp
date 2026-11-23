class CfgPatches
{
	class BigMachines
	{
		units[] = {"BM_Bulldozer"};
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

// The bulldozer's four physics wheels sit at the idlers and sprockets. Each slot's
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
	};
	class Slot_BM_Dozer_Roller_2_1: Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_2_1";
		displayName = "Idler, right";
		selection = "wheel_2_1";
	};
	class Slot_BM_Dozer_Roller_2_2: Slot_BM_Dozer_Roller_1_1
	{
		name = "BM_Dozer_Roller_2_2";
		displayName = "Sprocket, right";
		selection = "wheel_2_2";
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
};

class CfgVehicles
{
	class CarWheel;
	// A track end: the wheel the car simulation drives on. Fitted for good when the
	// machine is created (BM_Bulldozer.c) and can't be taken off.
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
		tyreRollResistance = 0.03;
		tyreGrip = 1.0;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 3.0;
		tyreLateralFriction = 2.2;
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

	class CarScript;
	class BM_Bulldozer: CarScript
	{
		scope = 2;
		displayName = "Bulldozer";
		descriptionShort = "A crawler bulldozer. Slow, heavy and very hard to stop.";
		model = "BigMachines\bulldozer\bm_bulldozer.p3d";
		attachments[] = {"TruckBattery", "BM_Dozer_Roller_1_1", "BM_Dozer_Roller_1_2", "BM_Dozer_Roller_2_1", "BM_Dozer_Roller_2_2"};
		fuelCapacity = 200;
		fuelConsumption = 40;
		hiddenSelections[] = {};
		hiddenSelectionsTextures[] = {};
		hiddenSelectionsMaterials[] = {};

		// Open canopy, no doors, one seat
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

		// Written out in full rather than inherited: Binarize only sees this file
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
				// Strong at idle: with the first curve (140 Nm at 650 rpm) it stalled in neutral
				// Falls to nothing below the redline: over it CarScript damages the engine every tick,
				// and the automatic box (one gear) has nowhere to shift to
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
			// One forward gear, about 10 km/h flat out (with the axles' 20:1): the automatic box
			// never upshifted a 3-speed and held first gear past the redline
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
					maxBrakeTorque = 25000;
					maxHandbrakeTorque = 30000;
					wheelHubMass = 60;
					wheelHubRadius = 0.45;
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
							inventorySlot = "BM_Dozer_Roller_1_1";
							animTurn = "turnfrontleft";
							animRotation = "wheelfrontleft";
							animDamper = "damper_1_1";
							wheelHub = "wheel_1_1_damper_land";
						};
						class Right
						{
							inventorySlot = "BM_Dozer_Roller_2_1";
							animTurn = "turnfrontright";
							animRotation = "wheelfrontright";
							animDamper = "damper_2_1";
							wheelHub = "wheel_2_1_damper_land";
						};
					};
				};
				class Rear
				{
					maxBrakeTorque = 25000;
					maxHandbrakeTorque = 30000;
					wheelHubMass = 60;
					wheelHubRadius = 0.45;
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
							inventorySlot = "BM_Dozer_Roller_1_2";
							animTurn = "turnbackleft";
							animRotation = "wheelbackleft";
							animDamper = "damper_1_2";
							wheelHub = "wheel_1_2_damper_land";
						};
						class Right
						{
							inventorySlot = "BM_Dozer_Roller_2_2";
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

		class AnimationSources
		{
			// Blade lift, 0 = down, 1 = up; driven by BM_Bulldozer.c, full travel in 4 s
			class bladeLift
			{
				source = "user";
				initPhase = 0.25;
				animPeriod = 4;
			};
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
};
