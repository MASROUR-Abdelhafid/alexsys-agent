import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

def run_test():
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU TEST : AGENT RAG (DOCUMENTATION)")
    print("="*60 + "\n")
    
    query = "D'après les manuels, à quoi sert exactement le four LF (Four de poche) et quelle est sa puissance ?"
    
    print(f"🧑‍🏭 User : {query}")
    print("-" * 60)
    
    result = run_agent(query, session_id="test_rag")
    
    print("\n📊 RÉSULTAT DE L'ORCHESTRATION :")
    print(f"   - Tâche identifiée par le Planner : {result.get('task_type')}")
    print(f"   - Contexte récupéré par le Retriever : {result.get('retrieved_context')[:150]}...")
    print(f"\n📝 RÉPONSE FINALE DU GÉNÉRATEUR :\n{result.get('final_response')}")
    print("="*60)

if __name__ == "__main__":
    run_test()