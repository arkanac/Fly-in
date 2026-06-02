from pydantic import BaseModel, Field, ValidationError, PositiveInt
from enum import Enum
from typing import Optional, Any


class ZoneType(str, Enum):
    NORMAL = "normal",
    BLOCKED = "blocked",
    RESTRICTED = "restricted",
    PRIORITY = "priority"


class Zone(BaseModel):
    name: str
    x: int
    y: int
    zone: ZoneType = Field(default=ZoneType.NORMAL)
    max_drones: int = Field(gt=0, default=1)
    color: Optional[str] = None


class Connection(BaseModel):
    name_1: Zone
    name_2: Zone
    max_link_capacity: int = Field(gt=0, default=1)


class Graph(BaseModel):
    nb_drones: int = Field(ge=0)
    zones: dict[str, Zone] = {}
    connection: list[Connection] = []


class Parsing:
    def __init__(self, path: str) -> None:
        self.metadata: Any = metadata
        self.zone_stats: Any = zone_stats
        self.connection_stat: str = connection_stats
        path = "/home/rem/Fly-in/maps/easy/01_linear_path.txt"
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for line in lines:

                if not line.strip() or line.startswith("#"):
                    continue
                elif line.startswith("hub:", "start_hub:", "end_hub"):
                    part = line.split("[")
                    self.zone_stats = part[0]
                    self.metadata = part[1]
                elif line.startswith("connection:"):
                    part = line.split("[")
                    self.connection_stats = part[0]
                    self.metadata = part[1]
        except ValidationError as e:
            raise Exception(e)





