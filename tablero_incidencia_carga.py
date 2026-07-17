# -*- coding: utf-8 -*-
"""Tablero de Incidencia · Prevalencia · Carga · Proyección del cáncer en el SSMO.

Consolida los EDA de incidencia/prevalencia (triangulación GLOBOCAN · comité · egresos ·
CECAN, incl. tumores fuera de cartera), la carga de enfermedad CECAN (AVISA/DALYs, YLL,
YLD) y la proyección de demanda a 2050.

Ejecutar:  streamlit run tablero_incidencia_carga.py
Datos:     parquets en `datos/` (generar con preparar_datos_tablero.py).
"""
import hmac
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Incidencia · Carga · Proyección — SSMO", layout="wide", page_icon="🎗️")

COL_FUENTE = {"GLOBOCAN crudo": "#b0b7be", "GLOBOCAN directo": "#111111", "CECAN": "#8e44ad",
              "GES/SIGES": "#16a085", "Comité": "#c0392b", "Egresos": "#e08a1e", "Defunciones": "#7a7a7a"}
AZUL, ROJO, VERDE = "#2C6E9B", "#c0392b", "#16a085"


def _check_password():
    try:
        pw = str(st.secrets.get("app_password", ""))
    except Exception:
        pw = ""
    if not pw:
        return True
    if st.session_state.get("_ok"):
        return True

    def _e():
        st.session_state["_ok"] = hmac.compare_digest(st.session_state.get("_pw", ""), pw)

    st.text_input("Clave de acceso", type="password", key="_pw", on_change=_e)
    if st.session_state.get("_pw") and not st.session_state.get("_ok"):
        st.error("Clave incorrecta.")
    return st.session_state.get("_ok", False)


if not _check_password():
    st.stop()


@st.cache_data(show_spinner="Cargando…")
def load():
    d = Path(__file__).resolve().parent / "datos"
    return {p.stem: pd.read_parquet(p) for p in d.glob("*.parquet")}


D = load()
fuentes = D["fuentes"]
carga = D["carga"]
prev = D["prevalencia"]
proy_c = D["proyeccion_cancer"]
serie = D["serie_cecan"]

st.title("🎗️ Incidencia · Prevalencia · Carga · Proyección — Cáncer SSMO")
st.caption("Triangulación de fuentes (GLOBOCAN · comité · egresos · CECAN), carga de enfermedad (AVISA/DALYs) y "
           "proyección de demanda. Incluye tumores **fuera de la cartera** (pulmón, vejiga).")

# ---------------------------------------------------------------- Filtros
st.sidebar.header("Filtros")
denom = st.sidebar.radio("Denominador poblacional", ["INE", "Beneficiaria"], index=0,
                         help="INE = población total; Beneficiaria = FONASA (red pública).")
ambito = st.sidebar.radio("Ámbito", ["Todos", "Solo cartera", "Solo fuera de cartera"], index=0)
canceres = list(fuentes["Cáncer"])
if ambito == "Solo cartera":
    canceres = list(fuentes[fuentes["Cartera"] == "sí"]["Cáncer"])
elif ambito == "Solo fuera de cartera":
    canceres = list(fuentes[fuentes["Cartera"] == "FUERA"]["Cáncer"])
sel = st.sidebar.multiselect("Cánceres", list(fuentes["Cáncer"]), default=canceres)
if not sel:
    sel = list(fuentes["Cáncer"])
st.sidebar.caption("Incidencia/prevalencia/carga: CECAN (modelo local, Prov. Santiago → SSMO) + GLOBOCAN + "
                   "observado. Proyección a 2050 (GLOBOCAN × población). Cifras preliminares — citar como rango.")

_sfx = "INE" if denom == "INE" else "Ben"
tabs = st.tabs(["🔬 Incidencia (multi-fuente)", "⏳ Prevalencia", "⚖️ Carga (AVISA/DALYs)", "📈 Proyección"])

