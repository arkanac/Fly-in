*This project has been created as part of the 42 curriculum by repichan.*

# Fly-in

## Description

Fly-in is a drone routing simulation. Given a map describing a network of
zones (hubs) connected by links, the program computes collision-free,
capacity-aware paths for a fleet of drones travelling from a single start
zone to a single end zone, then replays the result both as a turn-by-turn
console output and as an animated `pygame` visualization.

| Stage | Responsibility |
|---|---|
| **Parsing** | Reads the map file, validates syntax and constraints (zone types, capacities, duplicate connections, dashes in names, etc.) and builds an in-memory graph using `pydantic` models. |
| **Routing** | Computes, for every drone, a path from start to end that respects zone occupancy, link capacity, and movement costs, while avoiding conflicts with previously assigned paths. |
| **Display** | Prints the turn-by-turn movements in the required format, then renders the network and animates the drones inside a `pygame` window. |

---

## Instructions

The project uses `uv` for dependency management.

| Command | Description |
|---|---|
| `make install` | Installs the project dependencies |
| `make run` | Runs the simulation |
| `make debug` | Runs the simulation under `pdb` |
| `make lint` | Runs `flake8` and `mypy` |
| `make lint-strict` | Runs `flake8` and `mypy --strict` |
| `make clean` | Removes caches and temporary files |

Run the simulation on a specific map:

```bash
uv run python main.py maps/easy/01_linear_path.txt
```

If no map path is given, the program falls back to a default map.

The console output is printed first, then the `pygame` window opens: the
network is drawn (zones as shapes, connections as lines) and the drones
move from the start zone to the end zone, one simulation turn per second.
Scroll to zoom, click and drag to pan.

---

## Example input and expected output

Input map (`maps/easy/01_linear_path.txt`, simplified):

```
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: waypoint1 2 0
hub: waypoint2 4 0
end_hub: goal 6 0 [color=yellow]
connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Expected output:

```
D1-waypoint1 D2-start
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each line is one simulation turn and lists every movement that happens
during that turn, space-separated. Drones that do not move are omitted
from the line, and drones that reached the end zone are no longer
tracked. Here the single corridor has a capacity of one drone per zone,
so `D2` waits one turn on the start hub before following `D1`.

### Movement toward a restricted zone

Entering a `restricted` zone costs two turns. While a drone is in transit
on the connection, it is displayed as `D<ID>-<origin>-<destination>`.
Connections have no name of their own in the map format, so the pair of
zone names is used as the connection identifier:

```
D1-corridorA
D1-corridorA-roof1
D1-roof1
```

---

## Resources

