from __future__ import annotations

import sqlite3

con = sqlite3.connect(r"E:\Trellis\data\local\trellis.db")
for table in ("memory_cards", "review_states"):
    print(table, con.execute(f"select count(*) from {table}").fetchone()[0])
print("due", con.execute("select count(*) from review_states where due_at <= datetime('now')").fetchone()[0])
print(con.execute("select card_type, prompt, answer from memory_cards limit 3").fetchall())
