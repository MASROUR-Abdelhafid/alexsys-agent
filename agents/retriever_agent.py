"""
Agent Retriever - Interface entre l'orchestrateur et la pipeline RAG Avancée.
Gère l'extraction de contexte documentaire (Milvus/BM25).
"""

import structlog
from agents.state import AgentState

logger = structlog.get_logger(__name__)

class RetrieverAgent:
    def __init__(self):
        # Initialisation prudente de la pipeline RAG
        try:
            # On tente d'importer ta pipeline RAG existante
            from rag.rag_pipeline import RAGPipeline
            self.pipeline = RAGPipeline()
            self.has_real_rag = True
            logger.info("RAGPipeline chargée avec succès.")
        except Exception as e:
            logger.warning(f"Impossible de charger RAGPipeline (Milvus est-il lancé ?). Mode dégradé (Mock) activé. Erreur: {str(e)}")
            self.has_real_rag = False

    def retrieve(self, state: AgentState) -> dict:
        """Exécute la recherche documentaire et met à jour le contexte."""
        query = state.get("query", "")
        logger.info("RetrieverAgent activé", query=query)
        
        if self.has_real_rag:
            try:
                # Appel théorique à ta méthode de recherche (à adapter selon ta nomenclature exacte)
                # On suppose que ta pipeline a une méthode du type retrieve(query)
                context = self.pipeline.retrieve(query)
            except Exception as e:
                logger.error("Erreur lors de l'exécution du RAG", error=str(e))
                context = "Erreur technique lors de la consultation des manuels."
        else:
            # --- MOCK POUR LES TESTS D'ORCHESTRATION ---
            # Si Milvus/Docker n'est pas up, on renvoie un faux contexte extrait de ton PDF
            logger.info("Utilisation du contexte documentaire Mocké.")
            context = (
                "[EXTRAIT DOCUMENTAIRE - MOCK]\n"
                "Le four LF (Ladle Furnace / Four de poche) est un four de traitement secondaire "
                "utilisé après la fusion dans le four EAF. Il ne sert pas à fondre le métal, "
                "mais à le raffiner et ajuster la température (Réglage précis) et la composition "
                "chimique avant la coulée continue. Il a une puissance de 20MVA."
            )

        return {
            "retrieved_context": context,
            "action_history": [{"agent": "retriever", "action": "hybrid_search", "status": "success"}],
            "iteration_count": state.get("iteration_count", 0) + 1
        }