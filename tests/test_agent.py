import pytest
from unittest.mock import MagicMock, patch
from schemas import SceneBlueprint


VALID_BLUEPRINT_JSON = """{
  "layout_type": "linear",
  "stations": [
    {"id": "S1", "name": "工作站1",
     "position": {"x": 0, "y": 0, "z": 0},
     "sim": {"status": "active", "throughput": 45, "temperature": 23.5}}
  ],
  "tracks": [
    {"id": "T1", "from": "S1", "to": "S2",
     "position": {"x": 1, "y": 0.75, "z": 0},
     "rotation": {"x": 0, "y": 0, "z": 90},
     "scale": {"x": 0.15, "y": 1.0, "z": 0.15}}
  ]
}"""


def _mock_ark_response(json_text: str):
    msg = MagicMock()
    msg.content = json_text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_generate_blueprint_returns_scene_blueprint(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-key")
    monkeypatch.setenv("ARK_MODEL", "ep-test-model")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_ark_response(
        VALID_BLUEPRINT_JSON
    )

    with patch("agent.Ark", return_value=mock_client):
        from agent import generate_blueprint
        result = generate_blueprint("5个工作站直线产线")

    assert isinstance(result, SceneBlueprint)
    assert result.layout_type == "linear"
    assert result.stations[0].id == "S1"
    assert result.tracks[0].from_station == "S1"


def test_generate_blueprint_passes_system_prompt(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-key")
    monkeypatch.setenv("ARK_MODEL", "ep-test-model")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_ark_response(
        VALID_BLUEPRINT_JSON
    )

    with patch("agent.Ark", return_value=mock_client):
        from agent import generate_blueprint, SYSTEM_PROMPT
        generate_blueprint("5个工作站直线产线")

    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "5个工作站直线产线"


def test_system_prompt_contains_coordinate_rules():
    from agent import SYSTEM_PROMPT
    assert "2.0 米" in SYSTEM_PROMPT
    assert "z:90" in SYSTEM_PROMPT
    assert "scale.Y" in SYSTEM_PROMPT


def test_generate_blueprint_uses_json_object_format(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-key")
    monkeypatch.setenv("ARK_MODEL", "ep-test-model")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_ark_response(
        VALID_BLUEPRINT_JSON
    )

    with patch("agent.Ark", return_value=mock_client):
        from agent import generate_blueprint
        generate_blueprint("测试")

    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}
