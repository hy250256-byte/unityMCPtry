# 极简 MCP 数字孪生原型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用自然语言驱动 AI 生成 JSON 场景蓝图，再由 Python MCP Client 调用 mcp-unity 工具在 Unity Editor 中自动搭建服装吊挂产线的几何体场景（Cube 工作站 + Cylinder 轨道 + 仿真数据标签）。

**Architecture:** 两阶段流水线：① `agent.py` 调用火山引擎 Doubao 模型，将自然语言转换为带坐标和仿真数据的 JSON 蓝图（Pydantic 校验）；② `executor.py` 用 Python `mcp` 库连接 mcp-unity Node.js 进程，按蓝图顺序调用 `execute_menu_item` / `update_gameobject` / `update_component` 工具在 Unity 中搭建场景。

**Tech Stack:** Python 3.11+, volcenginesdkarkruntime, mcp (Python), pydantic v2, pytest, pytest-asyncio, Node.js 18+, mcp-unity (CoderGamester), Unity 2022 LTS+

---

## File Map

| 文件 | 职责 |
|------|------|
| `schemas.py` | Pydantic 模型：Vec3, SimData, Station, Track, SceneBlueprint |
| `agent.py` | SYSTEM_PROMPT 常量 + `generate_blueprint(user_input)` |
| `executor.py` | `SceneExecutor` 类：`build_scene`, `_create_station`, `_create_track` |
| `main.py` | CLI 入口：接收参数，串联 agent → executor |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 环境变量模板 |
| `.gitignore` | 忽略 .env, __pycache__, mcp-unity/node_modules 等 |
| `tests/__init__.py` | 空文件，使 tests 成为包 |
| `tests/test_schemas.py` | schemas.py 的单元测试 |
| `tests/test_agent.py` | agent.py 的单元测试（mock 火山SDK） |
| `tests/test_executor.py` | executor.py 的单元测试（mock MCP session） |

**MCP 工具调用规则（executor.py 必须遵守）：**
- 每次 `execute_menu_item("GameObject/3D Object/Cube")` 创建名为 `"Cube"` 的对象
- 紧接着 `update_gameobject({"path": "/Cube", "name": "S1"})` 重命名——此后 Unity 中不再有叫 `"Cube"` 的对象
- 下一次 `execute_menu_item` 再创建时，Unity 重新命名为 `"Cube"`（因为旧的已改名）
- 轨道同理：`"Cylinder"` → 立即重命名 → 下次还是 `"Cylinder"`

---

## Task 1: 项目基础设施

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```
volcengine-python-sdk[ark]>=1.0.0
mcp>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: 创建 .gitignore**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
mcp-unity/node_modules/
mcp-unity/build/
.superpowers/
```

- [ ] **Step 3: 创建 .env.example**

```
# 火山引擎 ARK API Key（在 https://console.volcengine.com/ark 获取）
ARK_API_KEY=your-ark-api-key-here

# 推理接入点 ID（在 ARK 控制台创建接入点后获取，格式 ep-xxxxxxxx-xxxxx）
ARK_MODEL=ep-xxxxxxxx-xxxxx

# mcp-unity Node.js 服务入口（克隆仓库后 npm run build 生成）
MCP_UNITY_PATH=./mcp-unity/build/index.js
```

- [ ] **Step 4: 创建 tests/__init__.py**

```python
```
（空文件）

- [ ] **Step 5: 安装依赖**

```bash
pip install -r requirements.txt
```

预期输出：`Successfully installed ...`（无报错）

- [ ] **Step 6: 复制并填写 .env**

```bash
cp .env.example .env
# 然后编辑 .env，填入真实的 ARK_API_KEY 和 ARK_MODEL
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore .env.example tests/__init__.py
git commit -m "chore: project bootstrap"
```

---

## Task 2: 数据模型 (schemas.py)

**Files:**
- Create: `schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_schemas.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_schemas.py -v
```

预期：`ImportError: cannot import name 'Vec3' from 'schemas'`（schemas.py 不存在）

- [ ] **Step 3: 实现 schemas.py**

```python
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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_schemas.py -v
```

预期：`8 passed`

- [ ] **Step 5: Commit**

```bash
git add schemas.py tests/test_schemas.py
git commit -m "feat: add blueprint data models with validation"
```

---

## Task 3: AI 蓝图生成器 (agent.py)

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_agent.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_agent.py -v
```

预期：`ImportError: cannot import name 'generate_blueprint' from 'agent'`

- [ ] **Step 3: 实现 agent.py**

```python
import os
from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark
from schemas import SceneBlueprint

load_dotenv()

