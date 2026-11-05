# Trellis API 文档

服务地址：`http://127.0.0.1:8000`　交互式文档：`/docs`

所有接口均为 JSON；错误返回 `{"detail": "..."}`，状态码 400/404/500。

## 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |

## 词条

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/words` | 分页列表，参数：`offset`、`limit`、`q`、`kind`、`status`、`unit_id`、`book_id` |
| GET | `/api/words/search?q=` | 搜索（英文、拼写变体、中文释义） |
| GET | `/api/words/{id}` | 词条详情（拼写、音标、义项、例句、搭配、词源、特性） |
| POST | `/api/words` | 新建词条 |
| PATCH | `/api/words/{id}` | 更新词条（可整体替换义项） |
| DELETE | `/api/words/{id}` | 默认归档（`status=archived`）；`?hard=true` 物理删除 |

新建示例：

```json
{
  "headword": "resilient",
  "kind": "word",
  "senses": [
    {
      "pos": "adj.",
      "definition_zh": "有韧性的；能恢复的",
      "examples": [{ "text": "She is remarkably resilient." }],
      "collocations": [{ "pattern": "be resilient to" }]
    }
  ]
}
```

## 图谱

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/graph` | 子图，参数：`unit_id`、`node_id`、`depth`、`relation_type`、`status` |
| GET | `/api/graph/nodes/{id}` | 单节点 |
| GET | `/api/graph/nodes/{id}/neighbors` | 邻居扩展（`depth`） |
| POST | `/api/graph/edges` | 新建关系 |
| PATCH | `/api/graph/edges/{id}` | 修改关系类型/审核状态/证据 |
| DELETE | `/api/graph/edges/{id}` | 删除关系 |
| GET | `/api/graph/layouts` | 布局列表 |
| PUT | `/api/graph/layouts` | 保存/更新布局 |

关系类型：`etymology`、`derivation`、`phrase`、`semantic`、`thematic`、`learning`。
审核状态：`pending_review`、`approved`、`rejected`。

## 词书与单元

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/books` | 词书列表 |
| GET | `/api/books/{id}/units` | 单元列表（含词数） |
| GET | `/api/units/{id}/words` | 单元词条（按顺序） |
| GET | `/api/sources` | 数据来源 |

## 学习与复习

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/study/plans` | 学习计划 |
| POST | `/api/study/plans` | 新建计划（`mode=fixed|fsrs`） |
| POST | `/api/study/sessions` | 开始一次学习会话 |
| GET | `/api/reviews/due` | 到期卡片 |
| POST | `/api/reviews/submit` | 提交复习结果（FSRS 或固定间隔） |
| GET | `/api/reviews/history` | 复习历史 |
| GET | `/api/statistics/overview` | 今日统计、连续天数、薄弱词 |

提交示例：

```json
{ "card_id": 12, "result": "good", "difficulty_feedback": 3, "client_token": "uuid-..." }
```

`client_token` 用于幂等：重复提交同一 token 不会重复计分。

## 数据管理

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/imports/legacy` | 幂等导入旧版词库 |
| POST | `/api/backup` | 创建一致性备份（`data/local/backups/`） |
| POST | `/api/restore` | 从备份恢复（`{"file": "..."}`，仅限备份目录） |

## 安全边界

- 默认仅监听 `127.0.0.1`，无鉴权，适合单用户本地使用。
- 恢复接口只接受 `data/local/backups/` 下的文件名，防止目录穿越。
- 所有 SQL 通过 SQLAlchemy 参数化，导入内容不做 HTML 拼接。
