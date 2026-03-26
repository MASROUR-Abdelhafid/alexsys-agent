import os
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from fpdf import FPDF

class PDFInput(BaseModel):
    kpi_name: str = Field(description="Nom exact de l'indicateur KPI analysé (ex: Taux de Disponibilité EAF)")
    kpi_value: str = Field(description="Valeur chiffrée extraite ou calculée")
    analysis: str = Field(description="Analyse textuelle complète générée par l'agent IA")

@tool("generate_kpi_report", args_schema=PDFInput)
def generate_kpi_report(kpi_name: str, kpi_value: str, analysis: str) -> str:
    """Génère un rapport officiel au format PDF contenant les résultats du KPI et l'analyse de l'agent. Retourne le chemin du fichier."""
    output_dir = os.path.join("data", "reports")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = kpi_name.replace(' ', '_').replace('/', '-')
    filename = f"{output_dir}/Rapport_{safe_name}_{timestamp}.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    
    # En-tête industriel
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="RAPPORT D'ANALYSE INDUSTRIELLE - ACIÉRIE", ln=True, align='C')
    pdf.line(10, 25, 200, 25)
    pdf.ln(10)
    
    # Corps du rapport
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"Indicateur Cible : {kpi_name}", ln=True)
    pdf.cell(0, 10, txt=f"Valeur Mesurée : {kpi_value}", ln=True)
    pdf.cell(0, 10, txt=f"Date d'Extraction : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)
    
    # Section Analyse
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Synthèse et Recommandations de l'Agent IA :", ln=True)
    pdf.set_font("Arial", '', 11)
    
    # Gestion de l'encodage pour éviter les erreurs FPDF avec les caractères spéciaux
    safe_analysis = analysis.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=safe_analysis)
    
    # Pied de page
    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, "Document généré de manière autonome par le système Multi-Agent RAG (Projet de fin d'études - Alexsys Solutions)", 0, 0, 'C')
    
    pdf.output(filename)
    
    return f"Le rapport PDF a été généré avec succès à l'emplacement suivant : {filename}"