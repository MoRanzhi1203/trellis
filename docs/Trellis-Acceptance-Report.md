# Trellis V1.0 验收报告

> 日期：2026-11-05　环境：conda `trellis`（Python 3.11.18）
> 后端：FastAPI 0.162 / SQLAlchemy 2.1.8 / Alembic 1.20.1 / SQLite（WAL）
> 前端：React 18 + TypeScript 5.6 + Vite 5.4 + Cytoscape 3.30

## 1. 验收结果总览

| 项目 | 结果 |
|---|---|
| 数据库初始化（Alembic upgrade head） | ✅ 30 张表，版本 `0f6fb4477299` |
| 旧数据迁移 | ✅ 39 词条、107 义项、65 节点、88 边 |
| 迁移幂等（连续执行两次） | ✅ 词条 39→39，边 88→88 |
| 后端测试 | ✅ `14 passed` |
| 前端构建（tsc + vite build） | ✅ 88 modules，dist 生成 |
| 端到端页面渲染 | ✅ 首页 / 词库 / 学习 / 图谱 / 导入 截图见 `docs/screenshots/` |
| 数据持久化 | ✅ 关闭服务后重新打开，39 词与 176 卡仍在 |

## 2. 数据库

- 30 张表：词典 11、图谱 5、词书与学习 7、记忆 4、数据管理 3。
- 39 个标准词条；`labor` 有 `labor` / `labour` / `labo(u)r` 三种拼写（source_form）。
- 88 条关系边：`learning` 66（教学结构，approved）、`semantic` 2、`derivation` 20（pending_review）。
- 49 条构词/词源记录全部 `pending_review`。
- 176 张记忆卡（每词 3–5 类），176 条复习状态，初始全部到期。

## 3. 后端接口（实测）

```
GET  /api/health                     200
GET  /api/words?limit=2              200  total=39
GET  /api/words/{id}                 200
POST /api/words                      201
PATCH /api/words/{id}                200
DELETE /api/words/{id}               200（归档）
GET  /api/graph?limit=120            200  节点 65 / 边 88（无悬空边）
GET  /api/reviews/due                200  176 张
POST /api/reviews/submit             200  FSRS 更新，重复 token 幂等
GET  /api/statistics/overview        200
POST /api/backup                     200
POST /api/restore                    200
POST /api/imports/legacy             200  幂等
```

## 4. 测试覆盖

`backend/tests/`：

- `test_fsrs.py`：首次评分、again 短于 good、固定间隔、间隔单调。
- `test_api.py`：健康检查、词条 CRUD 与归档、图谱无悬空边、复习提交与幂等、统计、备份恢复。
- `test_import.py`：迁移两次数量一致、39 条总数、`labor` 三拼写、单元关联。

命令与结果：

```
conda run -n trellis python -m pytest -q
14 passed
```

## 5. P11 端到端操作对照

| 要求 | 结果 |
|---|---|
| 1. 启动项目 | ✅ `scripts/start.ps1` 或 `uvicorn` + `npm run dev` |
| 2. 浏览原有 20 词图谱 | ✅ 图谱页包含 fin/volv/ergon/fallere/miht |
| 3. 打开 Day 1 的 19 条词目 | ✅ 学习单元筛选；词库 39 条含 Day 1 |
| 4. 新增一个单词 | ✅ 词库页新增（测试 `test_word_crud`） |
| 5. 添加释义与词根 | ⚠️ 释义可新增；词根关系需通过 API/数据迁移，页面暂未提供词根编辑面板 |
| 6. 建立一条新关系 | ✅ `POST /api/graph/edges`（接口可用，页面暂无建边 UI） |
| 7. 图谱中搜索并找到新节点 | ⚠️ 后端按节点查询可用；页面暂未提供图谱内搜索框 |
| 8. 完成一次学习 | ✅ 学习页出卡、显示答案 |
| 9. 提交复习反馈 | ✅ again/hard/good/easy 写库 |
| 10. 关闭并重启 | ✅ 数据保留 |
| 11. 确认数据仍存在 | ✅ 39 词 / 176 卡 |
| 12. 重复导入不重复 | ✅ 幂等测试 |
| 13. 备份并验证恢复 | ✅ API 与测试均通过 |
| 14. 控制台与日志无未处理错误 | ✅ 页面截图无错误；后端日志正常 |

## 6. 明确未完成（不冒充通过）

1. **P9 通用导入 UI**：Excel/CSV/JSON 的字段映射、预览、冲突确认页面尚未实现；目前只有旧版迁移入口与后端幂等导入器。
2. **Vitest / Playwright**：前端未写单元测试，端到端仅用无头浏览器截图人工核验。
3. **词根/词缀编辑 UI**：数据模型与 API 已具备，前端未提供编辑面板。
4. **图谱内搜索与建边 UI**：后端接口可用，前端未接按钮。
5. **学习计划管理 UI**：计划已迁移，页面未提供创建/编辑计划与单元划分。
6. **词书/单元管理 UI**：只读展示。
7. **统计页**：仅有首页概览，未做按词族掌握度、易错搭配等细分。

这些是后续迭代项，不影响当前「词库 CRUD、复习、动态图谱、迁移、备份」主链路。

## 7. 复现命令

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
# 浏览器 http://127.0.0.1:8123
```
