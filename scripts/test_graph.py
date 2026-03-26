import os
import sys

# Ajout au PYTHONPATH pour exécuter depuis la racine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

def run_tests():
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DES TESTS DU GRAPHE GLOBAL (SUPERVISEUR)")
    print("="*60 + "\n")
    
    tests = [
        {
            "name": "TEST 1: Requête orientée Action (Ticket CRM)",
            "query": "Le transformateur du four LF présente une surchauffe anormale. Crée un ticket CRM urgent immédiatement."
        },
        {
            "name": "TEST 2: Requête orientée Data (SQL / KPI)",
            "query": "Quel a été le taux de disponibilité du four EAF hier ?"
        }
    ]
    
    for test in tests:
        print(f"\n▶️ {test['name']}")
        print(f"🧑‍🏭 User : {test['query']}")
        print("-" * 60)
        
        # Exécution du graphe
        result = run_agent(test['query'], session_id="test_suite")
        
        print("\n📊 RÉSULTAT DU ROUTAGE :")
        print(f"   - Tâche identifiée : {result.get('task_type')}")
        print(f"   - Plan établi : {result.get('plan')}")
        
        if result.get("task_type") == "action":
            print(f"   - Réponse Finale (Action) : {result.get('final_response')}")
        else:
            print(f"   - État (Action ignorée pour ce test, voir logs)")
            
        print("="*60)

if __name__ == "__main__":
    run_tests()