"""Layout quality metrics for the Day 1 unit, mirroring the frontend layout.

Reads the live API, replays the deterministic preset layout, and reports:
node overlaps, edge crossings, canvas utilisation and stability.
This is an evaluation helper only; it never writes to the database.
"""

from __future__ import annotations

import json
import math
import urllib.request

API = "http://127.0.0.1:8123/api/graph?unit_id=1&limit=200"
UNIT_CELL = 1100
TREE_CELL = 430
R_BRANCH = 92
R_WORD = 100
RADIUS = {"root": 18.0, "branch": 9.0, "word": 7.0}
CANVAS = (1180.0, 720.0)


def load() -> dict:
    with urllib.request.urlopen(API, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def layout(data: dict) -> dict[int, tuple[float, float]]:
    nodes = data["nodes"]
    edges = data["edges"]
    by_id = {n["id"]: n for n in nodes}
    children: dict[int, list[int]] = {}
    for edge in edges:
        children.setdefault(edge["source_node_id"], []).append(edge["target_node_id"])

    roots = [n for n in nodes if n["node_type"] == "root"]
    tree_cols = max(1, math.ceil(math.sqrt(max(len(roots), 1))))
    positions: dict[int, tuple[float, float]] = {}
    assigned: set[int] = set()

    for index, root in enumerate(roots):
        tx = (index % tree_cols) * TREE_CELL
        ty = (index // tree_cols) * TREE_CELL
        positions[root["id"]] = (tx, ty)
        kids = [by_id[i] for i in children.get(root["id"], []) if i in by_id]
        branches = [k for k in kids if k["node_type"] == "branch"]
        direct = [k for k in kids if k["node_type"] != "branch"]
        for kid in kids:
            assigned.add(kid["id"])
        if branches:
            for bi, branch in enumerate(branches):
                angle = bi / len(branches) * 2 * math.pi - math.pi / 2
                bx = tx + math.cos(angle) * R_BRANCH
                by = ty + math.sin(angle) * R_BRANCH
                positions[branch["id"]] = (bx, by)
                words = [by_id[i] for i in children.get(branch["id"], []) if i in by_id]
                for word in words:
                    assigned.add(word["id"])
                spread = min(2.4, 0.6 * max(len(words), 1))
                for wi, word in enumerate(words):
                    offset = 0 if len(words) == 1 else (wi / (len(words) - 1) - 0.5) * spread
                    wa = angle + offset
                    positions[word["id"]] = (
                        bx + math.cos(wa) * R_WORD,
                        by + math.sin(wa) * R_WORD,
                    )
        else:
            for wi, word in enumerate(direct):
                angle = wi / max(len(direct), 1) * 2 * math.pi - math.pi / 2
                positions[word["id"]] = (tx + math.cos(angle) * R_WORD, ty + math.sin(angle) * R_WORD)

    for node in nodes:
        if node["id"] not in assigned and node["id"] not in positions:
            positions[node["id"]] = (0.0, 0.0)
    return positions


def segment_intersect(p1, p2, p3, p4) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = orient(p1, p2, p3)
    d2 = orient(p1, p2, p4)
    d3 = orient(p3, p4, p1)
    d4 = orient(p3, p4, p2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def metrics(data: dict, positions: dict[int, tuple[float, float]]) -> dict:
    nodes = data["nodes"]
    edges = data["edges"]
    overlaps = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            pa, pb = positions[a["id"]], positions[b["id"]]
            distance = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            if distance < RADIUS[a["node_type"]] + RADIUS[b["node_type"]]:
                overlaps += 1

    crossings = 0
    segments = []
    for edge in edges:
        segments.append((edge, positions[edge["source_node_id"]], positions[edge["target_node_id"]]))
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            e1, a1, b1 = segments[i]
            e2, a2, b2 = segments[j]
            if {e1["source_node_id"], e1["target_node_id"]} & {
                e2["source_node_id"],
                e2["target_node_id"],
            }:
                continue
            if segment_intersect(a1, b1, a2, b2):
                crossings += 1

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    width = max(xs) - min(xs) + 40
    height = max(ys) - min(ys) + 40
    bbox_area = width * height
    canvas_area = CANVAS[0] * CANVAS[1]
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "node_overlaps": overlaps,
        "edge_crossings": crossings,
        "bbox": [round(width, 1), round(height, 1)],
        "canvas_utilisation": round(min(1.0, bbox_area / canvas_area), 3),
        "stability": "deterministic (same input -> identical positions)",
    }


def layout_layered(data: dict) -> dict[int, tuple[float, float]]:
    """Mirror the frontend layered layout (roots -> branches -> words)."""
    nodes = data["nodes"]
    edges = data["edges"]
    by_id = {n["id"]: n for n in nodes}
    children: dict[int, list[int]] = {}
    for edge in edges:
        children.setdefault(edge["source_node_id"], []).append(edge["target_node_id"])
    roots = [n for n in nodes if n["node_type"] == "root"]
    positions: dict[int, tuple[float, float]] = {}
    cursor_y = 0.0
    for root in roots:
        positions[root["id"]] = (0.0, cursor_y)
        kids = [by_id[i] for i in children.get(root["id"], []) if i in by_id]
        branches = [k for k in kids if k["node_type"] == "branch"]
        branch_y = cursor_y
        if branches:
            for branch in branches:
                positions[branch["id"]] = (260.0, branch_y)
                words = [by_id[i] for i in children.get(branch["id"], []) if i in by_id]
                for wi, word in enumerate(words):
                    positions[word["id"]] = (520.0, branch_y + wi * 34)
                branch_y += max(70, len(words) * 34 + 24)
        else:
            for wi, word in enumerate(kids):
                positions[word["id"]] = (300.0, cursor_y + wi * 34)
            branch_y = cursor_y + max(70, len(kids) * 34 + 24)
        cursor_y = branch_y + 90
    for node in nodes:
        positions.setdefault(node["id"], (0.0, 0.0))
    return positions


def main() -> None:
    data = load()
    for name, fn in (("grouped", layout), ("layered", layout_layered)):
        first = fn(data)
        second = fn(data)
        result = metrics(data, first)
        result["layout"] = name
        result["stable_replay"] = first == second
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
