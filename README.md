# Tablero de Incidencia · Prevalencia · Carga · Proyección — Cáncer SSMO

Tablero interactivo que consolida los análisis del EPH del Centro Oncológico:

- **🔬 Incidencia (multi-fuente):** por cáncer, todas las estimaciones — GLOBOCAN crudo/directo (INE y
  beneficiaria), CECAN, comité, egresos y defunciones — incluyendo **pulmón y vejiga (fuera de la cartera)**.
- **⏳ Prevalencia:** CECAN vs estimación por supervivencia vs acumulado del comité.
- **⚖️ Carga (AVISA/DALYs):** DALYs por cáncer descompuestos en **YLL (mortalidad prematura)** y **YLD
  (discapacidad)**, y contraste **prevalencia vs carga** (mama = supervivencia; pulmón = letalidad).
- **📈 Proyección:** demanda a 2050 (Modelo A INE/beneficiaria, Markov, captado), cartera vs fuera de cartera,
  y escenarios de migración ISAPRE→FONASA.

Filtros: **denominador** (INE / beneficiaria), **ámbito** (cartera / fuera / todos) y **cánceres**.

## Datos

Parquets en `datos/`, consolidados por `preparar_datos_tablero.py` desde las salidas de los EDA:
`INCIDENCIA_PREVALENCIA_SSMO.xlsx`, `CECAN_SSMO_INCIDENCIA.xlsx`, `PROYECCION_DEMANDA_ONCOLOGICA_SSMO.xlsx`.
Regenerar: `python preparar_datos_tablero.py`.

## Ejecutar

```bash
pip install -r requirements.txt
streamlit run tablero_incidencia_carga.py
```

## Desplegar (Streamlit Community Cloud)

Los datos son **agregados** (por cáncer, sin identificadores). Subir el repo a GitHub y en
<https://share.streamlit.io> → New app → `tablero_incidencia_carga.py`. Clave opcional: `app_password` en Secrets.

## Nota metodológica

Ninguna fuente mide la incidencia real por sí sola: **triangular y reportar el rango**. El **CECAN** es un modelo
local (tasas de la Provincia de Santiago aplicadas al SSMO) que suele estimar más alto que GLOBOCAN y lo observado
→ no tomarlo como verdad. Cifras 2023+ preliminares.
