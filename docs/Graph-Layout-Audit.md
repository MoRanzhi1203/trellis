# 知识图谱布局审计（Phase 0）

> 审计对象：`frontend/src/pages/Graph.tsx`、`backend/app/api/graph.py`、`backend/app/services/graph.py`、SQLite `graph_nodes` / `graph_edges`
> 结论：当前混乱不是单一算法问题，而是「数据规模 + 关系无差别绘制 + 标签常显 + 布局按单元平铺」四件事叠加。

## 1. 当前技术栈

- 可视化：Cytoscape.js 3.30（Canvas 渲染）。
- 布局：自定义确定性 `preset` 布局（`layoutPositions` + `spreadNodes`），**不是**力导向。
- 数据来源：`GET /api/graph?unit_id=&limit=`，节点 322、边 322。
- 节点类型：`root`（词根）、`branch`（语义分支，仅 Day 1）、`word`（词条）。
- 关系类型：`learning` 66、`semantic` 2、`derivation` 20（`pending_review`）。

## 2. 混乱的真实原因

| # | 原因 | 证据 |
|---|---|---|
| 1 | **探索模式把 13 个单元平铺到一个画布** | 每单元块间距 `UNIT_CELL=1100`，13 块 4×4 网格；322 节点 fit 后 zoom≈0.25，标签必然挤 |
| 2 | **所有关系默认全部绘制** | elements 未按 relation_type 过滤，`semantic` 与 20 条 `pending_review` 派生边同时出现 |
| 3 | **待审核边用橙色虚线常显** | 20 条橙色边抢视觉注意力，且不是学习主干 |
| 4 | **标签常显、字号小** | 所有 node 都渲染 `label`（11px），zoom 0.3 时屏幕 3px，互相压 |
| 5 | **节点视觉权重区分弱** | root 34px / branch 20px / word 14px，颜色按 fam 随机分配，词根不突出 |
| 6 | **每次切换单元/模式全量重建** | `view.data` 变化 → `elements` 重算 → `preset` 全量重排，无缓存 |
| 7 | **缺少关系筛选/折叠/搜索** | 工具栏只有 探索/学习单元/深色/缩放/复位 |
| 8 | **词族（单元）无视觉边界** | 只有节点间距，没有组标题/边框，13 个块分不清 |

## 3. 不是问题的部分（不要改）

- 布局已经是**确定性**的（相同数据位置相同），不需要换成随机力导向。
- 节点/边来自真实数据库，不能删除或伪造。
- 滚轮/键盘/复位逻辑正常。

## 4. P0 修复方案（本轮）

1. **关系分层**：默认只画 `learning`（核心学习主干）；`semantic` / `derivation` / `pending_review` 通过工具栏开关显示，默认关闭。
2. **默认只显示一个单元**：保留 `learning` 模式为默认（Day 1），探索模式改为显式选择，避免 322 节点一屏。
3. **标签分级**：`zoom < 0.45` 隐藏 word 标签，只留 root/branch；放大后显示。
4. **词根/单词视觉权重**：root 36px 加粗，branch 18px，word 12px；root 使用更深的边框。
5. **初始视角**：fit 后保留 36px 内边距，不强制放大，避免裁切。
6. **节点防重叠**：保留 `spreadNodes`（最小间距 38）。
7. **指标与截图**：用独立脚本复现布局，统计重叠/交叉/利用率；截图对比。

## 5. 数据完整性

本轮只改前端显示逻辑，不改数据库、不改关系状态、不自动审核。
