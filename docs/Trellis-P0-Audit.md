# Trellis P0 项目审计报告

> 审计时间：2026-11-05　审计范围：`E:\Trellis` 全目录
> 结论先行：现有数据完整、可用，但分散在 3 个 HTML、1 个 JS、1 个 Excel、2 个 Markdown 中，字段结构互不一致，图谱关系全部是"教学结构"而非带来源与审核状态的词源关系。适合作为一次性迁移源，不适合继续承载增量录入。

---

## 1. 现有文件清单（以真实文件为准）

| 文件 | 大小 | 角色 | 是否含业务数据 | 迁移去向 |
|---|---|---|---|---|
| `词库.html` | 14,433 B | Day 1 词表视图（浅色） | 无（读 `data/words.js`） | 前端重构参考 |
| `词库网络图.html` | 21,182 B | Day 1 词族网络图（浅色 Canvas） | 无（读 `data/words.js` 的 `graph`） | 图谱前端参考 |
| `词族网络图.html` | 47,387 B | 20 词深色词源图（含详情/自测） | **有**：内嵌 `NODES`(34) / `EDGES`(29) | 迁移来源 A |
| `data/words.js` | 3,387 B | Day 1 唯一数据源 | **有**：19 词 + `graph` | 迁移来源 B |
| `词族词库_fin-volv.xlsx` | 16,449 B | 20 词词库（5 表） | **有** | 迁移来源 C |
| `词族知识库_fin-volv.md` | 25,970 B | 20 词详解 + 辨析 + 自测 | **有** | 迁移来源 D |
| `复习计划.md` | 2,567 B | Day 1 复习日期表 | **有** | 迁移来源 E |
| `data/` | 目录 | 无后端 | — | 保留为 legacy 只读 |

**注意**：清单与用户最初列出的文件名一致，无缺失、无额外业务文件。项目**不是 git 仓库**（无 `.git`），当前没有回滚基线。

---

## 2. 数据审计

### 2.1 来源 A：旧深色图谱 `词族网络图.html`

- 节点 34 个：`root` 5（fin / volv / ergon / fallere / miht）、`branch` 9、`word` 20。
- 边 29 条：`root → branch` 9 条，`branch → word` 20 条。
- 20 个单词的字段：`id`、`fam`、`label`、`level`（一级主词 9 / 半主词 3 / 派生 8）、`ipa`、`pos`、`gloss`、`senses[]`、`formula`（构词 HTML）、`coll[]`、`ex`（例句，含 `<em>`）、`hook`（记忆钩）。
- 家族分布：fin 7、volv 8、ergon 2、fallere 2、miht 1。
- 关系只存拓扑 `s/t`，可选 `d`（虚线）与 `p`（前缀/后缀标签），**没有关系类型、来源、方向语义、审核状态**。

### 2.2 来源 B：`data/words.js`

- 1 个学习日（Day 1，2026-11-05，`learned: true`），3 个分组，19 条词目：16 个单词 + 3 个短语（`work against` / `work on` / `work out`）。
- 字段：`id`（如 `d1-01`，**不可作为标准词条 ID**）、`term`、`kind`、`main`（work / state）、`senses[{pos, meanings[]}]`。
- `graph`：3 个 root（work / stat / labor）、9 个 branch、28 条 link；经脚本校验，19 个词全部被 link 引用，无孤立节点、无重复 id、无大小写重复。
- 缺失：音标、例句、搭配、词源、拼写变体。

### 2.3 来源 C：`词族词库_fin-volv.xlsx`

| 表 | 行×列 | 用途 | 迁移目标 |
|---|---|---|---|
| 词族总表 | 21×12 | 20 词的音标/词性/核心义/家族/词根义/前缀/构词公式/主词层级/意象/搭配 | `lexemes`、`spellings`、`pronunciations`、`senses`、`morphemes`、`collocations` |
| 主词判定 | 21×5 | 主词层级、判定依据、记忆成本、处理建议 | `lexeme_traits`（扩展属性） |
| 构词结构 | 11×8 | 族/词根/词根义/前缀/前缀义/合成逻辑/成品词/词性 | `morphemes` + 派生候选边（待审核） |
| 近义辨析 | 22×5 | 辨析组、核心区别、典型搭配、对比例句 | `sense_contrasts` + `examples` |
| 自测15题 | 16×4 | 题型/题目/答案 | 仅作导入报告素材，不进正式卡片 |

### 2.4 来源 D：`词族知识库_fin-volv.md`

