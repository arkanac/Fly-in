from parser import Zone


class Drone:
    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        self.path: list[Zone] = []
        self.drone_id: int = drone_id
        self.current_zone = current_zone
        self.current_index = 0

    def move(self) -> None:
        self.current_index += 1
        self.current_zone = self.path[self.current_index]

