"""Test LLM Ollama."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_factory import get_llm
from langchain_core.messages import HumanMessage

print("Chargement LLM...")
llm = get_llm(temperature=0)

print("Test en cours...")
response = llm.invoke([HumanMessage(content="Dis bonjour en français en une phrase courte.")])
print(f"✅ Réponse : {response.content}")