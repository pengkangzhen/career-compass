# Playbook 2 — Scan（外部信号采集）

> 目标：往 `data/signals/*.yaml` 里填带来源、带日期、标了置信度的外部信号。没经过这一步，分析就是空中楼阁。

## 检索什么

先派生查询：
```bash
uv run career-compass scan-plan
```
这些查询是基于用户画像生成的（围绕 frontier skills / core skills / 所在行业 / 当前角色）。**先跑这些**，不够再补。

## 三个 domain

| domain | 内容 | 文件 |
|--------|------|------|
| `trends` | 技术/行业走向、上升/衰退的技能、技术成熟度 | `signals/trends.yaml` |
| `market` | 需求量、薪酬区间、供需比、地域差异 | `signals/market.yaml` |
| `landscape` | 头部玩家、产业链上下游、谁在抢这类人才 | `signals/landscape.yaml` |

## 怎么入库

每条信号用 CLI 追加（会自动校验 + 打日期）：
```bash
uv run career-compass new-signal trends \
  "LLM 推理优化" \
  "vLLM/TGI 类推理框架需求年增，纯算法岗趋稳" \
  "某招聘平台 2026 报告" \
  "https://example.com/report" \
  --confidence medium
```

## 铁律

1. **每条必须有来源。** 没有可追溯来源的"行业感觉"不算信号，是噪声。
2. **每条必须有日期。** 信号会过期。`new-signal` 自动填今天，但若引用旧报告要手动改 `retrieved_on`。
3. **标置信度。** 一手数据/权威报告 = high；二手转述/单篇博客 = medium；猜测/无法验证 = low。诚实标注比充内行有用。
4. **区分事实与推测。** finding 里写"X 在增长"（事实）可以，写"X 会一直涨"（推测）必须标 low 并写明是判断。
5. **矛盾的信号都留。** 不要为了避免冲突只留一边。3-analyze 阶段会专门处理矛盾。

## 完成判据

三个 domain 都至少有 2-3 条信号，且都带来源和日期。然后：
```bash
uv run career-compass brief   # 确认信号出现在 brief 里
```
进 3-analyze。

## 反模式

- ❌ 把模型的先验知识当成"信号"写进去（那是你的训练数据，不是检索来的；要检索就拿来源）
- ❌ 全是 high confidence 自吹自擂
- ❌ 只搜支持用户现有方向的信号（确认偏误）
