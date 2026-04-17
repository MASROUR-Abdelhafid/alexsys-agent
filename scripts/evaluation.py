"""
Évaluation & Métriques — Système KPI Aciérie Maghreb Steel
Mesure : Précision, Rappel, F1, Latence, Disponibilité RAG
"""

import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

# ── Jeu de tests étendu ─────────────────────────────────────────
EVAL_CASES = [
    # KPI Gold — précision des valeurs
    {"q": "Quel est le taux de disponibilité EAF ?",        "type": "kpi", "expect": "81",       "kpi": "taux_disponibilite"},
    {"q": "Quelle est la consommation électrique totale ?", "type": "kpi", "expect": "54",        "kpi": "consommation_electrique"},
    {"q": "Combien de coulées ont été produites ?",         "type": "kpi", "expect": "929",       "kpi": "production_coulees"},
    {"q": "Quels sont les défauts les plus fréquents ?",    "type": "kpi", "expect": "tracemould","kpi": "defauts_brames"},
    {"q": "Quelle est la consommation d oxygène EAF ?",     "type": "kpi", "expect": "3328112",   "kpi": "consommation_oxygene"},
    {"q": "Quel est le poids moyen des brames ?",           "type": "kpi", "expect": "17560",     "kpi": "production_brames"},
    {"q": "Quelle est la consommation électrique par mois ?","type": "kpi","expect": "mwh",       "kpi": "consommation_electrique"},
    # Routing — classification correcte
    {"q": "Comment fonctionne le four EAF ?",               "type": "doc", "expect": "eaf",       "kpi": None},
    {"q": "Quel est le rôle du four LF ?",                  "type": "doc", "expect": "four lf",   "kpi": None},
    {"q": "Comment fonctionne la coulée continue CCM ?",    "type": "doc", "expect": "ccm",       "kpi": None},
    # Direct
    {"q": "Bonjour",                                        "type": "direct", "expect": "bonjour","kpi": None},
    {"q": "Quelle est la date d aujourd hui ?",             "type": "direct", "expect": "2026",   "kpi": None},
]


def normalize(text: str) -> str:
    return text.lower().replace(" ", "").replace(",", "").replace(".", "").replace("'", "")


def run_evaluation():
    print("=" * 65)
    print("ÉVALUATION — Système KPI Aciérie Maghreb Steel")
    print("=" * 65)

    results = []
    tp = fp = fn = 0
    latencies_kpi = []
    latencies_doc = []
    latencies_direct = []

    for i, tc in enumerate(EVAL_CASES):
        t0 = time.time()
        result = run_agent(tc["q"])
        latency = round((time.time() - t0) * 1000, 2)

        answer   = result.get("final_response", "")
        act_type = result.get("task_type", "")

        # Type correct ?
        type_ok = act_type in [tc["type"], "sql"] if tc["type"] == "kpi" else act_type == tc["type"]

        # Réponse correcte ?
        ans_ok = normalize(tc["expect"]) in normalize(answer)

        ok = type_ok and ans_ok

        # Métriques de classification
        if tc["type"] == "kpi":
            if ok: tp += 1
            elif not type_ok: fn += 1
            else: fp += 1

        # Latences par catégorie
        if tc["type"] == "kpi":      latencies_kpi.append(latency)
        elif tc["type"] == "doc":    latencies_doc.append(latency)
        else:                        latencies_direct.append(latency)

        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"[{i+1:02d}] {status} | {act_type:8} | {latency:7.0f}ms | {tc['q'][:45]}")

        results.append({
            "question":      tc["q"],
            "expected_type": tc["type"],
            "actual_type":   act_type,
            "type_correct":  type_ok,
            "answer_correct": ans_ok,
            "passed":        ok,
            "latency_ms":    latency,
        })

    # ── Calcul métriques ────────────────────────────────────────
    total   = len(EVAL_CASES)
    passed  = sum(1 for r in results if r["passed"])
    accuracy = passed / total * 100

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    avg_kpi    = sum(latencies_kpi)    / len(latencies_kpi)    if latencies_kpi    else 0
    avg_doc    = sum(latencies_doc)    / len(latencies_doc)    if latencies_doc    else 0
    avg_direct = sum(latencies_direct) / len(latencies_direct) if latencies_direct else 0
    avg_all    = sum(r["latency_ms"] for r in results) / total

    print("\n" + "=" * 65)
    print("📊 MÉTRIQUES D'ÉVALUATION")
    print("=" * 65)
    print(f"  Accuracy globale     : {accuracy:.1f}%  ({passed}/{total})")
    print(f"  Précision KPI        : {precision*100:.1f}%")
    print(f"  Rappel KPI           : {recall*100:.1f}%")
    print(f"  F1-Score KPI         : {f1*100:.1f}%")
    print(f"  Latence moy. KPI     : {avg_kpi:.0f}ms")
    print(f"  Latence moy. DOC     : {avg_doc:.0f}ms")
    print(f"  Latence moy. DIRECT  : {avg_direct:.0f}ms")
    print(f"  Latence moy. globale : {avg_all:.0f}ms")
    print("=" * 65)

    # ── Sauvegarde ──────────────────────────────────────────────
    report = {
        "accuracy":     f"{accuracy:.1f}%",
        "passed":       passed,
        "total":        total,
        "precision_kpi": f"{precision*100:.1f}%",
        "recall_kpi":   f"{recall*100:.1f}%",
        "f1_kpi":       f"{f1*100:.1f}%",
        "latency_kpi_ms":    round(avg_kpi),
        "latency_doc_ms":    round(avg_doc),
        "latency_direct_ms": round(avg_direct),
        "latency_avg_ms":    round(avg_all),
        "results":      results,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("✅ Rapport sauvegardé : data/evaluation_report.json")
    return report


if __name__ == "__main__":
    run_evaluation()