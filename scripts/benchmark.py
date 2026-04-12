"""
Benchmark Phase 6 — Tests formels du système.
10 questions test avec validation des réponses.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

TEST_CASES = [
    {"q": "Quel est le taux de disponibilité EAF ?",          "type": "kpi",    "expect": "81"},
    {"q": "Quelle est la consommation électrique totale ?",   "type": "kpi",    "expect": "54"},
    {"q": "Combien de coulées ont été produites ?",           "type": "kpi",    "expect": "929"},
    {"q": "Quels sont les défauts les plus fréquents ?",      "type": "kpi",    "expect": "Trace Mould"},
    {"q": "Quelle est la consommation d oxygène EAF ?",       "type": "kpi",    "expect": "3 328"},
    {"q": "Quel est le poids moyen des brames ?",             "type": "kpi",    "expect": "17 560"},
    {"q": "Quelle est la consommation électrique par mois ?", "type": "kpi",    "expect": "MWh"},
    {"q": "Comment fonctionne le four EAF ?",                 "type": "doc",    "expect": "électrique"},
    {"q": "Quel est le rôle du four LF ?",                    "type": "doc",    "expect": "affinage"},
    {"q": "Bonjour",                                          "type": "direct", "expect": "Bonjour"},
]


def run_benchmark():
    print("=" * 65)
    print("BENCHMARK — Système KPI Aciérie Maghreb Steel")
    print("=" * 65)

    results = []
    total_latency = 0
    passed = 0

    for i, tc in enumerate(TEST_CASES):
        t0 = time.time()
        result = run_agent(tc["q"])
        latency = round((time.time() - t0) * 1000, 2)
        total_latency += latency

        answer = result.get("final_response", "")
        task_type = result.get("task_type", "")
        type_ok = task_type in [tc["type"], "sql"] if tc["type"] == "kpi" else task_type == tc["type"]
        answer_ok = tc["expect"].lower().replace(" ", "") in answer.lower().replace(" ", "").replace(",", "").replace(".", "")
        ok = type_ok and answer_ok
        if ok:
            passed += 1

        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"\n[{i+1:02d}] {status} | {task_type:8} | {latency:6.0f}ms")
        print(f"     Q: {tc['q']}")
        print(f"     R: {answer[:80]}...")

        results.append({
            "question": tc["q"],
            "expected_type": tc["type"],
            "actual_type": task_type,
            "latency_ms": latency,
            "passed": ok,
        })

    print("\n" + "=" * 65)
    print(f"RÉSULTATS : {passed}/{len(TEST_CASES)} tests passés")
    print(f"Latence moyenne : {total_latency/len(TEST_CASES):.0f}ms")
    print(f"Taux de succès  : {passed/len(TEST_CASES)*100:.0f}%")
    print("=" * 65)

    os.makedirs("data", exist_ok=True)
    with open("data/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "total": len(TEST_CASES),
            "passed": passed,
            "success_rate": f"{passed/len(TEST_CASES)*100:.0f}%",
            "avg_latency_ms": round(total_latency/len(TEST_CASES), 0),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print("\n✅ Résultats sauvegardés : data/benchmark_results.json")


if __name__ == "__main__":
    run_benchmark()