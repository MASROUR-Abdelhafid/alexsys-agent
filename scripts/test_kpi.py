"""Test KPIs Aciérie."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kpi.engine import KPIEngine

engine = KPIEngine()
print("=== TEST KPIs ACIERIE ===\n")

# TD%
td = engine.get_taux_disponibilite()
print(f"TD%        = {td['valeur']}%")
print(f"Details    = {td['details']}\n")

# Conso Elec
ce = engine.get_consommation_electrique()
print(f"Conso Elec = {ce['valeur_totale_mwh']} MWh\n")

# Production
prod = engine.get_production_coulees()
print(f"Production = {prod['total_coulees']} coulées\n")

# Défauts
def_b = engine.get_defauts_brames(limit=3)
print(f"Défauts    = {def_b['total_defauts']} total")
print(f"Top 3      : {def_b['data'][:3]}\n")

# Arrêts
arrets = engine.get_arrets_by_type(limit=5)
print(f"Arrêts Top 5 :")
for a in arrets['data']:
    print(f"   {a}\n")

print("✅ Tous les KPIs OK !")