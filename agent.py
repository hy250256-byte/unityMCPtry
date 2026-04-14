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
  轨道 rotation = {x:0,y:0,z:90}。
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
