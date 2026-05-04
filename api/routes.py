"""Routes FastAPI Aciérie — avec sécurité token."""
import time
import os
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from api.schemas import QueryRequest, QueryResponse, HealthResponse
from agents.graph import run_agent
from config import config
import structlog
from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File

logger = structlog.get_logger(__name__)
router = APIRouter()



ROLES = {
    "maghreb_admin_2025":    "admin",
    "maghreb_steel_2025":    "operateur",
    "maghreb_readonly_2025": "lecteur",
}

def get_role(authorization: Optional[str] = Header(None)) -> str:
    """Retourne le rôle selon le token."""
    if config.APP_ENV == "development":
        return "admin"
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.replace("Bearer ", "").strip()
    role = ROLES.get(token)
    if not role:
        raise HTTPException(status_code=403, detail="Token invalide")
    return role


def require_operateur(role: str = Depends(get_role)):
    if role not in ["admin", "operateur"]:
        raise HTTPException(status_code=403, detail="Rôle insuffisant — opérateur requis")
    return role


def require_admin(role: str = Depends(get_role)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Rôle insuffisant — admin requis")
    return role


@router.post("/chat", response_model=QueryResponse)
async def chat(
    request: QueryRequest,
    role: str = Depends(get_role),
):
    """Point d'entrée principal du chatbot aciérie."""
    t_start = time.time()
    try:
        result = run_agent(
            query=request.question,
            session_id=request.session_id,
        )
        latency = round((time.time() - t_start) * 1000, 2)
        # Log audit
        logger.info(
            "AUDIT",
            action="chat",
            query=request.question[:80],
            task_type=result.get("task_type"),
            session=request.session_id,
            role=role,
            latency_ms=latency,
        )
        return QueryResponse(
            question=request.question,
            answer=result.get("final_response", ""),
            session_id=request.session_id,
            task_type=result.get("task_type", ""),
            plan=result.get("plan", []),
            metadata={
                **result.get("metadata", {}),
                "total_latency_ms": latency,
                "actions": len(result.get("action_history", [])),
                "user_role": role,
            },
            errors=result.get("errors", []),
        )
    except Exception as e:
        logger.error("Erreur API /chat", error=str(e), role=role)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        components={
            "api": "up",
            "database": "up",
            "kpi_engine": "up",
            "llm": "groq/llama-3.1-8b",
            "rag": "milvus/hnsw",
            "security": "token-based",
        }
    )


@router.get("/kpis")
async def get_kpis(role: str = Depends(get_role)):
    """Liste des KPIs Gold disponibles."""
    from kpi.definitions import KPI_DEFINITIONS
    
    logger.info("GET /kpis", role=role)
    
    return {
        "kpis": [
            {
                "key": k,
                "nom": v["nom"],
                "unite": v["unite"],
                "description": v["description"],
                "statut": "Gold",
            }
            for k, v in KPI_DEFINITIONS.items()
        ],
        "total": len(KPI_DEFINITIONS),
        "source": "Aciérie Maghreb Steel — Base officielle",
        "accessed_by": role,
    }


@router.get("/dashboard")
async def get_dashboard_data(role: str = Depends(get_role)):
    """Données complètes pour le dashboard."""
    from kpi.engine import KPIEngine
    
    logger.info("GET /dashboard", role=role)
    
    engine = KPIEngine()
    try:
        td      = engine.get_taux_disponibilite()
        conso   = engine.get_consommation_electrique(groupby="mois")
        prod    = engine.get_production_coulees(groupby="mois")
        defauts = engine.get_defauts_brames(limit=8)
        arrets  = engine.get_arrets_by_type(limit=6)
        oxy     = engine.get_consommation_oxygene()
        brames  = engine.get_poids_brames()
        
        return {
            "taux_disponibilite":     td,
            "consommation_electrique": conso,
            "production_coulees":     prod,
            "defauts_brames":         defauts,
            "arrets_by_type":         arrets,
            "oxygene":                oxy,
            "brames":                 brames,
            "status":                 "ok",
            "source":                 "Gold — Données officielles Aciérie",
            "accessed_by":            role,
        }
    except Exception as e:
        logger.error("Erreur dashboard", error=str(e), role=role)
        return {"status": "error", "message": str(e)}
    

