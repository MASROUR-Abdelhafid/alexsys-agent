"""
Script d'Évaluation et Benchmark MLOps.
Évalue l'Agent IA sur un set de questions et trace les résultats dans MLflow.
"""

import os
import sys
import time
import mlflow
import structlog
from dotenv import load_dotenv

# Ajout du path global pour l'importation des modules (remonter d'un cran)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

logger = structlog.get_logger(__name__)

def run_evaluation():
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DE L'ÉVALUATION EXPÉRIMENTALE (MLFLOW)")
    print("="*60 + "\n")

    load_dotenv()
    
    # 1. Configuration MLflow
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(mlflow_uri)
    
    # Création ou sélection de l'expérience
    experiment_name = "Alexsys_Agent_Evaluation"
    mlflow.set_experiment(experiment_name)
    
    # 2. Dataset d'évaluation (Couvre tous les cas du Superviseur)
    test_cases = [
        {
            "id": "q1_rag",
            "query": "D'après les manuels, à quoi sert exactement le four LF (Four de poche) ?",
            "expected_type": "rag"
        },
        {
            "id": "q2_sql",
            "query": "Quel a été le taux de disponibilité du four EAF hier ?",
            "expected_type": "sql"
        },
        {
            "id": "q3_action",
            "query": "Le transformateur du four LF est en surchauffe. Crée un ticket CRM urgent.",
            "expected_type": "action"
        },
        {
            "id": "q4_direct",
            "query": "Bonjour, je suis le superviseur de l'usine, comment vas-tu ?",
            "expected_type": "direct"
        }
    ]

    print(f"🔗 Connexion à MLflow sur : {mlflow_uri}")
    print(f"📦 Exécution de {len(test_cases)} requêtes d'évaluation...\n")

    for i, test in enumerate(test_cases, 1):
        print(f"▶️ Évaluation {i}/{len(test_cases)} : [{test['expected_type'].upper()}]")
        print(f"   Question : {test['query']}")
        
        with mlflow.start_run(run_name=f"eval_{test['id']}"):
            start_time = time.time()
            try:
                result = run_agent(test['query'], session_id=f"eval_{test['id']}")
                latency = time.time() - start_time
                actual_type = result.get('task_type', 'unknown')
                
                mlflow.log_param("query", test['query'])
                mlflow.log_param("expected_task_type", test['expected_type'])
                mlflow.log_param("actual_task_type", actual_type)
                mlflow.log_param("routing_success", actual_type == test['expected_type'])
                mlflow.log_metric("latency_seconds", latency)
                
                response = result.get('final_response', '')
                mlflow.log_text(response, "final_response.txt")
                
                print(f"   ✓ Succès ({latency:.2f}s) - Type détecté : {actual_type}\n")
            except Exception as e:
                latency = time.time() - start_time
                mlflow.log_param("error", str(e))
                mlflow.log_metric("latency_seconds", latency)
                print(f"   ❌ Échec ({latency:.2f}s) : {str(e)}\n")

    print("="*60)
    print("✅ ÉVALUATION TERMINÉE AVEC SUCCÈS.")
    print("📊 Ouvre ton navigateur sur http://localhost:5000 pour analyser les résultats.")
    print("="*60)

if __name__ == "__main__":
    run_evaluation()