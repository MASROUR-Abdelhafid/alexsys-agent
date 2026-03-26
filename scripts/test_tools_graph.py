import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.action_agent import action_app
from langchain_core.messages import HumanMessage

def run_test():
    print("🚀 Démarrage du test de l'Agent Autonome (Tool Executor)...\n")
    
    user_query = "Alerte : Le Taux de Disponibilité du four EAF a chuté à 78% cette semaine. Crée un ticket CRM urgent avec ces informations."
    
    print(f"🧑‍🏭 Utilisateur : {user_query}")
    print("-" * 50)
    
    # Initialisation de l'état avec les clés obligatoires de ton AgentState
    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "query": user_query,
        "plan": [],
        "task_type": "tool_execution",
        "retrieved_context": "",
        "tool_results": [],
        "action_history": [],
        "final_response": "",
        "metadata": {"session_id": "test_tools"},
        "iteration_count": 0,
        "errors": []
    }
    
    for event in action_app.stream(initial_state, stream_mode="updates"):
        for node_name, node_state in event.items():
            print(f"🔄 Nœud actif : [{node_name}]")
            message = node_state["messages"][-1]
            message.pretty_print()
            print("-" * 50)

if __name__ == "__main__":
    run_test()