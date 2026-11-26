# Big Machines - checklist

Goal: turn the construction-machine wrecks on the vanilla maps into vehicles a player can
get into and operate.

Source data: [`data/construction_vehicles.csv`](data/construction_vehicles.csv) has every
machine's position (map, class, model, x, y, z), from a headless server scan of all four maps
on 2026-11-24 (DayZ stable 1.30). The scan mission is in `tools/probe/init.c`, and
`tools/probe/group_sites.py <profiles dir>` groups the results into sites.

## The machines

| # | Machine | Map model | Chernarus | Livonia | Sakhal | Nasdara | Total |
|---|---|---|---|---|---|---|---|
| 1 | Bulldozer | `DZ\structures\Wrecks\Vehicles\Wreck_Bulldozer.p3d` (terrain object; Nasdara also has 1 `StaticObj_Wreck_Bulldozer_DE`) | 13 | 17 | 26 | 69 | 125 |
| 2 | Excavator (digger) | `DZ\structures\Wrecks\Vehicles\Wreck_Digger.p3d` (terrain object) | 18 | 23 | 24 | 51 | 116 |
| 3 | Mining excavator | `Land_Wreck_Mining_Excavator` (`structures_bliss`) | - | 2 | 3 | - | 5 |
| 4 | Mining haul truck | `Land_Wreck_Mining_HaulTruck` (`structures_bliss`) | - | 8 | 8 | - | 16 |
| 5 | Crawler crane | `Wreck_CrawlerCrane_Cabin` / `_Tracks` / `_Arm` (`structures_takistan`, 3 parts) | - | - | - | 7 | 7 |
| 6 | Tower crane | `Land_Construction_Crane` | 6 | - | 3 | 13 | 22 |
| 7 | Concrete mixer | `Concrete_Mixer_01.p3d` (a proxy of a Nasdara building site) | - | - | - | 1 | 1 |
| 8 | Combine harvester | `Land_Wreck_Harverster` (sic; loose headers `wreck_harvester_head.p3d` beside them, headers on trailers `Land_Wreck_Harvester_head_trailer`; [`data/farm_vehicles.csv`](data/farm_vehicles.csv), scanned 2026-11-25) | 31 | 53 | 5 | - | 89 |

Maybe later (farm machinery and port equipment):
tractor `Land_Wreck_Tractor` (49 / 81 / 69 / 75), harbour cranes `Land_Pier_Crane_A/B` (23 / 0 / 14 / 3), Sakhal's
`Pier_Crane2` gantries (13) and stockyard shiploaders (2).

## Progress

Steps for each machine:

- **Model**: a drivable model with wheels or tracks, seats, a driver's view, and geometry/physics LODs.
- **Moving parts**: blade, arm, bucket, boom, slew, tipper, drum, set up in `model.cfg` and driven by controls.
- **Vehicle class**: `CfgVehicles` config plus a `CarScript` subclass: engine, gearbox, fuel, damage zones.
- **Controls**: keybinds for the moving parts. Moving parts do real work, e.g. a blade or bucket shoves objects.
- **Sounds**: engine, tracks, hydraulics.
- **On the map**: hide each static wreck and spawn a working machine in its place, on all maps where it appears.
- **Tested**: drive, enter/exit, operate, damage, persistence across restarts.

| Machine | Model | Moving parts | Vehicle class | Controls | Sounds | On the map | Tested |
|---|---|---|---|---|---|---|---|
| 1 Bulldozer | [x] v0.2, FAT livery, weathered paint | [x] blade | [x] | [x] blade keys | [~] MS3 truck sounds | [x] replaces a share of wrecks | [~] see below |
| 2 Excavator | [x] v0.2, FAT livery, weathered paint | [x] slew, boom, stick, bucket | [x] | [x] | [~] MS3 truck sounds | [x] replaces a share of wrecks | [~] see below |
| 3 Mining excavator | [ ] | [ ] slew, boom, bucket | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 Mining haul truck | [ ] | [ ] tipper | [ ] | [ ] | [ ] | [ ] | [ ] |
| 5 Crawler crane | [ ] | [ ] slew, boom, hook | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 Tower crane (fixed; operate, not drive) | [x] v0.1, mast + slewing top, FAT livery, weathered | [x] slew, trolley, hook, latch items | [x] | [x] | [ ] none yet | [x] replaces a share of cranes | [~] see below |
| 7 Concrete mixer | [ ] | [ ] drum | [ ] | [ ] | [ ] | [ ] | [ ] |