# ---------------------------------------------------------------- Tab 1: incidencia
with tabs[0]:
    f = fuentes[fuentes["Cáncer"].isin(sel)].copy()
    fila = []
    for _, r in f.iterrows():
        fila += [
            {"Cáncer": r["Cáncer"], "Fuente": "GLOBOCAN crudo", "Casos/año": r[f"GLOB crudo·{_sfx}"]},
            {"Cáncer": r["Cáncer"], "Fuente": "GLOBOCAN directo", "Casos/año": r[f"GLOB dir·{_sfx}"]},
            {"Cáncer": r["Cáncer"], "Fuente": "CECAN", "Casos/año": r[f"CECAN·{_sfx}"]},
            {"Cáncer": r["Cáncer"], "Fuente": "Comité", "Casos/año": r["Comité obs."]},
            {"Cáncer": r["Cáncer"], "Fuente": "Egresos", "Casos/año": r["Egresos obs."]},
            {"Cáncer": r["Cáncer"], "Fuente": "Defunciones", "Casos/año": r["Defunc."]},
        ]
        # GES/SIGES es un registro local FONASA -> solo tiene sentido en denominador beneficiaria
        if _sfx == "Ben" and "GES/SIGES·Ben" in f.columns and pd.notna(r.get("GES/SIGES·Ben")):
            fila.append({"Cáncer": r["Cáncer"], "Fuente": "GES/SIGES", "Casos/año": r["GES/SIGES·Ben"]})
    lf = pd.DataFrame(fila).dropna(subset=["Casos/año"])
    orden = f.sort_values(f"CECAN·{_sfx}", ascending=False)["Cáncer"].tolist()
    fig = px.bar(lf, x="Cáncer", y="Casos/año", color="Fuente", barmode="group",
                 color_discrete_map=COL_FUENTE, category_orders={"Cáncer": orden, "Fuente": list(COL_FUENTE)},
                 title=f"Incidencia anual por cáncer y fuente (denominador {denom})")
    fig.update_layout(height=520, legend=dict(orientation="h", y=1.08), margin=dict(t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.info("Las estimaciones **modeladas** (GLOBOCAN, CECAN) y las **observadas** (comité, egresos, "
            "defunciones, **GES/SIGES**) miden cosas distintas. **CECAN** (modelo local) suele salir alto; "
            "**GES/SIGES** (registro local FONASA; solo con denominador *beneficiaria*) valida a mama "
            "(≈ CECAN) pero en **cérvix incluye lesiones preinvasoras** (no cáncer invasor) y en gástrico "
            "parece subcaptar; **comité** solo capta lo que pasa por él (los **fuera de cartera** — pulmón, "
            "vejiga — no tienen barra de comité); **egresos** son hospitalizaciones (sobrecuentan). Reportar "
            "el **rango entre fuentes**, no un valor único.")
    st.dataframe(f.set_index("Cáncer"), use_container_width=True)

# ---------------------------------------------------------------- Tab 2: prevalencia
with tabs[1]:
    cg = carga[carga["Cáncer"].isin(sel)][["Cáncer", f"Prevalencia · {_sfx}"]].rename(
        columns={f"Prevalencia · {_sfx}": "CECAN (personas)"})
    pv = prev.rename(columns={"Prevalencia 5a estimada": "Estimada 5a (superv.)",
                              "Pac. únicos acum. comité": "Acum. comité (observado)"})
    m = cg.merge(pv[["Cáncer", "Estimada 5a (superv.)", "Acum. comité (observado)"]], on="Cáncer", how="left")
    lm = m.melt(id_vars="Cáncer", var_name="Fuente", value_name="Personas").dropna(subset=["Personas"])
    ordp = cg.sort_values("CECAN (personas)", ascending=False)["Cáncer"].tolist()
    figp = px.bar(lm, x="Cáncer", y="Personas", color="Fuente", barmode="group",
                  category_orders={"Cáncer": ordp}, title=f"Prevalencia (personas viviendo con el cáncer) — {denom}",
                  color_discrete_map={"CECAN (personas)": "#8e44ad", "Estimada 5a (superv.)": AZUL,
                                      "Acum. comité (observado)": VERDE})
    figp.update_layout(height=500, legend=dict(orientation="h", y=1.08), margin=dict(t=60, b=10))
    st.plotly_chart(figp, use_container_width=True)
    st.caption("La prevalencia la manda la **supervivencia**: mama y próstata dominan (alta supervivencia → "
               "seguimiento crónico), pese a no ser los más letales. CECAN modela la prevalencia; la 'estimada 5a' "
               "es incidencia×5×supervivencia; 'acum. comité' es el piso observado (pac. únicos acumulados).")

# ---------------------------------------------------------------- Tab 3: carga
with tabs[2]:
    c = carga[carga["Cáncer"].isin(sel)].copy()
    yll, yld_, dal, prv = f"AVPM/YLL · {_sfx}", f"AVD/YLD · {_sfx}", f"AVISA/DALYs · {_sfx}", f"Prevalencia · {_sfx}"
    c = c.sort_values(dal, ascending=False)
    fig1 = go.Figure()
    fig1.add_bar(y=c["Cáncer"], x=c[yll], name="AVPM / YLL (muerte prematura)", orientation="h", marker_color=ROJO)
    fig1.add_bar(y=c["Cáncer"], x=c[yld_], name="AVD / YLD (discapacidad)", orientation="h", marker_color=AZUL)
    fig1.update_layout(barmode="stack", height=460, title=f"Carga por cáncer — AVISA/DALYs = YLL + YLD ({denom})",
                       yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=1.1), margin=dict(t=60, l=10))
    c1, c2 = st.columns([1.15, 1])
    c1.plotly_chart(fig1, use_container_width=True)
    fig2 = px.scatter(c, x=prv, y=dal, text="Cáncer", size=c[dal], color="En cartera",
                      color_discrete_map={True: VERDE, False: ROJO},
                      labels={prv: "Prevalencia (personas)", dal: "AVISA/DALYs (años)"},
                      title="Prevalencia vs carga: supervivencia (mama) vs letalidad (pulmón)")
    fig2.update_traces(textposition="top center", textfont_size=9)
    fig2.update_layout(height=460, margin=dict(t=60, b=10), legend_title="En cartera")
    c2.plotly_chart(fig2, use_container_width=True)
    c["% carga por muerte prematura"] = (c[yll] / c[dal] * 100).round(0).astype(int)
    st.caption("**El pulmón encabeza los DALYs** (casi todo por mortalidad prematura/YLL) pese a estar **fuera de "
               "la cartera**. La mama domina la prevalencia (supervivencia) pero aporta menos DALYs. Para priorizar "
               "por pérdida de salud, mirar los **DALYs**, no solo la incidencia.")
    st.dataframe(c.set_index("Cáncer")[[dal, yll, yld_, prv, "% carga por muerte prematura"]],
                 use_container_width=True)

# ---------------------------------------------------------------- Tab 4: proyección
with tabs[3]:
    tot = D["proy_total"].rename(columns={"cat": "Año"})
    figt = go.Figure()
    for col, cl in [("Modelo A · INE total", "#111"), ("Modelo A · Beneficiaria", AZUL),
                    ("Modelo B · Markov (INE)", VERDE), ("Markov captado P50", "#e08a1e")]:
        if col in tot.columns:
            figt.add_scatter(x=tot["Año"], y=tot[col], mode="lines+markers", name=col, line=dict(width=3))
    figt.update_layout(height=380, title="Demanda oncológica total proyectada — SSMO (casos/año)",
                       legend=dict(orientation="h", y=1.12), margin=dict(t=60, b=10))
    st.plotly_chart(figt, use_container_width=True)

    cc1, cc2 = st.columns(2)
    # cartera vs fuera por hito
    pc = proy_c.copy()
    g = pc.groupby(["Año", "Ámbito"])[denom if denom == "INE" else "Beneficiaria"].sum().reset_index()
    g.columns = ["Año", "Ámbito", "Casos"]
    figca = px.bar(g, x="Año", y="Casos", color="Ámbito", barmode="stack",
                   color_discrete_map={"Cartera": VERDE, "Fuera de cartera": ROJO},
                   title=f"Cartera vs fuera de cartera por hito ({denom})")
    figca.update_layout(height=380, margin=dict(t=60, b=10), legend=dict(orientation="h", y=1.12))
    cc1.plotly_chart(figca, use_container_width=True)
    # escenarios de migración
    mig = D["proy_migracion"].rename(columns={"cat": "Escenario"}).melt(id_vars="Escenario", var_name="Año", value_name="Casos")
    mig["Año"] = pd.to_numeric(mig["Año"], errors="coerce")
    figm = px.line(mig.dropna(subset=["Año"]), x="Año", y="Casos", color="Escenario", markers=True,
                   title="Demanda pública según migración ISAPRE→FONASA")
    figm.update_layout(height=380, margin=dict(t=60, b=10), legend=dict(orientation="h", y=1.12))
    cc2.plotly_chart(figm, use_container_width=True)

    # por cáncer
    val = "INE" if denom == "INE" else "Beneficiaria"
    dpc = proy_c[proy_c["Año"].isin([2025, 2050])].pivot_table(index="Cáncer", columns="Año", values=val)
    dpc = dpc.sort_values(2050, ascending=False)
    st.markdown("**Casos/año proyectados por cáncer** (2025 → 2050, denominador " + denom + "):")
    st.dataframe(dpc.astype("Int64"), use_container_width=True)
    st.caption("La demanda crece ~+77% a 2050 por envejecimiento aunque la población haga peak ~2035. La migración "
               "ISAPRE→FONASA puede sumar hasta ~40% a la demanda pública. **Pulmón** (fuera de cartera) se proyecta "
               "vía GLOBOCAN, que lo subestima frente a CECAN (regla: reportar rango).")

st.caption("Fuentes: EDA de incidencia/prevalencia y proyección (SSMO) + CECAN. Cifras 2023+ preliminares; "
           "CECAN = modelo local (Prov. de Santiago → SSMO), suele estimar alto → usar como rango, no valor único.")
