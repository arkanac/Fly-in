import argparse
import sys
from pydantic import ValidationError
from src import Parsing, Graph, Pathfinder, Display, ZoneType

DEFAULT_MAP: str = "maps/hard/01_maze_nightmare.txt"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the drone simulation network."""
    parser = argparse.ArgumentParser()
    parser.add_argument("map_path", nargs="?", default=DEFAULT_MAP)
    return parser.parse_args()


def print_drone_movements(path_list: list[list[tuple[int, str]]],
                          total_turns: int, graph: Graph,) -> None:
    """Print the synchronized step-by-step drone movements in the console."""
    for turn in range(1, total_turns + 1):
        movements: list[str] = []
        for d_idx, path in enumerate(path_list, start=1):
            previous: str = "start"
            for t, zone_name in path:
                if t == turn:
                    movements.append(f"D{d_idx}-{zone_name}")
                elif (t == turn + 1 and graph.zones[zone_name].zone ==
                      ZoneType.RESTRICTED):
                    neighbor_list = graph.get_neighbors(zone_name)
                    for connection, neighbor in neighbor_list:
                        if neighbor.name == previous:
                            movements.append(
                                f"D{d_idx}-{previous}-{zone_name}")
                previous = zone_name
        if movements:
            print(" ".join(movements))


def run_simulation(map_path: str) -> None:
    """
    Execute the pathfinding routing and run the visual network simulation."""
    parse = Parsing(map_path)
    graph: Graph = parse.graph
    pathfinder = Pathfinder(parse.graph)
    path_list: list[list[tuple[int, str]]] = pathfinder.routing()
    longest_path: list[tuple[int, str]] = max(
        path_list, key=lambda path: path[-1][0])
    total_turns: int = longest_path[-1][0]
    print_drone_movements(path_list, total_turns, graph)
    display = Display(parse.graph)
    display.create_network(path_list, total_turns)


def main() -> None:
    """Entry point of the program handling configuration and validations."""
    args: argparse.Namespace = parse_arguments()
    try:
        run_simulation(args.map_path)
    except ValidationError as e:
        for error in e.errors():
            print(f"ERROR: {error['loc'][0]} - {error['msg']}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
