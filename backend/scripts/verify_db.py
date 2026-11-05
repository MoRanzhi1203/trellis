from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "local" / "trellis.db"


def main() -> None:
    con = sqlite3.connect(DB)
    for table in [
        "lexemes",
        "spellings",
        "pronunciations",
        "senses",
        "examples",
        "collocations",
        "morphemes",
        "lexeme_morphemes",
        "etymologies",
        "books",
        "units",
        "unit_words",
        "graph_nodes",
        "graph_edges",
        "study_plans",
    ]:
        try:
            count = con.execute(f"select count(*) from {table}").fetchone()[0]
        except sqlite3.OperationalError:
            count = "missing"
        print(f"{table:20s} {count}")

    print("\nlabo(u)r row:")
    for row in con.execute(
        "select id, headword, headword_norm, kind from lexemes where headword like '%labor%' or headword like '%labour%'"
    ):
        print(row)
        lexeme_id = row[0]
        for sp in con.execute(
            "select spelling, variant_type, is_primary from spellings where lexeme_id=?", (lexeme_id,)
        ):
            print("   spelling:", sp)

    print("\nedges by type/status:")
    for row in con.execute(
        "select relation_type, status, count(*) from graph_edges group by relation_type, status"
    ):
        print(row)

    print("\nnodes by type:")
    for row in con.execute("select node_type, count(*) from graph_nodes group by node_type"):
        print(row)

    print("\nduplicate headwords:")
    for row in con.execute(
        "select headword_norm, kind, count(*) c from lexemes group by headword_norm, kind having c > 1"
    ):
        print(row)


if __name__ == "__main__":
    sys.exit(main())
