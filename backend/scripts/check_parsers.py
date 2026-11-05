from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.importers.legacy_parser import (  # noqa: E402
    parse_legacy_graph,
    parse_markdown,
    parse_words_js,
    parse_workbook,
)


def main() -> None:
    root = ROOT
    words = parse_words_js(root / "data" / "words.js")
    print("words.js days:", len(words["days"]), "words:",
          sum(len(g["words"]) for d in words["days"] for g in d["groups"]))

    graph = parse_legacy_graph(root / "词族网络图.html")
    print("legacy graph nodes:", len(graph["nodes"]), "edges:", len(graph["edges"]))

    workbook = parse_workbook(root / "词族词库_fin-volv.xlsx")
    print("workbook sheets:", {k: len(v) for k, v in workbook.items()})

    md = parse_markdown(root / "词族知识库_fin-volv.md")
    print("markdown entries:", len(md))
    if md:
        print(json.dumps(md[0], ensure_ascii=False, indent=1)[:600])


if __name__ == "__main__":
    main()
