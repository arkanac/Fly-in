import argparse
import sys
from pydantic import ValidationError
from src.graphics.graphic import Display
from src.parser import Parsing, Graph, ZoneType
from src.simulation import Pathfinder

DEFAULT_MAP = "maps/medium/02_circular_loop.txt"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_path", nargs="?", default=DEFAULT_MAP)
    return parser.parse_args()


def print_drone_movements(path_list: list, total_turns: int, graph: Graph) -> None:
    for turn in range(1, total_turns + 1):
        movements = []
        for d_idx, path in enumerate(path_list, start=1):
            previous = "start"
            for (t, zone_name) in path:
                if t == turn:
                    movements.append(f"D{d_idx}-{zone_name}")
                elif t == turn + 1 and graph.zones[zone_name].zone == ZoneType.RESTRICTED:
                    neighbor_list = graph.get_neighbors(zone_name)
                    for connection, neighbor in neighbor_list:
                        if neighbor.name == previous:
                            movements.append(f"D{d_idx}- Moving from "
                                             f"{previous} to {neighbor.name}")
                previous = zone_name
        if movements:
            print(" ".join(movements))


def run_simulation(map_path: str) -> None:
    parse = Parsing(map_path)
    graph = parse.graph
    pathfinder = Pathfinder(parse.graph)
    path_list = pathfinder.routing()

    longest_path = max(path_list, key=lambda path: path[-1][0])
    total_turns = longest_path[-1][0]
    print_drone_movements(path_list, total_turns, graph)

    display = Display(parse.graph)
    display.create_network(path_list, total_turns)




def main() -> None:
    args = parse_arguments()
    try:
        run_simulation(args.map_path)
    except ValidationError as e:
        for error in e.errors():
            print(f"ERROR: {error['loc'][0]} - {error['msg']}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
