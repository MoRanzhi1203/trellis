# Trellis 数据库结构说明

- 引擎：SQLite（WAL 模式，`PRAGMA foreign_keys=ON`）
- ORM：SQLAlchemy 2.x（`Mapped` 类型注解）
- 迁移：Alembic（`backend/alembic/versions/0f6fb4477299_initial_schema.py`）
- 文件：`data/local/trellis.db`（不入 Git）

## 1. 词典领域

| 表 | 作用 | 关键约束 |
|---|---|---|
| `lexemes` | 标准词条 | 唯一 `(headword_norm, kind, homograph_no)`；`kind ∈ word/phrase/morpheme` |
| `spellings` | 拼写与变体 | 唯一 `(lexeme_id, spelling)`；`variant_type ∈ standard/british/american/source_form` |
| `pronunciations` | 音标 | 唯一 `(lexeme_id, ipa, accent)` |
| `senses` | 词性与义项 | 唯一 `(lexeme_id, order_no)` |
| `examples` | 例句 | 关联 `senses`，级联删除 |
| `collocations` | 搭配 | 关联 `senses`，级联删除 |
| `morphemes` | 词根/前缀/后缀 | 唯一 `(form, type)` |
| `lexeme_morphemes` | 词条-词素 | 唯一 `(lexeme_id, morpheme_id, role)` |
| `etymologies` | 词源/构词说明 | `confidence ∈ low/medium/high`；`status ∈ pending_review/approved/rejected` |
| `lexeme_traits` | 主词层级、记忆成本 | 1:1 |
| `sense_contrast_groups` / `sense_contrast_items` | 近义辨析 | 组内唯一词条 |

## 2. 图谱领域

| 表 | 作用 | 关键约束 |
|---|---|---|
| `graph_nodes` | 节点（root/branch/word/affix） | 可关联 `lexeme`、`morpheme`、`unit` |
| `graph_edges` | 关系边 | 唯一 `(source, target, relation_type)`；`relation_type ∈ etymology/derivation/phrase/semantic/thematic/learning`；`status` 三态 |
| `graph_layouts` | 用户布局 | 唯一 `name` |
| `graph_review_queue` | 待审核关系 | 1:1 `edge` |
| `data_sources` | 数据出处 | 唯一 `name` |

## 3. 词书与学习

| 表 | 作用 |
|---|---|
| `books` / `units` / `unit_words` | 词书、单元、单元-词条（多对多） |
| `study_plans` / `study_plan_units` | 学习计划与单元排期 |
| `study_sessions` / `study_events` | 学习会话与行为记录 |

## 4. 记忆系统

| 表 | 作用 | 关键约束 |
|---|---|---|
| `memory_cards` | 记忆卡 | 唯一 `(lexeme_id, card_type)`；类型 `en_to_zh/zh_to_en/spelling/derivation/collocation` |
| `review_states` | 调度状态 | 1:1 `card`；`mode ∈ fixed/fsrs`；存 stability/difficulty/due_at/fixed_stage |
| `review_logs` | 复习事件 | `client_token` 唯一（幂等）；记录前后状态 |
| `users` | 本地用户 | 单用户预留 |

## 5. 数据管理

| 表 | 作用 |
|---|---|
| `import_jobs` / `import_rows` | 导入任务与逐行结果 |

## 6. 设计要点

- **全局 ID**：整数主键；`d1-01` 这类日编号不进入数据库。
- **多单元复用**：同一 `lexeme` 可关联多个 `unit_words`。
- **关系治理**：词源与主题关联分表/分类型存储；未核实关系一律 `pending_review`。
- **删除策略**：词条默认归档；示例与搭配随义项级联；学习历史通过 `StudyEvent` 快照保留。
- **时间**：UTC 存储，前端按本地时区展示。
- **索引**：`headword_norm`、`spelling`、`graph_nodes.label`、`graph_edges.source/target`、`review_states.due_at` 等。

## 7. 迁移命令

```powershell
conda run -n trellis python -m alembic -c backend/alembic.ini upgrade head
conda run -n trellis python -m alembic -c backend/alembic.ini downgrade -1
```
