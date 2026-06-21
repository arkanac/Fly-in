from typing import NamedTuple
from src.parser import Zone
try:
    import pygame
except ImportError as e:
    raise (e)


class ScreenTransform(NamedTuple):
    factor: int
    middle: tuple[int, int]
    screen_middle: tuple[int, int]


class Display:
    def __init__(self, graph):
        self.graph = graph
        self.running = True
        self.middle = []
        self.current_turn = 0

    def coordinate_calculation(self):
        max_y = max(self.graph.zones.values(), key=lambda zone: zone.y).y
        max_x = max(self.graph.zones.values(), key=lambda zone: zone.x).x
        min_y = min(self.graph.zones.values(), key=lambda zone: zone.y).y
        min_x = min(self.graph.zones.values(), key=lambda zone: zone.x).x
        x_amplitude = max((max_x - min_x), 1)
        y_amplitude = max((max_y - min_y), 1)
        middle_x = (min_x + max_x) / 2
        middle_y = (min_y + max_y) / 2
        screen_size = self.screen.get_size()
        screen_middle_x = screen_size[0] // 2
        screen_middle_y = screen_size[1] // 2
        x = screen_size[0]
        y = screen_size[1]
        x -= (x//10)
        y -= (y//10)
        x_coord = x // x_amplitude
        y_coord = y // y_amplitude
        factor = min(x_coord, y_coord)
        return ScreenTransform(factor, (middle_x, middle_y), (screen_middle_x,
                                                              screen_middle_y))

    def zone_to_screen(self, zone: Zone, screen:
                       ScreenTransform) -> tuple[int, int]:
        pos_x = screen.screen_middle[0] + (zone.x -
                                           screen.middle[0]) * screen.factor
        pos_y = screen.screen_middle[1] + (zone.y -
                                           screen.middle[1]) * screen.factor
        return (pos_x, pos_y)

    def create_network(self, path_list: list[list[tuple[int, str]]],
                       total_turns: int):
        pygame.init()
        self.screen = pygame.display.set_mode()
        self.coords = self.coordinate_calculation()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            self.screen.fill((255, 255, 255))
            for connection in self.graph.connection:
                width = int(connection.max_link_capacity)
                start = connection.name_1
                stop = connection.name_2
                start_point = self.zone_to_screen(start, self.coords)
                stop_point = self.zone_to_screen(stop, self.coords)
                pygame.draw.line(self.screen, "black", start_point, stop_point,
                                 width)
            for zone in self.graph.zones.values():
                zone_coord = self.zone_to_screen(zone, self.coords)
                zone_color = zone.color if zone.color is not None else "blue"
                pygame.draw.circle(self.screen, "black",
                                   [zone_coord[0], zone_coord[1]], 45, 0)
                pygame.draw.circle(self.screen, zone_color,
                                   [zone_coord[0], zone_coord[1]], 40, 0)
            self.show_drones(path_list, total_turns, self.current_turn)
            pygame.display.flip()
            pygame.time.wait(1000)
            if self.current_turn <= total_turns:
                self.current_turn += 1
        pygame.quit()

    def show_drones(self, path_list: list[list[tuple[int, str]]],
                    total_turns: int, current_turn: int) -> None:
        for path in path_list:
            drone_pos = None
            for (t, zone_name) in path:
                if t <= total_turns and t <= current_turn:
                    zone = self.graph.zones[zone_name]
                    drone_pos = self.zone_to_screen(zone, self.coords)
            if drone_pos is not None:
                pygame.draw.circle(self.screen, "black", drone_pos, 20, 0)