| Topic | Link |
|---|---|
| Dijkstra's algorithm | [Wikipedia](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) |
| Time-expanded graphs | [Wikipedia](https://en.wikipedia.org/wiki/Time-expanded_graph) |
| `heapq` (binary heap) | [Python docs](https://docs.python.org/3/library/heapq.html) |
| pygame | [Documentation](https://www.pygame.org/docs/) |
| Pydantic | [Documentation](https://docs.pydantic.dev/) |

### AI usage

AI was used for:

- Explaining algorithmic concepts (Dijkstra, time-expanded graph states,
  reservation tables) before writing the corresponding code.
- Pointing out bugs in code I had already written (e.g. an indentation
  issue that broke multi-drone routing) without providing the fix
  directly, so I could correct it myself.
- Clarifying specific library behaviour (`pygame`, `pydantic`, `heapq`)
  through documentation lookups when needed.
- Implementing two display details: the animated rainbow color and the
  click-and-drag panning.

---

## Algorithm choices and implementation strategy

### Parsing

The map file is parsed line by line. Each line is dispatched based on its
prefix (`nb_drones:`, `hub:`, `start_hub:`, `end_hub:`, `connection:`) to a
dedicated parsing method. Empty lines and lines starting with `#` are
skipped.

Zone and connection metadata (the optional `[key=value ...]` block) is
extracted in three steps:

1. Split the line on `[` to separate the fixed part from the metadata.
2. Split the fixed part on whitespace to get `name`, `x`, `y`.
3. Split each metadata token on `=` to get key/value pairs.

All extracted data is validated through `pydantic` models (`Zone`,
`Connection`, `Graph`), which enforce type-safety, positive capacities,
valid zone types, and custom constraints such as the absence of dashes in
zone names — dashes being the separator used by the `connection:` syntax.
A final `validate_graph` pass checks for exactly one start zone, exactly
one end zone, no duplicate coordinates, and a strictly positive drone
count.

### Pathfinding

Routing is performed with **Dijkstra's algorithm on a time-expanded
graph**, executed once per drone, sequentially.

| Concept | Implementation |
|---|---|
| Search state | `(turn, zone)` pair instead of just `zone`, since the same zone is a different resource at different turns |
| Zone capacity | `zone_table` records how many drones occupy a given zone at a given turn |
| Link capacity | `link_table` records how many drones use a given connection at a given turn, keyed on the two zone names sorted alphabetically so that `A-B` and `B-A` share one counter |
| Waiting | Modelled as an explicit edge toward `(turn + 1, same zone)`, letting a drone yield to a bottleneck instead of failing |
| Start / end zones | Exempted from occupancy limits, since the subject states that `max_drones` is ignored on both |
| Restricted zones | Cost two turns to enter instead of one, via a per-zone-type move cost function |
| Blocked zones | Filtered out at the graph level: `get_neighbors` never returns them, so no path can traverse one |
| Priority zones | Preferred through a fractional penalty (see below) |

**Preferring priority zones.** Movement costs are integers, so two
different routes often reach the end in the same number of turns. Every
move toward a non-priority zone therefore carries an extra `0.001`
penalty in the Dijkstra cost. The penalty is small enough that it can
never change the turn count of the chosen path, but it breaks ties in
favour of routes going through `priority` zones. Waiting carries a
slightly higher penalty than moving, so a drone only stalls when it has
to.

**Reservation.** Before a move is explored, the algorithm checks both
reservation tables to confirm the destination zone and the connection
used have available capacity; otherwise the move is discarded. Once a
drone's path is found, it is reserved in both tables so the next drone's
search accounts for it, guaranteeing every capacity constraint is
respected simultaneously across all drones.

**Complexity.** One Dijkstra run costs `O(E log V)` over the
time-expanded graph, and the routine runs once per drone, giving
`O(nb_drones * E log V)`. Paths are computed once and stored, never
recomputed: the display layer only replays them. Memory is dominated by
the two reservation tables, which hold one entry per occupied
`(turn, zone)` and `(turn, link)` pair — proportional to the total length
of all paths rather than to the size of the time-expanded graph.

This sequential, reservation-based approach trades global optimality (the
true multi-agent routing problem is NP-hard) for a tractable and
predictable algorithm that produces valid, conflict-free solutions.

### Object-oriented design

The whole project is class-based, and two design choices are worth
highlighting:

- **Pydantic models as the domain layer.** `Zone`, `Connection` and
  `Graph` are not plain data holders: `Graph` owns the graph operations
  (`get_neighbors`, `move_cost`), so the movement rules of the world live
  with the data they apply to.
- **Strategy pattern for rendering.** `ZoneRenderer` is an abstract base
  class with one concrete subclass per zone type, and `Display` holds a
  `ZoneType -> renderer` dictionary with a default fallback. Adding a new
  zone type means adding a class and one dictionary entry, without
  touching the render loop.

### Display

The visualization is intentionally kept as a thin replay layer: it has no
knowledge of the pathfinding logic. `Display` receives the computed list
of paths and, for each simulation turn, looks up each drone's position at
that turn, then draws it. Zone coordinates are converted to screen
coordinates through a single shared scale factor, computed from the map's
bounding box and the window size, so the network's proportions are never
distorted. Turns advance on a `pygame` timer event rather than on the
frame rate, keeping the animation speed independent of rendering
performance.

---

## Visual representation

Each zone type is drawn as a distinct shape, so the constraints of the
map are readable without consulting the file:

| Zone type | Shape |
|---|---|
| `normal` | Circle |
| `restricted` | Square |
| `blocked` | Diamond |
| `priority` | Star |

Zones use their declared color, or blue by default; the special value
`rainbow` animates the fill through the color wheel. Connections are
drawn as lines whose thickness is proportional to their
`max_link_capacity`, making bottlenecks visible at a glance. Drones are
black circles overlaid on top, and a drone in transit toward a restricted
zone is drawn at the midpoint of the connection — the visual counterpart
of the `D<ID>-<origin>-<destination>` console notation.

Every zone displays a live `current/maximum` occupancy label, which turns
red when the zone is saturated. The start and end hubs show the total
fleet size as their denominator instead, since they have no capacity
limit: the counter drains from `n/n` on the start hub and fills back up
to `n/n` on the end hub as drones are delivered.

Together these cues make it possible to see, during a run:

- Which zones are congested and which links are saturated
- How drones are distributed across the available routes
- Why a drone is waiting rather than moving
- How many drones have already been delivered

The view can be zoomed with the mouse wheel and panned by dragging, which
matters on the larger hard and challenger maps.