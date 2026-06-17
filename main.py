from parser import Parsing, Graph
from pydantic import ValidationError
from graphic import Display


def main():
    try:
        parse = Parsing("/home/rem/Fly-in/maps/medium/03_priority_puzzle.txt")
        d = Display(Graph)
        d.show_smg()

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
