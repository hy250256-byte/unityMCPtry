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
