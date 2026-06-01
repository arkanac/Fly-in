from pydantic import BaseModel, ValidationError,
from enum import Enum
from typing import Optional


class ZoneType(str, Enum):
    NORMAL = "normal",
    BLOCKED = "blocked",
    RESTRICTED = "restricted",
    PRIORITY = "priority"


class Zone(BaseModel):
    name: str
    x: int
    y: int
    zone: ZoneType
    max_drones: int
    color: Optional[str] = None


class Connection(BaseModel):
    name_1: Zone
    name_2: Zone
    max_link_capacity: int

class Graph(BaseModel):
    zones: dict[str, Zone] = {}
    connection: list[Connection] = []
