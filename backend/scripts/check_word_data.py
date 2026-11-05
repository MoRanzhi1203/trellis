from __future__ import annotations

import sqlite3

con = sqlite3.connect(r"E:\Trellis\data\local\trellis.db")
lexemes = con.execute("select count(*) from lexemes where status='active'").fetchone()[0]
with_sense = con.execute(
    "select count(distinct lexeme_id) from senses"
).fetchone()[0]
pos_senses = con.execute("select count(*) from senses where pos != ''").fetchone()[0]
meaning_senses = con.execute("select count(*) from senses where definition_zh != ''").fetchone()[0]
multi_pos = con.execute(
    "select count(*) from (select lexeme_id, count(distinct pos) c from senses where pos != '' group by lexeme_id having c > 1)"
).fetchone()[0]
edges = con.execute("select count(*) from graph_edges").fetchone()[0]
edges_evidence = con.execute(
    "select count(*) from graph_edges where evidence != '' and evidence != 'legacy words.js graph'"
).fetchone()[0]
pending = con.execute(
    "select count(*) from graph_edges where status='pending_review'"
).fetchone()[0]
print(
    {
        "lexemes": lexemes,
        "lexemes_with_senses": with_sense,
        "senses": con.execute("select count(*) from senses").fetchone()[0],
        "senses_with_pos": pos_senses,
        "senses_with_zh": meaning_senses,
        "multi_pos_lexemes": multi_pos,
        "edges": edges,
        "edges_with_formation": edges_evidence,
        "edges_pending": pending,
    }
)
