# Trellis 数据迁移报告

> 执行方式：`python backend/scripts/import_legacy.py`（可重复执行）
> 数据库：`data/local/trellis.db`（SQLite，Alembic 版本 `0f6fb4477299`）
> 迁移时间：2026-11-05

## 1. 迁移来源

| 来源 | 文件 | 解析方式 |
|---|---|---|
| A | `data/words.js` | Node 求值后输出 JSON |
| B | `词族网络图.html`（NODES/EDGES 常量） | Node 正则提取 + 求值 |
| C | `词族词库_fin-volv.xlsx`（5 表） | openpyxl |
| D | `词族知识库_fin-volv.md`（20 条） | 标题 + 分节正则 |
| E | `复习计划.md` | 结构化读取（固定间隔计划） |

## 2. 迁移结果

| 项目 | 数量 |
|---|---|
| 原始词目记录 | 39（20 + 19，跨源无交集） |
| 标准词条 `lexemes` | 39 |
| 拼写 `spellings` | 41（`labor` / `labour` / `labo(u)r` 三形） |
| 音标 `pronunciations` | 20 |
| 义项 `senses` | 107 |
| 例句 `examples` | 37 |
| 搭配 `collocations` | 85 |
| 词素 `morphemes` | 15 |
| 词条-词素关联 | 40 |
| 构词/词源记录 `etymologies` | 49（全部 `pending_review`） |
| 词书 `books` | 2 |
| 单元 `units` | 2（词族单元 + Day 1） |
| 单元词条 `unit_words` | 39 |
| 图谱节点 `graph_nodes` | 65（root 8 / branch 18 / word 39） |
| 图谱边 `graph_edges` | 88 |
| 　· learning（已核实教学结构） | 66 |
| 　· semantic（语义关联） | 2 |
| 　· derivation（待审核） | 20 |
| 学习计划 `study_plans` | 1（固定间隔，2026-11-05 起） |

## 3. 去重与合并规则

- 标准词条键：`(headword_norm, kind, homograph_no)`；同源重复合并、跨源合并。
- 义项键：`(lexeme_id, pos, definition_zh)`；重复不新增。
- 搭配键：`(sense_id, pattern)`；例句键：`(sense_id, text)`。
- 图节点键：`(node_type, label, unit_id)`；边键：`(source, target, relation_type)`。
- 单元-词条：`(unit_id, lexeme_id)`，同一词可出现在多个单元。

## 4. 拼写变体

`labo(u)r` 不再作为标准词形：

- 标准：`labor`
- 英式：`labour`
- 源写法：`labo(u)r`（`variant_type = source_form`，`is_primary = 0`）

重复执行迁移不会重新创建 `labo(u)r` 词条。

## 5. 关系分类

| 类型 | 来源 | 状态 |
|---|---|---|
| `learning` | 旧图 root→branch→word、words.js graph | `approved`（教学结构，不代表词源） |
| `semantic` | `career` ↔ `labor` 虚线 | `approved`（语义关联） |
| `derivation` | xlsx 构词公式、md 构词说明 | `pending_review`（需人工审核） |
| `etymology` | xlsx/md/旧图构词说明 | `pending_review`，**不自动升级为事实** |

## 6. 一致性验证

| 检查 | 结果 |
|---|---|
| 重复执行两次后的词条数 | 39 → 39 |
| 重复执行两次后的边数 | 88 → 88 |
| 悬空边（指向不存在节点） | 0 |
| 重复 headword（active） | 0 |
| 无来源词条 | 0（全部带 `data_sources` 记录） |
| 词条出现在多个单元 | 支持（`unit_words` 多对多） |

## 7. 已知限制

1. `etymologies` 全部为待审核，前端以「待审核」标签显示，不应作为已核实词源使用。
2. 旧图 `formula` 字段含 HTML，迁移时已去标签，未做语义解析。
3. `自测15题` 未进入记忆卡，仅保留在 Excel 中，待后续按导入任务处理。
4. `might` 的「一词两身份」未拆分为两个词条，保留在义项与备注中。