### Bulldozer status (2026-11-24)

Verified in game with DayZAutobot (a real client on a throwaway server), on open ground near Balota:
gets in from the left track (seat faces forward), engine starts and idles, drives 10.6 km/h flat
out at 2300 rpm (under the 2400 redline, so no engine damage), reverses at 8 km/h, steers (50 deg
in 6 s at full lock), brakes to a stop, blade raises/lowers/stops on the driver's RPC and its
collision moves with it, and the blade shoved a parked hatchback 15 m. The saved machine survives a
server restart. Headless checks (`tools/test.sh bigmachines` in DayZMissions) cover spawn, wheels,
attachments, get-in target and the blade.

Not yet checked by a person: how it feels to drive, the PageUp/PageDown keys themselves (Autobot
can't press keys a mod reads with GetUApi(); it sends the same RPC), third-person camera, sounds.

To do for the bulldozer:
- [x] FAT livery (DayZ's own fictional brand, from the vanilla wrecks), drawn clean by
  tools/make_textures.py as decals; radiator grille, hood hatch and grille, side doors, exhaust
  guard and rain cap, roof lights, beacon, grab handle (2026-11-24, checked in game)
- [x] Sprockets/idlers no longer stick out of the tracks or jump about: the game moves the
  wheel bones with the suspension, so the rollers are invisible and the sprockets are fixed to
  the track frame (blender/crawler.py); they turn with the treads now (below)
- [x] Weathered textures (tools/make_weathering.py: worn paint, chips, rust streaks, grime, muddy
  tracks; box-projected 2 m tiles), worn decals (2026-11-24, checked in game)
- [ ] A View Pilot LOD for the cab
- [x] Treads (playtest: "tracks should move with the vehicle, and have treads"): separate shoes
  with grouser bars (blender/crawler.py Tracks.treads), pitch chosen so whole shoes fill each
  run and each end; four bones a side (top, bottom, front, rear; sprocket and idler turn with
  the ends) that model.cfg moves one shoe on per cycle, looping seamlessly. Each client runs
  them from how far each side moved along the tracks (BM_Machine.TreadFrame), so they keep pace
  with the ground and run opposite ways turning on the spot. Autobot: phases 0 / 0.5 / 0.9 line
  up at the ends; forward 0.5 cycles/s at 0.3 km/h on both sides, opposite when turning; test.sh
  checks the 8 tread sources don't scramble the others. Bulldozer and excavator
- [x] Turn on the spot (skid steer) instead of car-style steering
- [x] Climbing (playtest: crawled up the slightest slope): it drove on the car simulation's four
  wheels, and the lowered blade caught rising ground. Now the excavator's scripted track drive
  (moved into BM_Machine) with low-grip rollers, a manual gearbox with 3 gears (4 / 7 / 10.6
  km/h, BM_Bulldozer.DOZER_SPEEDS), and the blade's collision 0.2 m above its edge. Autobot on
  a 10-11 deg slope: 3.1 km/h in 1st, 9.7 in 3rd, 6.5 in 2nd with the blade fully down
- [x] Keep the blade position across restarts (every joint is saved; checked on the excavator)
- [x] Replace a share of the map's Wreck_Bulldozer objects with working machines (see "On the map")
- [ ] Silence the engine warning "Second driver found when parsing class Crew::Crew" (harmless)

### Excavator status (2026-11-24)

Crawler excavator, 18.5 t: glazed cab front left, boom/stick/bucket with three hydraulic
cylinders, counterweight. Controls: PageUp/PageDown boom, Left/Right arrows slew, Home/End
stick, Insert/Delete bucket (rebindable, "Big Machines" in the key settings).

Slewing is faked: DayZ fixes a seated player where the seat is in the modelled pose, so the
cab can't turn on the model. The whole machine turns (the server spins it, the driver's client
predicts) and the undercarriage turns back so the tracks stay put.

Driving is scripted (TrackDrive in BM_Excavator.c): the physics wheels sit under the cab, so
they get next to no grip and only hold the machine up; each physics step sets its speed along
the tracks from throttle, brake and gear, stops sideways slide, and turns it on the spot when
steering (like a tracked machine, slew unchanged). Holds still on a slope.

Verified in game with DayZAutobot: gets in by aiming at the cab; engine; drives 5.5 km/h flat
out at 2300 rpm; slewing turns the driver with the cab (heading and counted slew agree to
0.02 deg) and the tracks stay pointing where they were; boom, stick and bucket move and stop at
their ends, cylinders follow; joint positions and slew survive a server restart. Headless
(`tools/test.sh bigmachines`): wheels, rollers, battery, get-in target, every joint, the arm's
collision following boom and slew, the tracks' collision staying put through a slew.

Not yet checked by a person: how slewing and digging feel, the keys themselves, sounds.

To do for the excavator:
- [x] FAT livery decals (boom stripes, counterweight letters, hazard stripes, logo plate,
  "FAT 218" badges); hood hatch with louvred grille, side doors, intake grille, radiator mesh
  door, toolbox, sight gauge, fuel cap, air cleaner, muffler, exhaust guard and rain cap,
  handrail, work lights, beacon, wiper, mirror; sprockets inside the tracks; a hollow cab
  (the seat and the driver's legs were buried in the lower panels) (checked in game)
- [x] Backhoe bucket: teeth face the machine and curl in under it (it was drawn as a front
  shovel); cylinder rods slide in their barrels instead of swinging with the part they push
- [x] The stick and bucket keys worked the wrong parts: two model.cfg animations shared a
  source, which shifts every source after them. Each now has its own; tools/test.sh checks it
- [x] Weathered textures; [ ] a View Pilot LOD for the cab
- [ ] Digging: something for the bucket to pick up or move (dirt piles, loose items)
- [x] Drive along the tracks, not the cab, after a slew (found in the first playtest;
  Autobot: slewed 94 deg, drove 6.6 m at 69.7 deg with the tracks at 70.1; reverse, steering,
  pivot turns; server and client agree)
- [ ] Engine sound: the wheels spin freely, so it revs to ~2300 rpm on throttle whatever the
  ground speed (the bulldozer too, now)
- [x] Boulders and knock-outs (playtest: stuck on smallish boulders, driver knocked out):
  vanilla crash damage goes by momentum, so a 14 t machine nudging a rock counted as a crash
  (shock 50 a knock); now scaled to the mass (BM_Machine.CheckContactCache / DamageCrew: hurts
  like a car at the same change of speed). Tracks: collision ends ramped (34 deg to 0.8 m),
  the blade's underside sloped, the drive pushes with 0.8 g of traction from the tracks' own
  speed, and when pushing without moving it climbs anything lower than 1 m ahead (at most
  0.8 m, not tilted past 30 deg). Autobot: over a 0.55 m boulder at 2-3 km/h without stopping,
  stops at a rock outcrop instead of climbing it (it flipped before the limits), shock 100
- [x] A higher gear (playtest): manual gearbox, 5.5 km/h in 1st, 9 in 2nd (EXC_SPEEDS); Autobot
  8.3 km/h in 2nd at the game's 0.9 throttle
- [x] Another gear (playtest): 3rd, 12 km/h; Autobot 11.9 km/h flat out at 2350 rpm (redline 2400)
- [x] Replace a share of the map's Wreck_Digger objects with working machines (see "On the map")

### Tower crane status (2026-11-24)

Two objects, because the game's ladders only work on buildings: `BM_TowerCraneMast`, a building
(concrete footing, 30 m lattice mast, ladder up its side, a walkway with handrails at the top),
and `BM_TowerCrane`, the working top (slewing column, cab, A-frame head, 30 m jib, trolley,
hook on a telescoping cable, counter-jib with counterweights) standing on the walkway on four
hidden wheels. Climb the ladder, step off on the walkway, get in at the short ladder under the
cab. Controls: arrows slew (12 deg/s, the whole top turns), Home/End trolley out/in, PageUp/
PageDown hook up/down, Insert latches the nearest loose item or crate within 1.5 m of the hook,
Delete lets go and sets it down on the first surface below. The top holds itself level and
still on the mast (BM_SlewingMachine, shared with the excavator). The test mission spawns one
at 5075/2420 with a wooden crate.

Verified in game with DayZAutobot: climb the ladder up (about 55 s) and step off; get in from
the walkway; slew 36.8 deg in 3 s with server and client agreeing; trolley and hook; lower onto
a crate, latch it, lift it 9 m (the client draws it on the hook), set it down on the ground; get
out onto the walkway; get on the ladder at the top and climb down. Headless: the top stands
level on the mast, the hook reaches the ground, latch/lift/slew/release, every animation source.

Not yet checked by a person: how it feels, the keys themselves.

To do for the tower crane:
- [ ] Sounds (slew motor, hoist winch)
- [ ] Lift vehicles (only items and crates for now)
- [ ] A load hanging at a restart stays where it was in mid-air (it isn't saved as hanging)
- [x] Replace a share of the maps' Land_Construction_Crane objects (see "On the map"); a saved
  top puts its mast back as it loads (AfterStoreLoad) and re-centres itself on it
- [x] Getting on the ladder at the top (found in the first playtest: you were stuck up there).
  The ladder's view geometry now reaches above the walkway so you can aim at it, and the
  top get-on point is just in from the notch edge (you must stand inward of it)
- [ ] The ladder's rungs seemed closer together near the top (playtest); not looked into yet
- [ ] Hook height is fixed to 30 m of travel: on a slope the hook stops short of or above the ground

### Combine harvester status (2026-11-25)

The map wreck restored (reference shots: `data/reference/combine_wreck_*.png`): pale mint green
body, cream grain tank and engine housing, glass cab on a deck at the front with a ladder up the
left, big lugged drive wheels at the front, small steering wheels at the back, the unloading
auger along the left side. blender/build_combine.py; weathered paint_mint / paint_cream
(tools/make_weathering.py); the header 6 m wide (the wreck's is 7.8 m: too wide for DayZ's roads).

Real wheels (blender/wheeled.py), as vanilla cars: the suspension moves a parent bone
(susp_wheel_X_Y), the wheel bone only spins (the hatchback's ODOL); the wheels sit on the ground
and stay still parked. The car simulation can't steer with the back axle (a negative steering
angle crashes the game), so it steers 1 degree and BM_Combine.SteerBack sets the yaw rate from
speed and steering each physics step; the back wheels turn for show.

Controls: PageUp / PageDown header (comes raised), Home / End unloading auger, Insert / Delete
header running (engine on). Running and lowered, it kills zombies, animals and players other
than the driver within its reach (BM_Combine.CatchTick, server, every 0.1 s).

Verified: Autobot (2026-11-25): drives, 4.9 km/h in 1st at 2300 rpm; forward with steering right
turned 293 -> 344 deg, reversing turns the other way; header down, running, reel spinning; a
zombie in front killed, one beside the cab and one in front of the raised header spared.
Headless suite (76 ok): the test combine passes CheckMachine; 8 of Chernarus's 31 combine
wrecks replaced at 25%, all upright on 4 wheels where the wreck was, wrecks and loose headers
gone; the header kills / spares and stops with the engine.

Driven in game (2026-11-26, local server): all 31 Chernarus combines placed at 100%. Fixed from
that: wheels, reel and back-wheel steer anims had the wrong sign (the back wheels turn against the
turn); the unloading auger swivels on the tank roof (front left) and climbs back at ~35 deg to a
cradle post, swinging out to the left; a spoked steering wheel facing the driver. It caught on
unseen bumps, even on roads: the header's physics sat 12 cm off the ground (0.44 m raised), so
the Geometry LOD's header and feeder now sit 0.3 m above the visual, the header's front a ramp.
The test mission's `$profile:BigMachines/move_me.txt` ("x z") puts the next character to connect
beside the machine nearest that spot.

To do:
- [ ] Snagging on roads after the header's collision was lifted (not driven far yet)
- [ ] The back wheels' steer look on other players' clients (GetSteering on a proxy?)
- [ ] Header and threshing sounds; blood when it catches something
- [ ] A View Pilot LOD for the cab

## On the map (2026-11-24)

`BM_Wrecks` (scripts/4_World): at every server start, a share of each map's bulldozer and digger
wrecks and tower cranes are working machines instead (`$profile:BigMachines/BigMachinesSettings.json`:
BulldozerPercent / ExcavatorPercent / TowerCranePercent, 25% by default; FuelPercentMin/Max;
SpawnWithBattery, default off). Destroyed machines are cleared away at the start and new ones
take other wrecks' places, chosen at random. The site list (`BM_WreckSites.c`) is generated from
`data/construction_vehicles.csv` by `tools/make_sites.py`.

A machine remembers its wreck (saved, store version 2), which stays hidden while it exists.
Hidden = sunk 300 m underground on the server and on every client (map objects aren't networked;
the list goes to each player as they join), swept back down every second (DayZMolotov's method).
The wreck must be hidden as the machine loads (AfterStoreLoad), or physics shoves the machine out
of it before the mission starts: 1-3 m and up to 66 deg per restart, cranes 1 m across the mast.
The bulldozer wreck's blade is at its back (yaw offset 180); the digger faces like ours.

Verified: Chernarus in game (wrecks gone up close, machines and cranes in place, the Prigorodki
crane at the building site), positions held across restarts, nothing new spawned while enough
remain; Livonia 4+6, Sakhal 6+6+1, Nasdara 17+13+3 placed headless, every listed wreck found,
all 33 Nasdara machines settled where put. On a client, wrecks outside the player's loaded area
can't be moved, so they're "re-sunk" every second until the player comes near: harmless.

To do:
- [ ] Modded maps: no site list (could scan for the wreck models at the first start)
- [ ] A wreck can show for up to a second as a player first comes near (client sweep)

## Main sites

Coordinates are x / z.

- **Chernarus**: Krasnaya Zarya quarry by Severograd 8633/13302 (4 dozers, 3 diggers);
  Prigorodki 8009/3065; Kamensk 7087/14593; Zabolote 1968/10003; Orlovets 11559/7433.
- **Livonia**: Maksymilian quarry by Nadbor 6617/4832 (8 haul trucks, 2 mining excavators,
  11 diggers, 2 dozers); Radunin 7505/6136; Brena 6421/11403.
- **Sakhal**: Zvezdny Nikel mine by Sakhalag 12072/10388 (3 mining excavators, 4 haul trucks);
  Rudnogorsk 13633/11834; geothermal plant 8524/10326; Severomorsk 9231/13734.
- **Nasdara**: Sarman-Naft refinery 10726/6618; Nasdar-Beton factory 9731/6344; Karkhana
  District 9003/4229; Dashtabad Airbase 12332/11347 (crawler cranes); OKB-754 7292/10248.
