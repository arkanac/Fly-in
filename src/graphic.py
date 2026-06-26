"""Pygame-based display module for the Fly-in drone simulation."""

from abc import ABC, abstractmethod
from typing import NamedTuple
import math
import pygame
from src.parser import Zone, ZoneType, Graph

ColorType = pygame.Color | str | tuple[int, int, int]


class ScreenTransform(NamedTuple):
    """Hold the screen-space transform parameters for coordinate conversion.

    Attributes:
        factor: Pixels per map unit.
        middle: Centre of the map in map coordinates (x, y).
        screen_middle: Centre of the screen in pixels (x, y).
    """

    factor: int
    middle: tuple[int | float, int | float]
    screen_middle: tuple[int, int]


class ColorResolver:
    """Resolve a zone's display color, including rainbow animation."""

    @staticmethod
    def resolve(zone: Zone, ticks: int) -> ColorType:
        """Return the display color for *zone* at the given *ticks* time.

        Args:
            zone: The zone whose color is resolved.
            ticks: Milliseconds since pygame was initialised (for animation).

        Returns:
            A pygame-compatible color value.
        """
        if zone.color == "rainbow":
            r = int((math.sin(ticks * 0.003) + 1) * 127.5)
            g = int((math.sin(ticks * 0.003 + 2) + 1) * 127.5)
            b = int((math.sin(ticks * 0.003 + 4) + 1) * 127.5)
            return (r, g, b)

        base_color: str = zone.color if zone.color else "blue"
        try:
            pygame.Color(base_color)
            return base_color
        except ValueError:
            return "blue"


class ZoneRenderer(ABC):
    """Abstract base class for zone shape renderers."""

    @abstractmethod
    def draw(self, screen: pygame.Surface, x: int, y: int, r: int, r_out: int,
             color: ColorType, scale: float) -> None:
        """Draw the zone shape on *screen*.

        Args:
            screen: Target pygame surface.
            x: Screen x coordinate of the zone centre.
            y: Screen y coordinate of the zone centre.
            r: Inner radius in pixels.
            r_out: Outer (border) radius in pixels.
            color: Fill color.
            scale: Current zoom scale factor.
        """


class RestrictedRenderer(ZoneRenderer):
    """Render a restricted zone as a filled rectangle with a black border."""

    def draw(self, screen: pygame.Surface, x: int, y: int, r: int, r_out: int,
             color: ColorType, scale: float) -> None:
        """Draw a restricted zone rectangle.

        Args:
            screen: Target pygame surface.
            x: Screen x coordinate of the zone centre.
            y: Screen y coordinate of the zone centre.
            r: Inner rectangle half-size in pixels.
            r_out: Outer rectangle half-size in pixels.
            color: Fill color.
            scale: Current zoom scale factor.
        """
        pygame.draw.rect(screen, "black", (x - r_out, y - r_out, r_out * 2,
                                           r_out * 2), 0)
        pygame.draw.rect(screen, color, (x - r, y - r, r * 2, r * 2), 0)


class BlockedRenderer(ZoneRenderer):
    """Render a blocked zone as a filled diamond with a black border."""

    def draw(self, screen: pygame.Surface, x: int, y: int, r: int, r_out: int,
             color: ColorType, scale: float) -> None:
        """Draw a blocked zone diamond.

        Args:
            screen: Target pygame surface.
            x: Screen x coordinate of the zone centre.
            y: Screen y coordinate of the zone centre.
            r: Unused (kept for interface compatibility).
            r_out: Unused (kept for interface compatibility).
            color: Fill color.
            scale: Current zoom scale factor.
        """
        ro = int(50 * scale)
        ri = int(42 * scale)
        pts_out = [(x, y - ro), (x + ro, y), (x, y + ro), (x - ro, y)]
        pts_in = [(x, y - ri), (x + ri, y), (x, y + ri), (x - ri, y)]
        pygame.draw.polygon(screen, "black", pts_out, 0)
        pygame.draw.polygon(screen, color, pts_in, 0)


