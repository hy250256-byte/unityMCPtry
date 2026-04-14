# 极简 MCP 数字孪生原型 — 设计规格

**项目：** HangingSystem Architect Agent  
**日期：** 2026-04-14  
**状态：** 已确认

---

## 1. 目标与成功标准

用户输入一句自然语言（如"搭建一条5个工作站的直线吊挂产线，间距2米"），系统在 Unity Editor 中自动生成：

- 3-5 个工作站（Cube 几何体），沿直线排列，位置正确
- 相邻工作站之间的轨道（Cylinder 几何体），方向与比例正确
- 每个工作站带仿真数据标签（吞吐量、状态、温度）

**不在范围内（本原型）：** 高保真3D模型、真实PLC信号、L/U型布局、交互式修改。

---

## 2. 系统架构

### 两阶段流水线

```
用户输入（自然语言）
        ↓
   [阶段一] agent.py
   感知 + 规划（合并）
   火山SDK (Doubao) 调用
   输出：JSON 场景蓝图
        ↓
   [数据层] 嵌入蓝图
   AI 顺带生成仿真值
        ↓
   [阶段二] executor.py
   Python MCP Client
   读蓝图 → 调 MCP 工具
        ↓
   mcp-unity（CoderGamester）
   Node.js 进程，stdio 连接
        ↓
   Unity Editor
   Cube + Cylinder 场景搭建完成
```

### 四层映射

| 层级 | 实现位置 | 说明 |
|------|----------|------|
| 感知层 | agent.py | 理解自然语言意图 |
| 规划层 | agent.py | 计算3D坐标，生成蓝图 |
| 数据层 | agent.py（嵌入） | 生成仿真值注入蓝图 |
| 行动层 | executor.py | 驱动 MCP 工具调用 Unity |

---

## 3. 核心文件结构

```
CJDJ_Agent/
├── main.py          # 入口：接收输入，串联两阶段
├── agent.py         # 感知+规划+数据：调火山SDK，输出 JSON 蓝图
├── executor.py      # 行动层：读蓝图，调 MCP 工具
├── schemas.py       # Pydantic 模型：蓝图数据结构与校验
└── requirements.txt # 依赖：mcp, volcenginesdkarkruntime, pydantic
```

---

## 4. JSON 场景蓝图格式

```json
{
  "layout_type": "linear",
  "stations": [
    {
      "id": "S1",
      "name": "工作站1",
      "position": {"x": 0.0, "y": 0.0, "z": 0.0},
      "sim": {
        "status": "active",
        "throughput": 45,
        "temperature": 23.5
      }
    }
  ],
  "tracks": [
    {
      "id": "T1",
      "from": "S1",
      "to": "S2",
      "position": {"x": 1.0, "y": 0.75, "z": 0.0},
      "rotation": {"x": 0.0, "y": 0.0, "z": 90.0},
      "scale":    {"x": 0.15, "y": 1.0, "z": 0.15}
    }
  ]
}
```

### 坐标规则

- 工作站沿 X 轴排列，间距默认 2.0 米
- 工作站 Y=0, Z=0（固定）
- 轨道 position = 相邻两站中点，Y = 0.75
- 轨道 rotation.Z = 90°（Cylinder 躺平沿 X 轴）
- 轨道 scale.Y = 站间距 / 2（间距2m → scale.Y=1.0）
- 轨道 scale.X = scale.Z = 0.15（轨道粗细）

### 仿真数据规则

- `status`: active(70%) / idle(20%) / error(10%)，随机分配
- `throughput`: active 时 30-60，idle/error 时 0
- `temperature`: 20.0-28.0，保留一位小数

---

## 5. agent.py — System Prompt

```
角色：你是服装吊挂产线布局规划师。
根据用户描述输出 JSON 场景蓝图，不输出任何其他内容。

坐标规则：
  工作站沿 X 轴排列，间距默认 2.0 米（用户未指定时）。
  工作站 position.Y = 0，position.Z = 0。
  轨道 position = 两站中点，Y = 0.75。
  轨道 rotation = {x:0, y:0, z:90}。
  轨道 scale.Y = 站间距 / 2，scale.X = scale.Z = 0.15。

仿真数据规则：
  status: active(70%) / idle(20%) / error(10%)，随机分配。
  throughput: active 时 30-60，idle/error 时 0。
  temperature: 20.0-28.0，保留一位小数。

输出格式：严格 JSON，无 markdown 代码块，无注释，无多余文字。
```

调用方式：使用 `response_format={"type": "json_object"}` 强制 JSON 输出，结果由 Pydantic 模型校验。

---

## 6. executor.py — MCP 工具调用序列

### 连接方式

```python
StdioServerParameters(command="node", args=["./mcp-unity/build/index.js"])
# mcp-unity 仓库克隆至项目根目录下的 mcp-unity/ 子目录
```

通过 Python `mcp` 库的 `stdio_client` 启动 mcp-unity Node.js 进程并连接。

### 每个工作站（4步）

1. `execute_menu_item("GameObject/3D Object/Cube")` — 创建 Cube 原始体
2. `update_gameobject(name=station.id, position=station.position)` — 重命名+定位
3. `update_component(path, "Transform", localScale={x:1, y:1.5, z:1})` — 调整尺寸
4. `update_component(path, "TextMesh", text="{status} | {throughput}件/h | {temperature}°C")` — 仿真数据标签（TextMesh 组件，字体大小0.3，位置偏移Y+1.2）

### 每条轨道（3步）

1. `execute_menu_item("GameObject/3D Object/Cylinder")` — 创建 Cylinder
2. `update_gameobject(name=track.id, position=track.position)` — 重命名+定位
3. `update_component(path, "Transform", rotation=track.rotation, scale=track.scale)` — 方向+比例（从蓝图直接读）

**顺序调用，不用 batch_execute**，报错时易定位。

---

## 7. 依赖与外部服务

| 依赖 | 用途 | 备注 |
|------|------|------|
| `volcenginesdkarkruntime` | 调用 Doubao 模型（火山引擎） | 需 API Key |
| `mcp` | Python MCP Client | 官方库 |
| `pydantic` | 蓝图数据校验 | v2 |
| `mcp-unity` (Node.js) | 桥接 MCP ↔ Unity Editor | CoderGamester 版本 |

---

## 8. 数据流（完整）

```
用户输入: "5个工作站直线产线"
    ↓ agent.py
火山SDK → JSON 蓝图（含坐标+仿真数据）
    ↓ schemas.py
Pydantic 校验（不合法则抛出异常）
    ↓ executor.py
for each station: 4次 MCP 调用 → Unity 创建 Cube + 数据标签
for each track:   3次 MCP 调用 → Unity 创建 Cylinder
    ↓
Unity Editor 场景：5个工作站 + 4条轨道 + 仿真数据标签
```

---

## 9. 不在本原型范围

- L型 / U型布局（后续迭代）
- 真实 PLC 信号接入
- 高保真3D模型
- 可交互 UI 面板
- 仿真数据实时刷新
