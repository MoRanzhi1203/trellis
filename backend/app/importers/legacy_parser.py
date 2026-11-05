"""Readers for the legacy Trellis data sources.

The legacy files are never modified: every parser only reads them.  JavaScript
sources are evaluated in a short-lived Node process (Node is already a project
dependency for the frontend), so no JS parser has to be reimplemented in Python.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import openpyxl

NODE_SCRIPT = Path(__file__).with_name("node_extract.js")
NODE_EXE = shutil.which("node") or "node"


class LegacyParseError(RuntimeError):
    pass


def _run_node(mode: str, target: Path) -> dict:
    proc = subprocess.run(
        [NODE_EXE, str(NODE_SCRIPT), mode, str(target)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise LegacyParseError(f"node extract failed for {target.name}: {proc.stderr[:500]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise LegacyParseError(f"invalid JSON from node for {target.name}") from exc


def parse_words_js(path: Path) -> dict:
    return _run_node("words", path)


def parse_legacy_graph(path: Path) -> dict:
    return _run_node("legacy-graph", path)


def parse_workbook(path: Path) -> dict[str, list[dict]]:
    wb = openpyxl.load_workbook(path, data_only=True)
    result: dict[str, list[dict]] = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            result[ws.title] = []
            continue
        header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        data: list[dict] = []
        for raw in rows[1:]:
            record = {}
            for key, value in zip(header, raw, strict=False):
                if not key:
                    continue
                record[key] = "" if value is None else str(value).strip()
            if any(record.values()):
                data.append(record)
        result[ws.title] = data
    return result


HEADING_RE = re.compile(r"^###\s+(\d+\.\d+)\s+(\S+)\s+`([^`]*)`\s*(.*)$")
BULLET_RE = re.compile(r"^\s*-\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")


def parse_markdown(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    entries: list[dict] = []
    current: dict | None = None
    section = ""
    for line in text.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            if current:
                entries.append(current)
            number, word, ipa, tail = match.groups()
            level = "主词" if "主词" in tail else ("派生" if "派生" in tail else tail.strip("— ").strip())
            pos_match = re.match(r"^([a-z]+\.(?:\s*&\s*[a-z]+\.)?)", tail.strip())
            current = {
                "number": number,
                "word": word,
                "ipa": ipa,
                "pos": pos_match.group(1) if pos_match else "",
                "level": level,
                "senses": [],
                "collocations": [],
                "examples": [],
                "construction": "",
                "notes": "",
            }
            section = ""
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- **义项**"):
            section = "senses"
            continue
        if stripped.startswith("- **搭配**"):
            section = "collocations"
            continue
        if stripped.startswith("- **例句**"):
            section = "examples"
            continue
        if stripped.startswith("- **构词**"):
            section = "construction"
            current["construction"] = stripped.split("**构词**：", 1)[-1].strip()
            continue
        if stripped.startswith("- **易错**") or stripped.startswith("- **发音陷阱"):
            section = "notes"
            current["notes"] = stripped.split("：", 1)[-1].strip()
            continue
        if stripped.startswith("- **"):
            section = ""
            continue
        if section == "senses":
            m = NUMBERED_RE.match(line)
            if m:
                current["senses"].append(m.group(1).strip())
        elif section == "collocations":
            m = BULLET_RE.match(line)
            if m and not m.group(1).startswith("**"):
                current["collocations"].append(m.group(1).strip())
        elif section == "examples":
            m = BULLET_RE.match(line)
            if m:
                current["examples"].append(m.group(1).strip())
    if current:
        entries.append(current)
    return entries