class PriorityRenderer(ZoneRenderer):
    """Render a priority zone as a star polygon with a coloured centre."""

    def draw(self, screen: pygame.Surface, x: int, y: int, r: int, r_out: int,
             color: ColorType, scale: float) -> None:
        """Draw a priority zone star.
        Args:
            screen: Target pygame surface.
            x: Screen x coordinate of the zone centre.
            y: Screen y coordinate of the zone centre.
            r: Unused (kept for interface compatibility).
            r_out: Unused (kept for interface compatibility).
            color: Fill color for the inner circle.
            scale: Current zoom scale factor.
        """
        pts_out: list[tuple[int, int]] = []
        pts_in: list[tuple[int, int]] = []
        r_xo, r_xi = int(55 * scale), int(50 * scale)
        r_io, r_ii = int(25 * scale), int(20 * scale)
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            if i % 2 == 0:
                pts_out.append((
                    x + int(r_xo * math.cos(angle)),
                    y + int(r_xo * math.sin(angle))))
                pts_in.append((
                    x + int(r_xi * math.cos(angle)),
                    y + int(r_xi * math.sin(angle))))
            else:
                pts_out.append((
                    x + int(r_io * math.cos(angle)),
                    y + int(r_io * math.sin(angle))))
                pts_in.append((
                    x + int(r_ii * math.cos(angle)),
                    y + int(r_ii * math.sin(angle))))
        pygame.draw.polygon(screen, "black", pts_out, 0)
        pygame.draw.polygon(screen, "yellow", pts_in, 0)
        pygame.draw.circle(screen, "black", [x, y], int(18 * scale), 0)
        pygame.draw.circle(screen, color, [x, y], int(15 * scale), 0)


class NormalRenderer(ZoneRenderer):
    """Render a normal zone as a filled circle with a black border."""

    def draw(self, screen: pygame.Surface, x: int, y: int, r: int, r_out: int,
             color: ColorType, scale: float) -> None:
        """Draw a normal zone circle.

        Args:
            screen: Target pygame surface.
            x: Screen x coordinate of the zone centre.
            y: Screen y coordinate of the zone centre.
            r: Inner radius in pixels.
            r_out: Outer (border) radius in pixels.
            color: Fill color.
            scale: Current zoom scale factor.
        """
        pygame.draw.circle(screen, "black", (x, y), r_out, 0)
        pygame.draw.circle(screen, color, (x, y), r, 0)


