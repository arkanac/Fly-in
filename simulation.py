from parser import Zone, Graph
import heapq


class Drone:
    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        self.path: list[Zone] = []
        self.drone_id: int = drone_id
        self.current_zone = current_zone
        self.current_index = 0

    def move(self) -> None:
        self.current_index += 1
        self.current_zone = self.path[self.current_index]


class Pathfinder:
    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.zone_table: dict[tuple[int, str], int] = {}
        self.link_table: dict[tuple[str, str, int], int] = {}

    def find_path(self) -> list[tuple[int, str]] | None:
        start_hub = next(z.name for z in self.graph.zones.values()
                         if z.is_start)
        end_hub = next(z.name for z in self.graph.zones.values()
                       if z.is_end)
        queue = [(0, start_hub)]
        prev: dict[tuple[int, str], tuple[int, str] | None
                   ] = {(0, start_hub): None}
        visited: set = set()
        while queue:
            turn, zone_name = heapq.heappop(queue)
            if (turn, zone_name) in visited:
                continue
            visited.add((turn, zone_name))
            if zone_name == end_hub:
                path = []
                state: tuple[int, str] | None = (turn, end_hub)
                while state is not None:
                    path.append(state)
                    state = prev[state]
                path.reverse()
                return path
            connection_list = self.graph.get_neighbors(zone_name)
            for connection, neighbor in connection_list:
                new_turn = turn + self.graph.move_cost(neighbor)
                zone_count = self.zone_table.get((new_turn, neighbor.name), 0)
                if zone_count >= neighbor.max_drones:
                    continue
                link_count = self.link_table.get((connection.name_1.name,
                                                  connection.name_2.name,
                                                  turn + 1), 0)
                if link_count >= connection.max_link_capacity:
                    continue
                next_one = (new_turn, neighbor.name)
                heapq.heappush(queue, next_one)
                prev[(new_turn, neighbor.name)] = (turn, zone_name)
            wait_count = self.zone_table.get((turn + 1, zone_name), 0)
            if wait_count < self.graph.zones[zone_name].max_drones:
                heapq.heappush(queue, (turn + 1, zone_name))
                if (turn + 1, zone_name) not in prev:
                    prev[(turn + 1, zone_name)] = (turn, zone_name)
        return None

    def reserve_path(self, path: list[tuple[int, str]] | None) -> None:
        if path is None:
            return
        for state in path:
            self.zone_table[state] = self.zone_table.get(state, 0) + 1
        for (turn1, zone1), (turn2, zone2) in zip(path, path[1:]):
            if zone1 != zone2:
                link = (zone1, zone2, turn1)
                self.link_table[link] = self.link_table.get(link, 0) + 1

    def routing(self) -> list[list[tuple[int, str]]]:
        path_list = []
        for _ in range(self.graph.nb_drones):
            drone_path = self.find_path()
            if drone_path is None:
                raise Exception("No valid drone path found !")
            self.reserve_path(drone_path)
            path_list.append(drone_path)
        return path_list
