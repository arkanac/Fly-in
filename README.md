*This project has been created as part of the 42 curriculum by repichan.*

# Fly-in

## Description

Fly-in is a drone routing simulation. Given a map describing a network of
zones (hubs) connected by links, the program computes collision-free,
capacity-aware paths for a fleet of drones travelling from a single start
zone to a single end zone, then replays the result as a turn-by-turn
simulation with a graphical visualization built with `pygame`.

| Stage | Responsibility |
|---|---|
| **Parsing** | Reads the map file, validates syntax and constraints (zone types, capacities, duplicate connections, dashes in names, etc.) and builds an in-memory graph using `pydantic` models. |
| **Routing** | Computes, for every drone, a path from start to end that respects zone occupancy, link capacity, and movement costs, while avoiding conflicts with previously assigned paths. |
| **Display** | Renders the parsed network and animates the drones moving turn by turn inside a `pygame` window. |

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

If no map path is given, a map selection screen built with `pygame` lets
you pick a category (easy / medium / hard / challenger) and then a map
file from that category.

Once the simulation window is open, the network is drawn first (zones as
circles, connections as lines), and the drones then move from the start
zone to the end zone, one simulation turn at a time.

---

## Resources

| Topic | Link |
|---|---|
| Dijkstra's algorithm | [Wikipedia](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) |
| A* search algorithm | [Wikipedia](https://en.wikipedia.org/wiki/A*_search_algorithm) |
| pygame | [Documentation](https://www.pygame.org/docs/) |
| Pydantic | [Documentation](https://docs.pydantic.dev/) |
| pathlib | [Python docs](https://docs.python.org/3/library/pathlib.html) |

### AI usage

AI assistance (Claude) was used as a learning aid throughout this
project, primarily to:

- Explain algorithmic concepts (Dijkstra, time-expanded graph states,
  reservation tables) before writing the corresponding code.
- Point out bugs in code I had already written (e.g. an indentation
  issue that broke multi-drone routing) without providing the fix
  directly, so I could correct it myself.
- Clarify specific library behaviour (`pygame`, `pydantic`, `heapq`)
  through documentation lookups when needed.


---

## Algorithm choices and implementation strategy

### Parsing

The map file is parsed line by line. Each line is dispatched based on its
prefix (`nb_drones:`, `hub:`, `start_hub:`, `end_hub:`, `connection:`) to a
dedicated parsing method.

Zone and connection metadata (the optional `[key=value ...]` block) is
extracted in three steps:

1. Split the line on `[` to separate the fixed part from the metadata.
2. Split the fixed part on whitespace to get `name`, `x`, `y`.
3. Split each metadata token on `=` to get key/value pairs.

All extracted data is validated through `pydantic` models (`Zone`,
`Connection`, `Graph`), which enforce type-safety, positive capacities,
valid zone types, and custom constraints such as the absence of dashes in
zone names. A final `validate_graph` pass checks for exactly one
start/end zone, no duplicate coordinates, and a strictly positive drone
count.

### Pathfinding

Routing is performed with **Dijkstra's algorithm**, executed once per
drone, sequentially.

| Concept | Implementation |
|---|---|
| Search state | `(zone, turn)` pair instead of just `zone`, since the same zone can be visited at different turns by different drones |
| Zone capacity | `zone_table` records how many drones occupy a given zone at a given turn |
| Link capacity | `link_table` records how many drones use a given connection at a given turn |
| Waiting | Modelled as a valid move (staying in place for one turn), letting a drone yield to a bottleneck instead of failing |
| Start / end zones | Explicitly exempted from occupancy limits, since the subject allows drones to freely share both |
| Restricted zones | Cost two turns to enter instead of one, via a per-zone-type move cost function |

Before a move is explored, the algorithm checks both reservation tables to
confirm the destination zone and the connection used have available
capacity; otherwise the move is discarded. Once a drone's path is found,
it is reserved in both tables so the next drone's search accounts for it,
guaranteeing every capacity constraint is respected simultaneously across
all drones.

This sequential, reservation-based approach trades global optimality (the
true multi-agent optimal routing problem is NP-hard) for a tractable and
predictable algorithm that produces valid, conflict-free solutions in
polynomial time per drone.

### Display

The visualization is intentionally kept as a thin replay layer: it has no
knowledge of the pathfinding logic. `Display` receives the computed list
of paths and, for each simulation turn, looks up each drone's last known
position at or before that turn, then draws it. Zone coordinates are
converted to screen coordinates through a single shared scale factor
(computed from the map's bounding box and the window size) to avoid
distorting the network's proportions.

---

## Visual representation

The `pygame` window draws the static network first — zones as colored
circles (using each zone's declared color, or a default if none is
specified) and connections as black lines between them — then overlays
the drones as separate circles whose position is recomputed every turn.

This separation makes it easy to see, at a glance:

- Which zones are congested
- How drones are distributed across the available paths during a run

A map selection screen, also built with `pygame`, lets the user browse
and pick a map by category before the simulation starts, without needing
to pass a file path manually.