"""Test SQL Agent Acierie."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sql_agent import SQLAgent
from agents.state import AgentState

agent = SQLAgent()

def test_query(question):
    print(f"\n{'='*55}")
    print(f"Question : {question}")
    print('='*55)
    state = AgentState(
        query=question, plan=[], task_type="sql",
        retrieved_context="", tool_results=[],
        action_history=[], final_response="",
        metadata={}, iteration_count=0, errors=[]
    )
    result = agent.execute(state)
    print(result["retrieved_context"])

test_query("Quel est le taux de disponibilite EAF ?")
test_query("Quelle est la consommation electrique totale ?")
test_query("Combien de coulees ont ete produites ?")
test_query("Quels sont les defauts les plus frequents sur les brames ?")