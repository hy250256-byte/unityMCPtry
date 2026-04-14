import pytest
from pydantic import ValidationError
from schemas import Vec3, SimData, Station, Track, SceneBlueprint


def test_vec3_defaults():
    v = Vec3()
    assert v.x == 0.0 and v.y == 0.0 and v.z == 0.0


def test_sim_data_valid():
    s = SimData(status="active", throughput=45, temperature=23.5)
    assert s.status == "active"


def test_sim_data_invalid_status():
    with pytest.raises(ValidationError):
        SimData(status="broken", throughput=0, temperature=25.0)


def test_sim_data_negative_throughput():
    with pytest.raises(ValidationError):
        SimData(status="active", throughput=-1, temperature=25.0)


def test_sim_data_temperature_out_of_range():
    with pytest.raises(ValidationError):
        SimData(status="active", throughput=0, temperature=35.0)


def test_track_from_alias():
    data = {
        "id": "T1", "from": "S1", "to": "S2",
        "position": {"x": 1, "y": 0.75, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 90},
        "scale": {"x": 0.15, "y": 1.0, "z": 0.15},
    }
    track = Track.model_validate(data)
    assert track.from_station == "S1"
    assert track.to_station == "S2"


def test_blueprint_requires_at_least_one_station():
    with pytest.raises(ValidationError):
        SceneBlueprint(layout_type="linear", stations=[], tracks=[])


def test_valid_full_blueprint():
    data = {
        "layout_type": "linear",
        "stations": [
            {
                "id": "S1", "name": "工作站1",
                "position": {"x": 0, "y": 0, "z": 0},
                "sim": {"status": "active", "throughput": 45, "temperature": 23.5},
            }
        ],
        "tracks": [
            {
                "id": "T1", "from": "S1", "to": "S2",
                "position": {"x": 1, "y": 0.75, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 90},
                "scale": {"x": 0.15, "y": 1.0, "z": 0.15},
            }
        ],
    }
    bp = SceneBlueprint.model_validate(data)
    assert len(bp.stations) == 1
    assert len(bp.tracks) == 1
    assert bp.tracks[0].from_station == "S1"
