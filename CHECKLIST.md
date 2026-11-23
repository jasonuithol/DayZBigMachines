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

Maybe later (farm machinery and port equipment, not construction):
tractor `Land_Wreck_Tractor` (49 / 81 / 69 / 75), combine harvester `Land_Wreck_Harverster`
(31 / 53 / 5 / 0), harbour cranes `Land_Pier_Crane_A/B` (23 / 0 / 14 / 3), Sakhal's
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
| 1 Bulldozer | [x] v0.2, FAT livery decals, flat paint | [x] blade | [x] | [x] blade keys | [~] MS3 truck sounds | [ ] | [~] see below |
| 2 Excavator | [x] v0.2, FAT livery decals, flat paint | [x] slew, boom, stick, bucket | [x] | [x] | [~] MS3 truck sounds | [ ] | [~] see below |
| 3 Mining excavator | [ ] | [ ] slew, boom, bucket | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 Mining haul truck | [ ] | [ ] tipper | [ ] | [ ] | [ ] | [ ] | [ ] |
| 5 Crawler crane | [ ] | [ ] slew, boom, hook | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 Tower crane (fixed; operate, not drive) | [ ] | [ ] slew, trolley, hook | [ ] | [ ] | [ ] | [ ] | [ ] |
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
  the track frame (blender/crawler.py); they don't turn yet
- [ ] Textures (weathered paint, track links) instead of flat colours; a View Pilot LOD for the cab
- [ ] Track animation (texture scroll or moving links) and turning sprockets
- [ ] Turn on the spot (skid steer) instead of car-style steering
- [x] Keep the blade position across restarts (every joint is saved; checked on the excavator)
- [ ] Replace the map's static Wreck_Bulldozer objects with working machines (all 4 maps)
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
- [ ] Textures (weathered paint); a View Pilot LOD for the cab
- [ ] Digging: something for the bucket to pick up or move (dirt piles, loose items)
- [x] Drive along the tracks, not the cab, after a slew (found in the first playtest;
  Autobot: slewed 94 deg, drove 6.6 m at 69.7 deg with the tracks at 70.1; reverse, steering,
  pivot turns; server and client agree)
- [ ] Engine sound: the wheels spin freely, so it revs to ~2300 rpm on throttle whatever the
  ground speed
- [ ] Replace the map's static Wreck_Digger objects with working machines (all 4 maps)

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
