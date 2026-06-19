from pydantic import BaseModel, Field, ValidationError, field_validator
from enum import Enum
from typing import Optional, Any


class ZoneType(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone(BaseModel):
    name: str
    x: int
    y: int
    zone: ZoneType = Field(default=ZoneType.NORMAL)
    max_drones: int = Field(ge=1, default=1)
    color: Optional[str] = None
    is_start: bool = False
    is_end: bool = False

    @field_validator("color", mode='before')
    @classmethod
    def single_word(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and " " in v:
            raise ValueError("Color must be a single-word string")
        return v


class Connection(BaseModel):
    name_1: Zone
    name_2: Zone
    max_link_capacity: int = Field(gt=0, default=1)


class Graph(BaseModel, validate_assignment=True):
    nb_drones: int = Field(ge=0, default=0)
    zones: dict[str, Zone] = {}
    connection: list[Connection] = []

    def get_neighbors(self, zone_name: str) -> list[tuple[Connection, Zone]]:
        neighbor_list: list[tuple[Connection, Zone]] = []
        for link in self.connection:
            if (link.name_1.name == zone_name and link.name_2.zone
                    != ZoneType.BLOCKED):
                neighbor_list.append((link, link.name_2))
            elif (link.name_2.name == zone_name and link.name_1.zone
                    != ZoneType.BLOCKED):
                neighbor_list.append((link, link.name_1))
        return neighbor_list

    def move_cost(self, zone: Zone) -> int:
        match zone.zone:
            case ZoneType.RESTRICTED:
                return 2
            case _:
                return 1


class Parsing:
    def __init__(self, path: str) -> None:
        self.graph = Graph()
        self.seen_connections: set[tuple[str, str]] = set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if not line.strip() or line.startswith("#"):
                    continue
                elif line.startswith("hub:"):
                    self.parse_zone(line, False, False)
                elif line.startswith("start_hub:"):
                    self.parse_zone(line, True, False)
                elif line.startswith("end_hub:"):
                    self.parse_zone(line, False, True)
                elif line.startswith("connection:"):
                    connection = self.parse_connection(line)
                    self.graph.connection.append(connection)
                elif line.startswith("nb_drones:"):
                    self.parse_nb_drone(line)
            self.validate_graph()
        except ValidationError:
            raise

    def parse_nb_drone(self, line: str) -> None:
        try:
            self.graph.nb_drones = int(line.split(":")[1].strip())
        except (ValidationError, ValueError):
            raise ValueError(f"ERROR: Invalid nb_drones value, must be an int"
                             f" -> {line.split(":")[1].strip()}")

    def parse_zone(self, line: str,  is_start: bool = False,
                   is_end: bool = False) -> Zone:
        zone_data: dict[str, Any] = {}
        try:
            if is_start:
                zone_data["is_start"] = True
            if is_end:
                zone_data["is_end"] = True
            data = line.split(":")[1]
            part = data.split("[")
            zone_stats = part[0]
            stats = zone_stats.split()
            zone_data["name"] = stats[0]
            if "-" in zone_data["name"]:
                raise ValueError("Error: Zone name cannot contain dashes")
            zone_data["x"] = int(stats[1])
            zone_data["y"] = int(stats[2])
            if len(part) > 1:
                metadata = part[1]
                metadata_parts = metadata.split()
                for pair in metadata_parts:
                    if "=" not in pair:
                        raise ValueError(f"Invalid metadata pair: '{pair}'")
                    k, v = pair.split("=")
                    zone_data[k] = v.strip("]")
            zone = Zone.model_validate(zone_data)
            if zone.name in self.graph.zones:
                raise ValueError(f"Duplicate zone: '{zone.name}'")
            self.graph.zones[zone.name] = zone
            return zone
        except ValidationError as e:
            raise e

    def parse_connection(self, line: str) -> Connection:
        connection_data: dict[str, Any] = {}
        try:
            data = line.split(":")[1]
            part = data.split("[")
            zone_name = part[0]
            name = zone_name.split("-")
            if len(name) != 2:
                raise ValueError(f"Invalid connection format:"
                                 f"'{zone_name.strip()}'")
            name_1 = name[0].strip()
            name_2 = name[1].strip()
            if name_1 not in self.graph.zones:
                raise ValueError(f"Hub {name_1} not found")
            if name_2 not in self.graph.zones:
                raise ValueError(f"Hub {name_2} not found")
            zone_1 = self.graph.zones[name_1]
            zone_2 = self.graph.zones[name_2]
            connection_data["name_1"] = zone_1
            connection_data["name_2"] = zone_2
            if len(part) > 1:
                metadata = part[1].strip("]")
                for pair in metadata.split():
                    if "=" not in pair:
                        raise ValueError(f"Invalid metadata pair: '{pair}'")

                    k, v = pair.split("=")
                    if k != "max_link_capacity":
                        raise ValueError(f"Unknown metadata key: {k}")
                    connection_data[k] = v.strip("]")
            if ((name_1, name_2) in self.seen_connections
                    or (name_2, name_1) in self.seen_connections):
                raise ValueError(f"Duplicate connection: '{name_1}-{name_2}'")
            self.seen_connections.add((name_1, name_2))
            connection = Connection.model_validate(connection_data)
            return connection
        except ValidationError as e:
            raise e

    def validate_graph(self) -> None:
        starts = [z for z in self.graph.zones.values() if z.is_start]
        ends = [z for z in self.graph.zones.values() if z.is_end]
        if len(starts) != 1:
            raise ValueError(f"Expected 1 start zone, found {len(starts)}")
        coords = [(z.x, z.y) for z in self.graph.zones.values()]
        if len(coords) != len(set(coords)):
            raise ValueError("Two zones share the same coordinates")
        if len(ends) != 1:
            raise ValueError(f"Expected 1 end zone, found {len(ends)}")
        if self.graph.nb_drones <= 0:
            raise ValueError("1 or more drone expected")
