"""
Script d'initialisation de la base de données aciérie.
Importe les fichiers Excel vers SQLite.
"""

import sqlite3
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "data/acierie.db"
EXCEL_MAIN = "data/acierie/DATA-ACIERIE.xlsx"
EXCEL_MAJ = "data/acierie/MAJ_DATA-MAI2025.xlsx"

# Mapping nom feuille Excel → nom table SQLite
TABLE_MAPPING = {
    "CCM-Analyse":    "CCM_Analyse",
    "01-PAF":         "PAF",
    "Défauts_Brame":  "Defauts_Brame",
    "EAF_Arrêts":     "EAF_Arrets",
    "05-CCM-Brame":   "CCM_Brame",
    "04-CCM-Coulée":  "CCM_Coulee",
    "02-EAF":         "EAF",
    "03-LF":          "LF",
}


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les noms de colonnes pour SQLite."""
    df.columns = (
        df.columns.str.strip()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace("(", "")
        .str.replace(")", "")
        .str.replace("%", "PCT")
        .str.replace("/", "_")
        .str.replace(".", "_")
    )
    return df


def import_excel_to_sqlite(excel_path: str, conn: sqlite3.Connection, label: str):
    """Importe toutes les feuilles d'un fichier Excel dans SQLite."""
    print(f"\n📂 Lecture de : {excel_path}")
    xl = pd.ExcelFile(excel_path)

    for sheet_name in xl.sheet_names:
        table_name = TABLE_MAPPING.get(sheet_name, sheet_name.replace("-", "_").replace(" ", "_"))

        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)

            if df.empty:
                print(f"   ⚠️  Feuille vide ignorée : {sheet_name}")
                continue

            df = clean_column_names(df)

            # Convertir dates en string pour SQLite
            for col in df.select_dtypes(include=["datetime64"]).columns:
                df[col] = df[col].astype(str)

            # Si table existe déjà (MAJ), append
            if_exists = "append" if label == "MAJ" else "replace"

            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            print(f"   ✅ {sheet_name} → {table_name} ({len(df)} lignes)")

        except Exception as e:
            print(f"   ❌ Erreur sur {sheet_name} : {e}")


def verify_database(conn: sqlite3.Connection):
    """Vérifie le contenu de la base de données."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    print(f"\n{'='*55}")
    print(f"📊 BASE DE DONNÉES ACIÉRIE — RÉSUMÉ")
    print(f"{'='*55}")

    total_rows = 0
    for (table,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = cursor.fetchone()[0]
        total_rows += count
        print(f"   {table:<30} : {count:>8} lignes")

    print(f"{'─'*55}")
    print(f"   {'TOTAL':<30} : {total_rows:>8} lignes")
    print(f"   Tables                         : {len(tables):>8}")
    print(f"{'='*55}")


def main():
    print("=" * 55)
    print("🏭 INIT BASE DE DONNÉES — ACIÉRIE")
    print("=" * 55)

    os.makedirs("data", exist_ok=True)

    # Supprimer ancienne DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"🗑️  Ancienne DB supprimée")

    conn = sqlite3.connect(DB_PATH)

    # Importer DATA-ACIERIE.xlsx
    if os.path.exists(EXCEL_MAIN):
        import_excel_to_sqlite(EXCEL_MAIN, conn, "MAIN")
    else:
        print(f"❌ Fichier introuvable : {EXCEL_MAIN}")

    # Importer MAJ_DATA-MAI2025.xlsx
    if os.path.exists(EXCEL_MAJ):
        import_excel_to_sqlite(EXCEL_MAJ, conn, "MAJ")
    else:
        print(f"⚠️  Fichier MAJ introuvable : {EXCEL_MAJ}")

    conn.commit()
    verify_database(conn)
    conn.close()

    print(f"\n✅ Base de données créée : {DB_PATH}")
    print(f"   Taille : {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()