"""
Agent d'Action (Tool Executor) - Pattern ReAct.
Gère l'exécution autonome des outils industriels (CRM, PDF).
"""

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
import structlog

from agents.llm_factory import get_llm
from agents.state import AgentState
from tools.crm_mock import create_crm_ticket
from tools.pdf_generator import generate_kpi_report

logger = structlog.get_logger(__name__)

# 1. Configuration des outils
tools = [create_crm_ticket, generate_kpi_report]
tool_node = ToolNode(tools)

# 2. Liaison avec le LLM configuré dans ton usine
llm = get_llm()
llm_with_tools = llm.bind_tools(tools)

# 3. Prompt système corrigé et épuré pour compatibilité maximale avec l'API Groq/Llama3
SYSTEM_PROMPT = """Tu es un Agent IA Autonome industriel spécialisé dans l'aciérie.
Tu as accès à des outils métiers. Tu dois analyser la demande de l'utilisateur et décider si l'usage d'un outil est pertinent.
- Pour remonter une alerte ou un incident, appelle l'outil create_crm_ticket.
- Pour formater des données KPI sous forme de document, appelle l'outil generate_kpi_report.
Si tu n'as pas besoin d'outil, réponds simplement à l'utilisateur de manière concise."""

def action_agent_node(state: AgentState):
    """Nœud principal de l'agent qui invoque le LLM."""
    messages = state.get("messages", [])
    
    # Injection du prompt système s'il n'est pas déjà présent
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    logger.info("Action Agent Invoqué", nb_messages=len(messages))
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def build_action_graph():
    """Construit le graphe orienté cyclique (Isolé pour les tests de la Phase 2)."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", action_agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.add_edge(START, "agent")
    
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", "__end__": END}
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

# Instance exportée pour les tests
action_app = build_action_graph()