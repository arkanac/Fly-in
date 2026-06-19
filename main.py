from src.parser import Parsing, Graph, Zone
from pydantic import ValidationError
from src.graphic import Display
from src.simulation import Pathfinder


def main():
    try:
        parse = Parsing("/home/rem/Fly-in/maps/hard/01_maze_nightmare.txt")
        graph = parse.graph
        pf = Pathfinder(graph)
        path_list = pf.routing()
        turns = max(path_list, key=lambda p: (p[-1][0]))
        total_turns = turns[-1][0]
        d = Display(graph)
        d.create_network()
        for t in range(total_turns + 1):
            d.show_drones()

    except ValidationError as e:
        for error in e.errors():
            print(f"ERROR: {error['loc'][0]} - {error['msg']}")
            exit(1)
    except Exception as e:
        print(e)
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
