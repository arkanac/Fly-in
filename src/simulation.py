import heapq
from src.parser import Graph, Zone, ZoneType


class Drone:
    """Represents a drone navigating through the time-expanded network."""

    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        self.path: list[Zone] = []
        self.drone_id: int = drone_id
        self.current_zone: Zone = current_zone
        self.current_index: int = 0

    def move(self) -> None:
        """Advance the drone to its next position along the path."""
        self.current_index += 1
        self.current_zone = self.path[self.current_index]


class Pathfinder:
    """Space-time pathfinder maximizing priority lanes via Dijkstra."""

    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.zone_table: dict[tuple[int, str], int] = {}
        self.link_table: dict[tuple[str, str, int], int] = {}

    def link_key(self, zone1: str, zone2: str) -> tuple[str, str]:
        """Generate a unique deterministic key representing a spatial link."""
        if zone1 < zone2:
            return (zone1, zone2)
        return (zone2, zone1)

    def find_path(self) -> list[tuple[int, str]] | None:
        """Find the optimal space-time path for a single drone."""
        start_hub: str = next(z.name for z in self.graph.zones.values()
                              if z.is_start)
        end_hub: str = next(z.name for z in self.graph.zones.values()
                            if z.is_end)
        queue: list[tuple[float, int, str]] = [(0.0, 0, start_hub)]
        prev: dict[tuple[int, str], tuple[int, str] |
                   None] = {(0, start_hub): None}
        visited: set[tuple[int, str]] = set()

        while queue:
            accumulated_cost, turn, zone_name = heapq.heappop(queue)
            if (turn, zone_name) in visited:
                continue
            visited.add((turn, zone_name))
            if zone_name == end_hub:
                path: list[tuple[int, str]] = []
                state: tuple[int, str] | None = (turn, end_hub)
                while state is not None:
                    path.append(state)
                    state = prev[state]
                path.reverse()
                return path
            connection_list = self.graph.get_neighbors(zone_name)
            for connection, neighbor in connection_list:
                move_cost: int = self.graph.move_cost(neighbor)
                new_turn: int = turn + move_cost
                zone_count: int = self.zone_table.get(
                    (new_turn, neighbor.name), 0)
                if not neighbor.is_end and not neighbor.is_start:
                    if zone_count >= neighbor.max_drones:
                        continue
                k: tuple[str, str] = self.link_key(zone_name, neighbor.name)
                busy: bool = False
                for t in range(turn + 1, new_turn + 1):
                    if (self.link_table.get((k[0], k[1], t), 0) >=
                            connection.max_link_capacity):
                        busy = True
                        break
                if busy:
                    continue
                penalty: float = (0.0 if neighbor.zone ==
                                  ZoneType.PRIORITY else 0.001)
                next_one: tuple[float, int, str] = (
                    accumulated_cost + float(move_cost) + penalty,
                    new_turn, neighbor.name)
                heapq.heappush(queue, next_one)
                if (new_turn, neighbor.name) not in prev:
                    prev[(new_turn, neighbor.name)] = (turn, zone_name)
            if (self.graph.zones[zone_name].is_start or
                    self.graph.zones[zone_name].is_end):
                heapq.heappush(queue, (accumulated_cost + 1.0, turn +
                                       1, zone_name))
                if (turn + 1, zone_name) not in prev:
                    prev[(turn + 1, zone_name)] = (turn, zone_name)
            else:
                wait_count: int = self.zone_table.get((turn + 1, zone_name), 0)
                if wait_count < self.graph.zones[zone_name].max_drones:
                    heapq.heappush(queue, (accumulated_cost + 1.001,
                                           turn + 1, zone_name))
                    if (turn + 1, zone_name) not in prev:
                        prev[(turn + 1, zone_name)] = (turn, zone_name)
        return None

    def reserve_path(self, path: list[tuple[int, str]] | None) -> None:
        """Reserve resources along the given space-time path."""
        if path is None:
            return
        for state in path:
            self.zone_table[state] = self.zone_table.get(state, 0) + 1
        for (turn1, zone1), (turn2, zone2) in zip(path, path[1:]):
            if zone1 != zone2:
                key = self.link_key(zone1, zone2)
                for t in range(turn1 + 1, turn2 + 1):
                    link = (*key, t)
                    self.link_table[link] = self.link_table.get(link, 0) + 1

    def routing(self) -> list[list[tuple[int, str]]]:
        """Compute and reserve valid paths for all active drones."""
        path_list: list[list[tuple[int, str]]] = []
        for _ in range(self.graph.nb_drones):
            drone_path: list[tuple[int, str]] | None = self.find_path()
            if drone_path is None:
                raise Exception("No valid drone path found !")
            self.reserve_path(drone_path)
            path_list.append(drone_path)
        return path_list
