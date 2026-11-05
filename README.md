# Trellis · 词汇知识图谱与智能记忆系统

Trellis V1.0 把原来的静态 HTML/JS 词库升级为数据库驱动的 Web 应用：

- **后端**：Python 3.11 + FastAPI + SQLite + SQLAlchemy 2.x + Alembic
- **前端**：React + TypeScript + Vite + TanStack Query + Cytoscape.js
- **复习**：FSRS-5 与旧版固定间隔（+1/+2/+4/+7/+15 天）双模式
- **数据**：旧版 `words.js`、`词族网络图.html`、Excel、Markdown 一次性幂等迁移

原有文件全部保留，不改不删；新系统通过 `legacy` 迁移读写数据库。

## 目录

```
Trellis/
├─ backend/            FastAPI、SQLAlchemy 模型、Alembic、导入器、测试
├─ frontend/           React + Vite 前端
├─ data/
│  ├─ words.js         旧数据（只读）
│  └─ local/           数据库与备份（不入 Git）
├─ docs/               P0 审计、API、数据库、用户说明、迁移报告
├─ scripts/            setup / start / test / backup
├─ legacy/             旧版静态页面预留目录
└─ 词库.html 等         旧版页面（保留）
```

## 快速开始

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

- 前端 <http://127.0.0.1:8123>
- 接口文档 <http://127.0.0.1:8123/docs>

手动方式：

```powershell
conda create -n trellis python=3.11 pip -y
conda activate trellis
python -m pip install -e "backend[dev]"
cd backend
python -m alembic upgrade head
python scripts/import_legacy.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

cd ..\frontend
npm install
npm run dev
```

## 测试

```powershell
cd backend
conda run -n trellis python -m pytest -q
```

当前后端测试覆盖：数据库初始化、词条 CRUD、归档、图谱无悬空边、复习提交与幂等、统计、备份恢复、迁移幂等、拼写变体。

## 数据迁移

```powershell
conda run -n trellis python backend/scripts/import_legacy.py
```

迁移报告见 `docs/Trellis-Data-Migration-Report.md`，审计见 `docs/Trellis-P0-Audit.md`。

## 关键设计

- 210 个标准词条、2 个词书、13 个单元（12 天计划 + 1 个词族单元）；同一词条可属于多个单元。
- 12 天计划完整：Day 1（11-05）到 Day 12（11-16），Day 2–11 来自 12 张词表截图。
- 词源与构词说明全部 `pending_review`，不冒充已核实词源。
- 关系边有类型、方向、来源和审核状态。
- 学习记录与词条分离；编辑词条不删除复习历史。
- 数据库与备份不进 Git，服务默认只监听 `127.0.0.1`。

## 状态

- P0 审计、P1 环境、P3 数据库、P4 迁移、P5 API、P8 复习调度：已完成并有测试。
- P6 前端、P7 图谱：页面与 Cytoscape 集成已完成，构建校验见验收报告。
- P9 通用导入（Excel/CSV/JSON 预览）、Playwright 端到端：见 `docs/` 中的遗留项。
