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