- 20 条词目（1.1–1.7 fin 7 条；2.1–2.8 volv 8 条；3.1–3.5 energy/energetic/might/fail/failure 5 条）。
- 每条含：音标、词性、主词/派生标注、构词拆解、语义链、义项、搭配、例句、易错点/发音陷阱、记忆钩。
- 另有 5.1–5.3 三节规则（前缀决定边界/方向、词性后缀规律）与 15 题自测。

### 2.5 来源 E：`复习计划.md`

- Day 1 学习日 2026-11-05，固定间隔 `+1/+2/+4/+7/+15` → 2026-11-06 / 07 / 09 / 12 / 20。
- 其余 Day 2–12 为"待录入"占位，不构成真实数据。

---

## 3. 数据质量与冲突分析

1. **跨源无重复**：39 条词目（20 + 19）无交集，fins/volv 组与 work/stat 组是两套独立来源。
2. **同源异构**：20 词在旧图 / xlsx / md 三处字段不同。合并规则：音标以旧图为准（最完整），义项与例句以 md 为准，主词层级以 xlsx 为准，冲突写入 `import_rows`。
3. **拼写变体**：`labo(u)r` 是源写法；迁移为 `lexeme.headword = "labor"`，`spellings` 保留 `labor`、`labour`、`labo(u)r` 三种，`variant_type` 区分标准/英式/源写法。
4. **短语识别**：`work against/on/out` 是动词短语，不是单词；`patchwork`、`workplace` 等是合成词，需与短语分开建实体。
5. **词源不确定性**：旧图与 md 中的"fin = 边界""stat = 站立"来自教学材料，不是可核验的权威词源。迁移为 `etymologies`（`confidence = medium`，`status = pending_review`），**不标 verified**。
6. **关系语义缺失**：旧图边只表达"谁连着谁"，无法区分词源、派生、短语、语义、主题、学习关联。迁移时按结构推断为 `learning` / `derivation_candidate` / `semantic`，全部带来源，词源类进审核队列。
7. **ID 问题**：`d1-01` 这类按日编号的 id 不能作为标准词条 ID；迁移后用自增主键 + `headword_norm` 唯一键。
8. **学习记录缺失**：唯一的学习状态是 `词库.html` 的 `localStorage["trellis.mastered.v1"]`（已掌握集合），属于 UI 状态，不是正式记录，不迁移为复习状态，仅在迁移报告中记录为"未发现正式学习历史"。

---

## 4. 代码结构审计

- 三套前端实现并存：
  - `词库.html`：浅色列表 + 搜索 + localStorage 掌握标记。
  - `词库网络图.html`：浅色 Canvas 力导向，数据来自 `words.js`，三根九支，点击面板。
  - `词族网络图.html`：深色 Canvas 力导向，内嵌 20 词，含自测模式、图例过滤、搜索、复位。
- 两个 Canvas 图各自实现物理布局与交互，**约 60% 逻辑重复**（拖拽、缩放、拾取、高亮、面板）。
- 所有业务数据要么在 `words.js`，要么在 HTML 内嵌常量；新增词必须手改 JS 再重开页面，无法增量管理。
- 无后端、无数据库、无 API、无鉴权（纯本地 file:// 打开）。

---

## 5. 目标数据库设计（初稿）

规范化表（共 27 张，按领域分组）：

**词典**：`lexemes`、`spellings`、`pronunciations`、`senses`、`examples`、`collocations`、`morphemes`、`lexeme_morphemes`、`etymologies`、`lexeme_traits`、`sense_contrasts`

**图谱**：`graph_nodes`、`graph_edges`、`graph_layouts`、`graph_review_queue`、`data_sources`

**词书/学习**：`books`、`units`、`unit_words`、`study_plans`、`study_plan_units`、`study_sessions`、`study_events`

**记忆**：`users`、`memory_cards`、`review_states`、`review_logs`

**数据管理**：`import_jobs`、`import_rows`

关键约束：

- `lexemes.headword` 不作为唯一键（允许同形异义）；`lexemes(headword_norm, kind, homograph_no)` 唯一。
- `spellings(lexeme_id, spelling)` 唯一，`variant_type ∈ {standard, british, american, source_form}`。
- `graph_edges` 必须有 `relation_type ∈ {etymology, derivation, phrase, semantic, thematic, learning}`、`status ∈ {pending_review, approved, rejected}`、`source_id`、`directed`。
- 所有外键 `ON DELETE` 明确：`senses/pronunciations/spellings` 级联删除；`review_logs` 保留（`restrict` + 归档）；`unit_words` 级联。
- 时间统一 UTC 存储；SQLite 使用 WAL 模式；FTS5 用于英文与中文检索（中文用 unicode61 + 应用层兜底）。

