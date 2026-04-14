from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Vec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SimData(BaseModel):
    status: Literal["active", "idle", "error"]
    throughput: int = Field(ge=0)
    temperature: float = Field(ge=20.0, le=28.0)


class Station(BaseModel):
    id: str
    name: str
    position: Vec3
    sim: SimData


class Track(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    from_station: str = Field(alias="from")
    to_station: str = Field(alias="to")
    position: Vec3
    rotation: Vec3
    scale: Vec3


class SceneBlueprint(BaseModel):
    layout_type: Literal["linear"]
    stations: list[Station] = Field(min_length=1)
    tracks: list[Track]
