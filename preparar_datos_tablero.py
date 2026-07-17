# -*- coding: utf-8 -*-
"""Prepara los datos del Tablero de Incidencia · Prevalencia · Carga · Proyección.

Consolida en `datos/` (parquets livianos) las salidas ya calculadas por los EDA:
  - INCIDENCIA_PREVALENCIA_SSMO.xlsx  (hojas comparacion_fuentes, prevalencia)
  - CECAN_SSMO_INCIDENCIA.xlsx        (hojas carga_2025, incidencia_serie)
  - PROYECCION_DEMANDA_ONCOLOGICA_SSMO.xlsx (modelo A/B, escenarios, migración)

Ejecutar:  python preparar_datos_tablero.py
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[3]                 # ...\ANALISIS Y BBDD
CO = BASE / "DATOS" / "DATOS_CANCER" / "COMITE_ONCOLOGICO"
CEC = BASE / "DATOS" / "DATOS_CANCER" / "CECAN_INCIDENCIA"
OUT = Path(__file__).resolve().parent / "datos"; OUT.mkdir(exist_ok=True)

INC = CO / "INCIDENCIA_PREVALENCIA_SSMO.xlsx"
PROY = CO / "PROYECCION_DEMANDA_ONCOLOGICA_SSMO.xlsx"
CECX = CEC / "CECAN_SSMO_INCIDENCIA.xlsx"


def _melt_cancer(sheet, valor):
    d = pd.read_excel(PROY, sheet_name=sheet).rename(columns={"Unnamed: 0": "Cáncer"})
    d = d.melt(id_vars="Cáncer", var_name="Año", value_name=valor)
    d["Año"] = pd.to_numeric(d["Año"], errors="coerce").astype("Int64")
    return d.dropna(subset=["Año"])


def main():
    # --- Incidencia multi-fuente + prevalencia (EDA incidencia) ---
    fuentes = pd.read_excel(INC, sheet_name="comparacion_fuentes")
    fuentes.to_parquet(OUT / "fuentes.parquet", index=False)
    prev = pd.read_excel(INC, sheet_name="prevalencia")
    prev.to_parquet(OUT / "prevalencia.parquet", index=False)

    # --- CECAN carga + serie ---
    pd.read_excel(CECX, sheet_name="carga_2025").to_parquet(OUT / "carga.parquet", index=False)
    pd.read_excel(CECX, sheet_name="incidencia_serie").to_parquet(OUT / "serie_cecan.parquet", index=False)

    # --- Proyección ---
    ine = _melt_cancer("modeloA_INE_por_cancer", "INE"); ben = _melt_cancer("modeloA_benef_por_cancer", "Beneficiaria")
    proy = ine.merge(ben, on=["Cáncer", "Año"], how="outer")
    # marca cartera (pulmón fuera)
    proy["Ámbito"] = proy["Cáncer"].map(lambda c: "Fuera de cartera" if str(c).strip() == "Pulmón" else "Cartera")
    proy.to_parquet(OUT / "proyeccion_cancer.parquet", index=False)
    for sheet, fn in [("total_por_hito_modelo", "proy_total"), ("escenarios_markov_captado", "proy_escenarios"),
                      ("demanda_x_migracion_isapre", "proy_migracion")]:
        d = pd.read_excel(PROY, sheet_name=sheet).rename(columns={"Unnamed: 0": "cat"})
        d.to_parquet(OUT / f"{fn}.parquet", index=False)

    print("Parquets ->", OUT)
    for p in sorted(OUT.glob("*.parquet")):
        print(f"  {p.name:26s} {pd.read_parquet(p).shape}")


if __name__ == "__main__":
    main()
