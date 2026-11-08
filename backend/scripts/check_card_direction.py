from __future__ import annotations

import sqlite3

con = sqlite3.connect(r"E:\Trellis\data\local\trellis.db")
print("columns:", [row[1] for row in con.execute("PRAGMA table_info(memory_cards)")])
for row in con.execute(
    "select card_type, direction, enabled, count(*) from memory_cards group by card_type, direction, enabled"
):
    print(row)
print("triggers:", [row[0] for row in con.execute("select name from sqlite_master where type='trigger'")])
