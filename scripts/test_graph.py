"""Test graphe complet Aciérie."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

questions = [
    "Quel est le taux de disponibilite EAF ?",
    "Quelle est la consommation electrique totale ?",
    "Quels sont les defauts les plus frequents sur les brames ?",
    "Comment fonctionne le four EAF ?",
]

for q in questions:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print('='*60)
    result = run_agent(q)
    print(f"Type     : {result['task_type']}")
    print(f"Plan     : {result['plan']}")
    print(f"Réponse  : {result['final_response'][:300]}...")
    print(f"Actions  : {len(result['action_history'])} étapes")