"""Visualise les logs d'audit."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log_path = "logs/audit.log"
if not os.path.exists(log_path):
    print("Aucun log d'audit trouvé.")
    sys.exit(0)

print("=" * 60)
print("AUDIT TRAIL — Aciérie Maghreb Steel")
print("=" * 60)

with open(log_path, encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total entrées : {len(lines)}\n")

kpi_count = 0
doc_count = 0
direct_count = 0

for line in lines[-20:]:
    try:
        e = json.loads(line)
        t = e.get("task_type", "")
        if t in ["kpi", "sql"]:
            kpi_count += 1
        elif t == "doc":
            doc_count += 1
        else:
            direct_count += 1
        ts = e["timestamp"][:19].replace("T", " ")
        print(f"[{ts}] {t:8} | {e.get('latency_ms',0):6.0f}ms | {e.get('query','')[:50]}")
    except Exception:
        pass

print(f"\nStats : KPI={kpi_count} | DOC={doc_count} | DIRECT={direct_count}")