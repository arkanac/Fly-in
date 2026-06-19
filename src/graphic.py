from typing import NamedTuple
from src.parser import Zone

try:
    import pygame
except ImportError as e:
    raise e


class ScreenTransform(NamedTuple):
    factor: float
    middle: tuple[float, float]
    screen_middle: tuple[int, int]

    @classmethod
    def calculate(cls, graph, screen_size: tuple[int, int]) -> "ScreenTransform":
        """Calculates the scaling factor and centers based on graph coordinates and screen size."""
        zones = graph.zones.values()
        
        x_coords = [zone.x for zone in zones]
        y_coords = [zone.y for zone in zones]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        x_amplitude = max((max_x - min_x), 1)
        y_amplitude = max((max_y - min_y), 1)

        middle_x = (min_x + max_x) / 2
        middle_y = (min_y + max_y) / 2

        screen_w, screen_h = screen_size
        screen_middle_x = screen_w // 2
        screen_middle_y = screen_h // 2

        usable_w = screen_w - (screen_w // 10)
        usable_h = screen_h - (screen_h // 10)

        factor = min(usable_w // x_amplitude, usable_h // y_amplitude)

        return cls(factor, (middle_x, middle_y), (screen_middle_x, screen_middle_y))

    def transform(self, zone: Zone) -> tuple[int, int]:
        """Transforms a zone's logical coordinates into screen pixel coordinates."""
        pos_x = self.screen_middle[0] + (zone.x - self.middle[0]) * self.factor
        pos_y = self.screen_middle[1] + (zone.y - self.middle[1]) * self.factor
        return int(pos_x), int(pos_y)


class Display:
    def __init__(self, graph):
        self.graph = graph
        self.running = True
        self.screen = None

    def _handle_events(self) -> None:
        """Processes pygame events to handle application lifecycle."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _render(self, transform: ScreenTransform) -> None:
        """Renders the connections and zones onto the screen."""
        self.screen.fill((255, 255, 255))

        for connection in self.graph.connection:
            start_point = transform.transform(connection.name_1)
            stop_point = transform.transform(connection.name_2)
            pygame.draw.line(self.screen, "black", start_point, stop_point)

        for zone in self.graph.zones.values():
            zone_coord = transform.transform(zone)
            zone_color = zone.color if zone.color is not None else "blue"
            pygame.draw.circle(self.screen, zone_color, zone_coord, 40, 0)

        pygame.display.flip()

    def create_network(self) -> None:
        """Initializes the window and runs the main application loop."""
        pygame.init()
        self.screen = pygame.display.set_mode()
        
        transform = ScreenTransform.calculate(self.graph, self.screen.get_size())

        while self.running:
            self._handle_events()
            self._render(transform)
        pygame.quit()

    def show_drones(self, path_list: list[list[tuple[int, str]]], turn: int) -> None:
        for path in path_list:
            for (t, zone_name) in path:
                zone = zone_name