@router.get("/export/kpis")
async def export_kpis_csv(role: str = Depends(get_role)):
    """Export CSV des KPIs Gold pour outils BI externes."""
    import csv, io
    from fastapi.responses import StreamingResponse
    from kpi.engine import KPIEngine

    engine = KPIEngine()
    td     = engine.get_taux_disponibilite()
    conso  = engine.get_consommation_electrique(groupby="mois")
    prod   = engine.get_production_coulees(groupby="mois")
    oxy    = engine.get_consommation_oxygene()
    brames = engine.get_poids_brames()
    defauts = engine.get_defauts_brames(limit=5)

    # UTF-8 BOM pour compatibilité Excel Windows
    output = io.StringIO()
    output.write('\ufeff')  # BOM UTF-8
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["KPI", "Valeur", "Unité", "Détail", "Source", "Statut"])
    writer.writerow([
        "Taux Disponibilité EAF",
        td.get("valeur", 0),
        "%",
        f"Nb jours: {td.get('details', {}).get('nb_jours', 0)}",
        "Gold", "Officiel"
    ])
    writer.writerow([
        "Consommation Électrique Totale",
        conso.get("total_mwh", 0),
        "MWh",
        f"EAF + LF combinés",
        "Gold", "Officiel"
    ])
    writer.writerow([
        "Production Coulées",
        prod.get("total_coulees", 0),
        "coulées",
        f"Période complète",
        "Gold", "Officiel"
    ])
    writer.writerow([
        "Consommation Oxygène EAF",
        oxy.get("valeur", 0),
        "Nm³",
        f"Moy/coulée: {oxy.get('details', {}).get('moyenne_par_coulee_nm3', 0)} Nm³",
        "Gold", "Officiel"
    ])
    writer.writerow([
        "Poids Moyen Brames",
        brames.get("valeur", 0),
        "kg",
        f"Total: {brames.get('details', {}).get('poids_total_tonnes', 0)} t",
        "Gold", "Officiel"
    ])
    writer.writerow([
        "Défauts Brames Total",
        defauts.get("total_defauts", 0),
        "défauts",
        f"Types détectés: {len(defauts.get('data', []))}",
        "Gold", "Officiel"
    ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=kpis_maghreb_steel.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


@router.post("/feedback")
async def feedback(
    request: dict,
    role: str = Depends(get_role),
):
    """Enregistre le feedback utilisateur pour amélioration continue."""
    import json
    from datetime import datetime
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": request.get("session_id", ""),
        "question": request.get("question", ""),
        "answer": request.get("answer", "")[:200],
        "rating": request.get("rating", ""),  # "positive" ou "negative"
        "comment": request.get("comment", ""),
        "task_type": request.get("task_type", ""),
    }
    with open("logs/feedback.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info("Feedback enregistré", rating=entry["rating"], task_type=entry["task_type"])
    return {"status": "ok", "message": "Feedback enregistré"}


@router.post("/index-document")
async def index_document(
    file: bytes = None,
    role: str = Depends(get_role),
):
    """Indexe un nouveau document PDF ou TXT dans Milvus."""
    from fastapi import UploadFile, File
    return {"status": "use /index-document-upload"}


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    role: str = Depends(get_role),
):
    import tempfile, os
    from rag.ingestion import DocumentIngestionPipeline, IngestionConfig
    from rag.vector_store import MilvusVectorStore

    filename = file.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ["pdf", "txt"]:
        raise HTTPException(status_code=400, detail=f"Format '{ext}' non supporté. PDF ou TXT uniquement.")

    os.makedirs("data/acierie", exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}", dir="data/acierie") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        config_ing = IngestionConfig(chunk_size=600, chunk_overlap=80)
        pipeline = DocumentIngestionPipeline(config_ing)
        chunks = pipeline.ingest(tmp_path)

        try:
            store = MilvusVectorStore()
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="⚠️ Milvus indisponible — lancez Docker : cd docker && docker-compose up -d"
            )

        inserted = store.insert_chunks(chunks)
        logger.info("Document indexé", filename=filename, chunks=inserted, role=role)
        return {"status": "ok", "filename": filename, "chunks_indexed": inserted,
                "message": f"✅ {inserted} chunks indexés depuis '{filename}'"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/admin/stats")
async def admin_stats(role: str = Depends(require_admin)):
    """Statistiques d'utilisation — admin uniquement."""
    import json
    from collections import Counter
    stats = {"total_requetes": 0, "par_type": {}, "latence_moy": 0, "feedback": {}}
    # Audit log
    if os.path.exists("logs/audit.log"):
        with open("logs/audit.log", encoding="utf-8") as f:
            entries = [json.loads(l) for l in f if l.strip()]
        stats["total_requetes"] = len(entries)
        types = Counter(e.get("task_type", "") for e in entries)
        stats["par_type"] = dict(types)
        latencies = [e.get("latency_ms", 0) for e in entries if e.get("latency_ms")]
        stats["latence_moy"] = round(sum(latencies) / len(latencies), 0) if latencies else 0
    # Feedback log
    if os.path.exists("logs/feedback.log"):
        with open("logs/feedback.log", encoding="utf-8") as f:
            feedbacks = [json.loads(l) for l in f if l.strip()]
        ratings = Counter(f.get("rating", "") for f in feedbacks)
        stats["feedback"] = dict(ratings)
        stats["total_feedbacks"] = len(feedbacks)
    return stats