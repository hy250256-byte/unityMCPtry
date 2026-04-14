import pytest
from unittest.mock import AsyncMock
from schemas import Vec3, SimData, Station, Track, SceneBlueprint
from executor import SceneExecutor


def make_station(sid: str, x: float) -> Station:
    return Station(
        id=sid,
        name=f"工作站{sid}",
        position=Vec3(x=x, y=0.0, z=0.0),
        sim=SimData(status="active", throughput=45, temperature=23.5),
    )


def make_track(tid: str, from_s: str, to_s: str, x_mid: float) -> Track:
    return Track.model_validate({
        "id": tid, "from": from_s, "to": to_s,
        "position": {"x": x_mid, "y": 0.75, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 90.0},
        "scale": {"x": 0.15, "y": 1.0, "z": 0.15},
    })


@pytest.mark.asyncio
async def test_create_station_calls_4_mcp_tools():
    executor = SceneExecutor()
    session = AsyncMock()
    station = make_station("S1", 0.0)

    await executor._create_station(session, station)

    assert session.call_tool.call_count == 4
    tool_names = [call.args[0] for call in session.call_tool.call_args_list]
    assert tool_names[0] == "execute_menu_item"
    assert tool_names[1] == "update_gameobject"
    assert tool_names[2] == "update_component"
    assert tool_names[3] == "update_component"


@pytest.mark.asyncio
async def test_create_station_renames_cube_to_station_id():
    executor = SceneExecutor()
    session = AsyncMock()
    station = make_station("S1", 0.0)

    await executor._create_station(session, station)

    rename_call = session.call_tool.call_args_list[1]
    args = rename_call.args[1]
    assert args["path"] == "/Cube"
    assert args["name"] == "S1"


@pytest.mark.asyncio
async def test_create_station_sets_transform_position():
    executor = SceneExecutor()
    session = AsyncMock()
    station = make_station("S1", 4.0)

    await executor._create_station(session, station)

    transform_call = session.call_tool.call_args_list[2]
    values = transform_call.args[1]["values"]
    assert values["localPosition"] == {"x": 4.0, "y": 0.0, "z": 0.0}
    assert values["localScale"] == {"x": 1.0, "y": 1.5, "z": 1.0}


@pytest.mark.asyncio
async def test_create_station_sets_textmesh_label():
    executor = SceneExecutor()
    session = AsyncMock()
    station = make_station("S1", 0.0)

    await executor._create_station(session, station)

    label_call = session.call_tool.call_args_list[3]
    assert label_call.args[1]["componentType"] == "TextMesh"
    text = label_call.args[1]["values"]["text"]
    assert "active" in text
    assert "45" in text
    assert "23.5" in text


@pytest.mark.asyncio
async def test_create_track_calls_3_mcp_tools():
    executor = SceneExecutor()
    session = AsyncMock()
    track = make_track("T1", "S1", "S2", 1.0)

    await executor._create_track(session, track)

    assert session.call_tool.call_count == 3
    tool_names = [call.args[0] for call in session.call_tool.call_args_list]
    assert tool_names[0] == "execute_menu_item"
    assert tool_names[1] == "update_gameobject"
    assert tool_names[2] == "update_component"


@pytest.mark.asyncio
async def test_create_track_renames_cylinder():
    executor = SceneExecutor()
    session = AsyncMock()
    track = make_track("T1", "S1", "S2", 1.0)

    await executor._create_track(session, track)

    rename_call = session.call_tool.call_args_list[1]
    assert rename_call.args[1]["path"] == "/Cylinder"
    assert rename_call.args[1]["name"] == "T1"


@pytest.mark.asyncio
async def test_create_track_sets_transform_from_blueprint():
    executor = SceneExecutor()
    session = AsyncMock()
    track = make_track("T1", "S1", "S2", 1.0)

    await executor._create_track(session, track)

    transform_call = session.call_tool.call_args_list[2]
    values = transform_call.args[1]["values"]
    assert values["localPosition"] == {"x": 1.0, "y": 0.75, "z": 0.0}
    assert values["localEulerAngles"] == {"x": 0.0, "y": 0.0, "z": 90.0}
    assert values["localScale"] == {"x": 0.15, "y": 1.0, "z": 0.15}


@pytest.mark.asyncio
async def test_build_scene_processes_all_stations_and_tracks():
    executor = SceneExecutor()
    session = AsyncMock()
    blueprint = SceneBlueprint(
        layout_type="linear",
        stations=[make_station("S1", 0.0), make_station("S2", 2.0)],
        tracks=[make_track("T1", "S1", "S2", 1.0)],
    )

    await executor._build_with_session(session, blueprint)

    # 2 stations × 4 calls + 1 track × 3 calls = 11 total
    assert session.call_tool.call_count == 11
