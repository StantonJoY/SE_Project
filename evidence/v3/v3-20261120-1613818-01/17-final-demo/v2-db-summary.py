import json
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
requests = db.execute(
    "SELECT request_id, ad_id, charge_cents FROM requests ORDER BY rowid"
).fetchall()
selected = {row[1] for row in requests if row[1]}
rows = db.execute(
    "SELECT ad_id, total_cents, spent_cents, remaining_cents, status "
    "FROM budget ORDER BY ad_id"
).fetchall()
rows = [row for row in rows if row[0] in selected]
print(json.dumps({
    "audit_count": db.execute("SELECT COUNT(*) FROM audit").fetchone()[0],
    "requests": requests,
    "selected_budgets": rows,
}, ensure_ascii=False, indent=2))