迁移预测（去重后）：`lexemes` 39、`spellings` 40（labo(u)r 三形）、`senses` 约 70、`examples` 约 60、`collocations` 约 80、`graph_nodes` 约 46、`graph_edges` 约 57、`etymologies` 约 5（待审核）、`books` 2、`units` 2（词族单元 + Day 1 单元）、`study_plans` 1。

---

## 6. 迁移规划（P4）

1. **解析层**：`words.js`（node/eval 或 JSON 化）、旧图 `NODES/EDGES`（正则提取 + eval）、xlsx（openpyxl）、md（标题正则）、复习计划（表格解析）。
2. **暂存层**：写入 `import_jobs` / `import_rows`，记录来源文件、行号、原始字段。
3. **规范化层**：headword 规范化（小写、`labo(u)r → labor`）、去重（`labour/labor`）、短语/合成词判定、义项拆分。
4. **提交层**：单事务写入；幂等键 `(headword_norm, kind)`；已存在则更新非空字段，不删除已有义项。
5. **关系层**：root→branch→word 迁移为 `learning` 边（approved，source=legacy_graph）；派生候选为 `derivation` 边（pending_review）；career↔labor 为 `semantic` 边（approved）；词源断言进 `etymologies`（pending_review）。
6. **报告层**：输出 `docs/Trellis-Data-Migration-Report.md`（前后数量、去重、冲突、失败）。
7. **回滚**：迁移前备份数据库；脚本可重复执行；失败整体回滚。

---

## 7. 风险与回滚方案

| 风险 | 影响 | 缓解 |
|---|---|---|
| 旧图 HTML 数据靠正则提取 | 解析失败 | 解析失败即中止并报告，不写入半成品；解析结果先落盘 JSON 供核对 |
| 词源断言被误当事实 | 知识错误 | 全部 `pending_review`，前端显示"待审核"徽标 |
| Conda 环境创建失败 | 阻塞 | 保留 `environment.yml`，失败时回退 bundled Python 并记录（不装 base） |
| 前端重写丢失现有视觉 | 体验回退 | 保留 legacy 文件；新前端沿用同一色板与布局 |
| 无 git 基线 | 无法回滚 | P0 末尾 `git init` + 基线提交 |
| 数据误删 | 不可逆 | 迁移脚本只增不删；删除操作走软删除（`archived_at`） |

---

## 8. 环境审计

- Conda 25.3.0，位于 `E:\anaconda3`；`envs_dirs` 依次为 `C:\Users\MSIPC\.conda\envs`、`E:\anaconda3\envs`、`C:\Users\MSIPC\AppData\Local\conda\conda\envs`。
- `trellis` 环境**不存在**，将按环境名创建（装到默认 `C:\Users\MSIPC\.conda\envs\trellis`）。
- Python 3.11 可用；Node 24.19.0、npm 11.17.0；pypi（200）与 npm registry（PONG）均可访问。
- 无 git 仓库、无后端、无数据库。

---

## 9. 分阶段计划

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | 本报告 + git 基线 | 报告落盘、基线提交 |
| P1 | `trellis` conda 环境 + pyproject | `python -c "import fastapi, sqlalchemy, alembic, openpyxl"` 通过 |
| P2 | 目录重构 + legacy 归位 | 原文件保留，结构就位 |
| P3 | SQLite 模型 + Alembic | 空库迁移成功、约束生效 |
| P4 | 迁移脚本 + 报告 | 39 词入库，重跑不重复 |
| P5 | FastAPI | OpenAPI 文档 + 接口测试 |
| P6 | React 前端 | 词库/详情/学习页可用 |
| P7 | Cytoscape 图谱 | 学习/探索双模式 |
| P8 | FSRS + 固定间隔 | 到期计算与提交正确 |
| P9 | 导入与审核 | Excel/CSV/JSON 幂等导入 |
| P10 | Windows 脚本 | setup/start/test/backup 可运行 |
| P11 | 测试 + 验收 | pytest/Vitest/Playwright 通过 |

---

## 10. 需确认事项

1. 环境位置：默认 `C:\Users\MSIPC\.conda\envs\trellis`（可用 `-p E:\anaconda3\envs\trellis` 改到 E 盘）。
2. 是否允许 `git init`（用于回滚基线）。
3. 词书命名：建议 `Trellis 词族词库（fin/volv）` 与 `Trellis 12 天词汇`。
4. 旧版静态页面保留在 `legacy/` 只读，是否接受（不删除、不覆盖）。
