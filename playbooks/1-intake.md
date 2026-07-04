# Playbook 1 — Intake（引导式构建画像）

> 目标：产出完整的 `data/profile.yaml`、`data/narrative.md`、`data/constraints.yaml`，并通过 `validate`。
> **方式：引导式** —— 用户**不用预填**，Agent 像职业顾问一样带聊，边聊边把用户的话**提炼**成结构化画像。繁琐的活在 Agent 这侧，不在用户那侧。

## 怎么做（引导式，不是审问）

1. **先开放聊**：用 2-3 个宽问题热身（"现在什么阶段、最近在琢磨什么、来这里想解决什么"），让用户自然讲，别一上来甩表或逐项问。
2. **边听边填表**：从用户的讲述里**主动提取**结构化信息，直接写进 `data/profile.yaml`（先 `cp templates/profile.example.yaml data/profile.yaml` 再覆盖填，或新建）。**用户只负责说，你负责结构化。**
   - **教育背景必采**：本 / 硕 / 博 **院校全名**、**专业**、**学院**（如有）、**起止年份**、**在读/已毕业**；`school_tier` 单独记 985/211/双一流/一本/二本/海外，**不要把「211」「二本」写在 school 里**。
   - 博士在读：补 `thesis_or_focus`、`advisor`（可选）、预计毕业年 `end_year`。
3. **针对缺口引导追问**：跑 `uv run career-compass validate`，针对它报的缺口（以及你判断的关键缺口，如 values / constraints）做**精准追问**，不一刀切逐项审问。
4. **每条优势只问一句证据**：用户说"我擅长 X"，你就问"给一个最能让陌生人信服的例子或数字"，不纠缠。

核心姿态：**用户像在和一个懂行的顾问聊天，你在背后把画像建好。**

## 铁律（不能因"引导"而放松）

1. **没有证据的"擅长"不入库。** `strength_evidence` 的 `proof` 必须是事件/数字/可核验结果。引导时自然地问出证据，但必须有。
2. **技能要分层**（core / adjacent / frontier），别堆名词。用户说"什么都会一点"时，帮 ta 诚实分层。
3. **constraints 是墙**（地域 / 签证 / 家庭 / runway / 风险偏好 / 年龄），聊到就如实记，不漏。
4. **values 要排出来**（learning / impact / autonomy / money / stability / family / research / status）。排不清时用"二选一"逼一下（"impact 和 autonomy 只能保一个，你选哪个"）。

## narrative.md 写什么

profile.yaml 装不下的叙述：转折故事、为什么离开上一段、最自豪/最讨厌、3 年后想要的生活、红线。**同样由你从聊天里提炼写入**，不是让用户写作文。

## 可选：自动采集项目证据

聊天前或聊天中，可跑一次（**用户点名目录，opt-in**）：

```bash
uv run career-compass scan-projects ~/code/projectA ~/code/projectB
```

自动提取每个项目的语言 / 关键依赖 / 规模 / 论文成果（`paper/`、`.tex`）→ 写入 `data/projects.yaml`。这些是 `strength_evidence` 的硬证据来源（真实代码 > 自我报告），3-analyze 时会被 `brief` 带入。**只扫用户点名的目录，不扫整盘。**

## 完成判据

```bash
uv run career-compass validate
```
- `✅` → 进 2-scan。
- 缺口 → 针对缺口引导追问，补完再 validate。**不带缺口进分析。**

## 反模式

- ❌ 甩一个空模板让用户自己填（冷启动杀手）
- ❌ 一次甩一堆问题 / 逐项审问（繁琐，用户会跑）
- ❌ 用户说"什么都会一点"就记一堆 core 技能
- ❌ 接受"学习能力强"当优势却不挂证据
- ❌ 跳过 constraints 直接谈方向