SYSTEM_PROMPT = """你是服装吊挂产线布局规划师。
根据用户描述输出 JSON 场景蓝图，不输出任何其他内容。

坐标规则：
  工作站沿 X 轴排列，间距默认 2.0 米（用户未指定时）。
  工作站 position.Y = 0，position.Z = 0。
  轨道 position = 两站中点，Y = 0.75。
  轨道 rotation = {"x":0,"y":0,"z":90}。
  轨道 scale.Y = 站间距 / 2，scale.X = scale.Z = 0.15。
  轨道 "from" 为起始工作站 id，"to" 为终止工作站 id。

仿真数据规则：
  status: active(70%) / idle(20%) / error(10%)，随机分配。
  throughput: active 时 30-60，idle/error 时 0。
  temperature: 20.0-28.0，保留一位小数。

输出格式：严格 JSON，无 markdown 代码块，无注释，无多余文字。
JSON 结构：{"layout_type":"linear","stations":[...],"tracks":[...]}"""


def generate_blueprint(user_input: str) -> SceneBlueprint:
    client = Ark(api_key=os.environ["ARK_API_KEY"])
    response = client.chat.completions.create(
        model=os.environ["ARK_MODEL"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return SceneBlueprint.model_validate_json(raw)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_agent.py -v
```

预期：`4 passed`

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: add AI blueprint generator with Doubao SDK"
```

---

## Task 4: MCP 场景执行器 (executor.py)

**Files:**
- Create: `executor.py`
- Create: `tests/test_executor.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_executor.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_executor.py -v
```

预期：`ImportError: cannot import name 'SceneExecutor' from 'executor'`

- [ ] **Step 3: 实现 executor.py**

```python
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from schemas import SceneBlueprint, Station, Track

load_dotenv()


class SceneExecutor:
    def __init__(self, mcp_unity_path: str | None = None):
        path = mcp_unity_path or os.environ.get(
            "MCP_UNITY_PATH", "./mcp-unity/build/index.js"
        )
        self.server_params = StdioServerParameters(
            command="node", args=[path]
        )

    async def build_scene(self, blueprint: SceneBlueprint) -> None:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self._build_with_session(session, blueprint)

    async def _build_with_session(
        self, session: ClientSession, blueprint: SceneBlueprint
    ) -> None:
        for station in blueprint.stations:
            await self._create_station(session, station)
        for track in blueprint.tracks:
            await self._create_track(session, track)

    async def _create_station(
        self, session: ClientSession, station: Station
    ) -> None:
        # 1. 创建 Cube 原始体（Unity 自动命名为 "Cube"）
        await session.call_tool(
            "execute_menu_item",
            {"menuPath": "GameObject/3D Object/Cube"},
        )
        # 2. 重命名（"/Cube" → station.id），移出 "Cube" 命名空间
        await session.call_tool(
            "update_gameobject",
            {"path": "/Cube", "name": station.id},
        )
        # 3. 设置位置和尺寸
        await session.call_tool(
            "update_component",
            {
                "gameObjectPath": f"/{station.id}",
                "componentType": "Transform",
                "values": {
                    "localPosition": {
                        "x": station.position.x,
                        "y": station.position.y,
                        "z": station.position.z,
                    },
                    "localScale": {"x": 1.0, "y": 1.5, "z": 1.0},
                },
            },
        )
        # 4. 添加仿真数据文字标签
        label = (
            f"{station.sim.status} | "
            f"{station.sim.throughput}件/h | "
            f"{station.sim.temperature}°C"
        )
        await session.call_tool(
            "update_component",
            {
                "gameObjectPath": f"/{station.id}",
                "componentType": "TextMesh",
                "values": {"text": label, "characterSize": 0.2},
            },
        )

    async def _create_track(
        self, session: ClientSession, track: Track
    ) -> None:
        # 1. 创建 Cylinder 原始体（Unity 自动命名为 "Cylinder"）
        await session.call_tool(
            "execute_menu_item",
            {"menuPath": "GameObject/3D Object/Cylinder"},
        )
        # 2. 重命名
        await session.call_tool(
            "update_gameobject",
            {"path": "/Cylinder", "name": track.id},
        )
        # 3. 设置位置、旋转、缩放（全部来自蓝图，AI 已算好）
        await session.call_tool(
            "update_component",
            {
                "gameObjectPath": f"/{track.id}",
                "componentType": "Transform",
                "values": {
                    "localPosition": {
                        "x": track.position.x,
                        "y": track.position.y,
                        "z": track.position.z,
                    },
                    "localEulerAngles": {
                        "x": track.rotation.x,
                        "y": track.rotation.y,
                        "z": track.rotation.z,
                    },
                    "localScale": {
                        "x": track.scale.x,
                        "y": track.scale.y,
                        "z": track.scale.z,
                    },
                },
            },
        )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_executor.py -v
```

预期：`8 passed`

- [ ] **Step 5: Commit**

```bash
git add executor.py tests/test_executor.py
git commit -m "feat: add MCP scene executor with Unity tool calls"
```

---

## Task 5: CLI 入口 (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: 实现 main.py**

```python
import asyncio
import sys
from agent import generate_blueprint
from executor import SceneExecutor


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python main.py \"<自然语言描述>\"")
        print("示例: python main.py \"搭建5个工作站的直线吊挂产线，间距2米\"")
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])

    print(f"\n[1/2] 生成场景蓝图...")
    print(f"  输入: {user_input}")
    blueprint = generate_blueprint(user_input)
    print(f"  ✓ {len(blueprint.stations)} 个工作站, {len(blueprint.tracks)} 条轨道")
    for s in blueprint.stations:
        pos = s.position
        print(f"      {s.id} ({s.name}): ({pos.x}, {pos.y}, {pos.z})  [{s.sim.status}]")

    print(f"\n[2/2] 在 Unity 中搭建场景...")
    executor = SceneExecutor()
    asyncio.run(executor.build_scene(blueprint))
    print(f"  ✓ 场景搭建完成\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 import 无报错**

```bash
python -c "import main"
```

预期：无输出，无报错

- [ ] **Step 3: 运行全部测试，确认无回归**

```bash
pytest tests/ -v
```

预期：`20 passed`（test_schemas: 8 + test_agent: 4 + test_executor: 8）

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add CLI entry point"
```

---

## Task 6: mcp-unity 安装与 Unity 项目配置

> 此 Task 为手动操作步骤，无自动化测试。

**Files:**
- Create: `mcp-unity/` (通过 git clone)

- [ ] **Step 1: 克隆 mcp-unity 到项目根目录**

```bash
git clone https://github.com/CoderGamester/mcp-unity.git
```

- [ ] **Step 2: 安装 Node.js 依赖并构建**

```bash
cd mcp-unity
npm install
npm run build
cd ..
```

预期：`mcp-unity/build/index.js` 文件生成

- [ ] **Step 3: 验证 Node.js 服务可启动**

```bash
node mcp-unity/build/index.js --version 2>&1 | head -5
```

预期：无崩溃（可能输出版本信息或等待连接）。按 Ctrl+C 退出。

- [ ] **Step 4: 在 Unity 中安装 mcp-unity Package**

打开 Unity 2022 LTS+，进入：
`Window → Package Manager → + → Add package from disk`
选择文件：`mcp-unity/Packages/com.gamelovers.mcp-unity/package.json`

安装完成后，Unity 控制台应出现：`MCP Unity Server initialized`（或类似提示）。

- [ ] **Step 5: 在 Unity 中创建新的空场景**

`File → New Scene → Basic (Built-in)` → 保存为 `Assets/Scenes/HangingLine.unity`

- [ ] **Step 6: Commit mcp-unity 子模块配置**

```bash
git add .gitmodules mcp-unity 2>/dev/null || git add mcp-unity
git commit -m "chore: add mcp-unity as dependency"
```

---

## Task 7: 端到端冒烟测试

> 前置条件：Unity 已打开 HangingLine 场景，mcp-unity Package 已安装且服务运行中。

- [ ] **Step 1: 确认 .env 已配置真实 API Key**

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ARK_API_KEY:', os.environ.get('ARK_API_KEY', 'NOT SET')[:8] + '...')"
```

预期：`ARK_API_KEY: xxxxxxxx...`（非 NOT SET）

- [ ] **Step 2: 运行端到端**

```bash
python main.py "搭建一条5个工作站的直线吊挂产线，间距2米"
```

预期输出：
```
[1/2] 生成场景蓝图...
  输入: 搭建一条5个工作站的直线吊挂产线，间距2米
  ✓ 5 个工作站, 4 条轨道
      S1 (工作站1): (0.0, 0.0, 0.0)  [active]
      S2 (工作站2): (2.0, 0.0, 0.0)  [idle]
      ...

[2/2] 在 Unity 中搭建场景...
  ✓ 场景搭建完成
```

- [ ] **Step 3: 在 Unity Editor 中验证场景**

切换到 Unity，在 Hierarchy 面板确认：
- `S1`, `S2`, `S3`, `S4`, `S5` — 5 个 Cube，沿 X 轴排列
- `T1`, `T2`, `T3`, `T4` — 4 个 Cylinder，躺平连接相邻工作站
- 每个 Cube 有 TextMesh 组件，显示状态/吞吐量/温度

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "feat: end-to-end digital twin prototype working"
```

---

## 已知局限（下一版本迭代）

- TextMesh 标签渲染在 Cube 中心而非正上方（可用 child GameObject 改善）
- 若 Unity 场景已有同名对象，重命名步骤会失败（需在运行前清空场景）
- 仅支持直线 `linear` 布局