class Display:
    """Manage the pygame window, event loop, and simulation rendering."""

    def __init__(self, graph: Graph) -> None:
        """Initialise display state for the given routing graph.

        Args:
            graph: The parsed and routed graph to visualise.
        """
        self.graph = graph
        self.running = True
        self.current_turn = 0
        self.zoom_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.spacing_multiplier = 2.0
        self.total_turns = 0

        self.renderers: dict[ZoneType, ZoneRenderer] = {
            ZoneType.RESTRICTED: RestrictedRenderer(),
            ZoneType.BLOCKED: BlockedRenderer(),
            ZoneType.PRIORITY: PriorityRenderer()}
        self.default_renderer: ZoneRenderer = NormalRenderer()

    def coordinate_calculation(self) -> ScreenTransform:
        """Compute the scale factor and centres from the graph bounding box.

        Returns:
            A ScreenTransform with the computed factor, map centre, and
            screen centre.
        """
        max_y = max(self.graph.zones.values(), key=lambda z: z.y).y
        max_x = max(self.graph.zones.values(), key=lambda z: z.x).x
        min_y = min(self.graph.zones.values(), key=lambda z: z.y).y
        min_x = min(self.graph.zones.values(), key=lambda z: z.x).x
        x_amp = max((max_x - min_x), 1)
        y_amp = max((max_y - min_y), 1)
        middle_x = (min_x + max_x) / 2
        middle_y = (min_y + max_y) / 2
        sz = self.screen.get_size()
        x, y = sz[0] - (sz[0] // 10), sz[1] - (sz[1] // 10)
        factor = int(min(x // x_amp, y // y_amp) * self.spacing_multiplier)
        return ScreenTransform(
            factor, (middle_x, middle_y), (sz[0] // 2, sz[1] // 2),)

    def zone_to_screen(
        self, zone: Zone, screen: ScreenTransform,
    ) -> tuple[int, int]:
        """Convert map coordinates of *zone* to screen pixels.

        Args:
            zone: The zone whose position is converted.
            screen: The current screen transform.

        Returns:
            A (x, y) pixel coordinate tuple.
        """
        base_x = (screen.screen_middle[0] +
                  (zone.x - screen.middle[0]) * screen.factor)
        base_y = (screen.screen_middle[1] +
                  (zone.y - screen.middle[1]) * screen.factor)
        pos_x = int(screen.screen_middle[0] +
                    (base_x - screen.screen_middle[0]) * self.zoom_scale +
                    self.offset_x)
        pos_y = int(screen.screen_middle[1] +
                    (base_y - screen.screen_middle[1]) * self.zoom_scale +
                    self.offset_y)
        return (pos_x, pos_y)

    def _handle_events(self) -> None:
        """Process pygame events for the current frame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.USEREVENT + 1:
                if self.current_turn < self.total_turns:
                    self.current_turn += 1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.dragging = True
                elif event.button == 4:
                    self.zoom_scale *= 1.1
                elif event.button == 5:
                    self.zoom_scale /= 1.1
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                dx, dy = event.rel
                self.offset_x += dx
                self.offset_y += dy

    def create_network(self, path_list: list[list[tuple[int, str]]],
                       total_turns: int) -> None:
        """Initialise pygame and run the main render loop.

        Args:
            path_list: Precomputed drone paths as (turn, zone_name) lists.
            total_turns: Total number of simulation turns.
        """
        pygame.init()
        font = pygame.font.SysFont("Arial", 24)
        small_font = pygame.font.SysFont("Arial", 14)
        self.total_turns = total_turns
        self.screen = pygame.display.set_mode()
        self.coords = self.coordinate_calculation()
        pygame.time.set_timer(pygame.USEREVENT + 1, 1000)

        while self.running:
            self._handle_events()
            self.screen.fill((255, 255, 255))
            r = int(40 * self.zoom_scale)
            r_out = int(45 * self.zoom_scale)

            for connection in self.graph.connection:
                width = max(
                    1, int(connection.max_link_capacity * self.zoom_scale))
                p1 = self.zone_to_screen(connection.name_1, self.coords)
                p2 = self.zone_to_screen(connection.name_2, self.coords)
                pygame.draw.line(self.screen, "black", p1, p2, width)
            current_occupancy: dict[str, int] = {}
            for path in path_list:
                for turn, zone_name in path:
                    if turn == self.current_turn:
                        current_occupancy[zone_name] = (
                            current_occupancy.get(zone_name, 0) + 1)

            ticks = pygame.time.get_ticks()
            for zone in self.graph.zones.values():
                x, y = self.zone_to_screen(zone, self.coords)
                color = ColorResolver.resolve(zone, ticks)
                renderer = self.renderers.get(
                    zone.zone, self.default_renderer)
                renderer.draw(
                    self.screen, x, y, r, r_out, color, self.zoom_scale)
                curr = current_occupancy.get(zone.name, 0)
                mx = zone.max_drones
                lbl = f"{curr}/{mx}" if not zone.is_start else f"{curr}/∞"

                txt_color = (255, 0, 0) if curr >= mx else (0, 0, 0)
                count_surf = small_font.render(lbl, True, txt_color)

                txt_x = x - (count_surf.get_width() // 2)
                txt_y = y - r_out - 18
                self.screen.blit(count_surf, (txt_x, txt_y))
            self.show_drones(path_list, self.current_turn)
            turn_text = f"Tour : {self.current_turn} / {total_turns}"
            text_surface = font.render(turn_text, True, (0, 0, 0))

            pygame.draw.rect(
                self.screen, (240, 240, 240), (10, 10, 180, 40), 0)
            pygame.draw.rect(
                self.screen, (0, 0, 0), (10, 10, 180, 40), 1)
            self.screen.blit(text_surface, (20, 18))
            pygame.display.flip()
        pygame.quit()

    def show_drones(self, path_list: list[list[tuple[int, str]]],
                    current_turn: int) -> None:
        """Draw all drones at their position for *current_turn*.

        Drones in transit toward a restricted zone are rendered at the
        midpoint between their previous and next zones.

        Args:
            path_list: Precomputed drone paths as (turn, zone_name) lists.
            current_turn: The simulation turn to display.
        """
        drone_radius = max(5, int(20 * self.zoom_scale))
        for path in path_list:
            drone_pos: tuple[int, int] | None = None
            exact_state = next(
                (name for t, name in path if t == current_turn), None)
            if exact_state:
                drone_pos = self.zone_to_screen(
                    self.graph.zones[exact_state], self.coords,)
            else:
                prev_state: str | None = None
                next_state: str | None = None
                for t, zone_name in path:
                    if t < current_turn:
                        prev_state = zone_name
                    if t > current_turn and next_state is None:
                        next_state = zone_name
                        break
                if prev_state and next_state:
                    nz = self.graph.zones[next_state]
                    pz = self.graph.zones[prev_state]
                    if nz.zone == ZoneType.RESTRICTED:
                        start_pos = self.zone_to_screen(pz, self.coords)
                        end_pos = self.zone_to_screen(nz, self.coords)
                        drone_pos = ((start_pos[0] + end_pos[0]) // 2,
                                     (start_pos[1] + end_pos[1]) // 2,)
                    else:
                        drone_pos = self.zone_to_screen(pz, self.coords)
                elif prev_state:
                    drone_pos = self.zone_to_screen(
                        self.graph.zones[prev_state], self.coords)
            if drone_pos is not None:
                pygame.draw.circle(
                    self.screen, "black", drone_pos, drone_radius, 0)
