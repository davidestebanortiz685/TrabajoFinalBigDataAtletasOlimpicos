from pathlib import Path
import json
import sqlite3
import textwrap

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.express as px
from plotly.offline import get_plotlyjs


SOURCE_DIR = Path(r"C:\Users\david\OneDrive\Documentos\BIG DATA")
PDF_PATH = Path(r"C:\Users\david\Downloads\Taller_ETL_BI.pdf")
OUT_DIR = SOURCE_DIR / "entregables_taller_bi"
CSV_DIR = OUT_DIR / "csv_powerbi"
IMG_DIR = OUT_DIR / "imagenes"


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def infer_event_gender(event_name: str) -> str:
    text = str(event_name)
    if "Women's" in text or "Women" in text:
        return "Femenino"
    if "Men's" in text or "Men" in text:
        return "Masculino"
    if "Mixed" in text or "Open" in text:
        return "Mixto/Open"
    return "No especificado"


def md_cell(cells, text):
    cells.append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": textwrap.dedent(text).strip().splitlines(True),
        }
    )


def code_cell(cells, code):
    cells.append(
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": textwrap.dedent(code).strip().splitlines(True),
        }
    )


def write_notebook(path: Path):
    cells = []
    md_cell(
        cells,
        """
        # Taller BI - Juegos Olimpicos

        Notebook del ETL en Python solicitado en el taller. Carga los CSV, limpia datos,
        construye un modelo estrella, crea indicadores, almacena el resultado en SQLite
        y genera visualizaciones con Plotly.
        """,
    )
    code_cell(
        cells,
        f"""
        from pathlib import Path
        import sqlite3
        import pandas as pd
        import plotly.express as px

        SOURCE_DIR = Path(r"{SOURCE_DIR}")
        OUT_DIR = SOURCE_DIR / "entregables_taller_bi"
        CSV_DIR = OUT_DIR / "csv_powerbi"
        OUT_DIR.mkdir(exist_ok=True)
        CSV_DIR.mkdir(exist_ok=True)
        """,
    )
    md_cell(cells, "## 1. Extraccion\n\nSe leen los cinco archivos planos del proyecto.")
    code_cell(
        cells,
        """
        athletes = pd.read_csv(SOURCE_DIR / "Athletes_Games.csv")
        editions = pd.read_csv(SOURCE_DIR / "Edition_Games.csv")
        teams = pd.read_csv(SOURCE_DIR / "equipos_Games.csv")
        events = pd.read_csv(SOURCE_DIR / "Events_Olimpycs.csv")
        fact_src = pd.read_csv(SOURCE_DIR / "JJ.OO.csv")
        {name: df.shape for name, df in {
            "athletes": athletes, "editions": editions, "teams": teams,
            "events": events, "fact": fact_src
        }.items()}
        """,
    )
    md_cell(cells, "## 2. Perfilamiento y calidad")
    code_cell(
        cells,
        """
        for name, df in {"athletes": athletes, "editions": editions, "teams": teams, "events": events, "fact": fact_src}.items():
            print(name, "shape:", df.shape, "duplicados:", df.duplicated().sum(), "nulos:", df.isna().sum().sum())
        print("Competencias distintas:", events[["Competition_id", "Sport", "Event"]].drop_duplicates().shape[0])
        print(fact_src["Medal"].value_counts())
        """,
    )
    md_cell(cells, "## 3. Transformacion\n\nSe construyen dimensiones, tabla de hechos e indicadores.")
    code_cell(
        cells,
        """
        def clean_text_columns(df):
            df = df.copy()
            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].astype(str).str.strip()
            return df

        def infer_event_gender(event_name):
            text = str(event_name)
            if "Women's" in text or "Women" in text:
                return "Femenino"
            if "Men's" in text or "Men" in text:
                return "Masculino"
            if "Mixed" in text or "Open" in text:
                return "Mixto/Open"
            return "No especificado"

        athletes, editions, teams, events, fact_src = [clean_text_columns(df) for df in [athletes, editions, teams, events, fact_src]]

        dim_atleta = athletes.rename(columns={"athlete_id":"atleta_id", "ID":"id_original_atleta", "Year":"anio_registro", "Name":"nombre_atleta", "Sex":"sexo", "Age":"edad", "Height":"altura_cm", "Weight":"peso_kg"})[["atleta_id", "id_original_atleta", "anio_registro", "nombre_atleta", "sexo", "edad", "altura_cm", "peso_kg"]]
        dim_equipo = teams.rename(columns={"team_id":"equipo_id", "Team":"equipo", "NOC":"noc"})[["equipo_id", "equipo", "noc"]]
        dim_edicion = editions.rename(columns={"edition_id":"edicion_id", "Games":"juegos", "Year":"anio", "Season":"temporada", "City":"ciudad"})[["edicion_id", "juegos", "anio", "temporada", "ciudad"]]
        dim_competencia = events[["Competition_id", "Sport", "Event"]].drop_duplicates().rename(columns={"Competition_id":"competencia_id", "Sport":"deporte", "Event":"evento"}).sort_values("competencia_id")
        dim_competencia["genero_evento"] = dim_competencia["evento"].map(infer_event_gender)

        fact_participacion = fact_src.rename(columns={"id_participacion":"participacion_id", "Medal":"medalla", "athlete_id":"atleta_id", "team_id":"equipo_id", "edition_id":"edicion_id", "Competition_id":"competencia_id"})[["participacion_id", "medalla", "atleta_id", "equipo_id", "edicion_id", "competencia_id"]].copy()
        fact_participacion["edad"] = pd.to_numeric(events["Age"], errors="coerce")
        fact_participacion["altura_cm"] = pd.to_numeric(events["Height"], errors="coerce")
        fact_participacion["peso_kg"] = pd.to_numeric(events["Weight"], errors="coerce")
        fact_participacion["obtuvo_medalla"] = (fact_participacion["medalla"] != "No Medal").astype(int)
        fact_participacion["oro"] = (fact_participacion["medalla"] == "Gold").astype(int)
        fact_participacion["plata"] = (fact_participacion["medalla"] == "Silver").astype(int)
        fact_participacion["bronce"] = (fact_participacion["medalla"] == "Bronze").astype(int)
        fact_participacion["puntaje_medalla"] = fact_participacion["medalla"].map({"No Medal":0, "Bronze":1, "Silver":2, "Gold":3}).astype(int)
        fact_participacion.head()
        """,
    )
    md_cell(cells, "## 4. Carga a SQLite y CSV para Power BI")
    code_cell(
        cells,
        """
        tables = {"dim_atleta": dim_atleta, "dim_equipo": dim_equipo, "dim_edicion": dim_edicion, "dim_competencia": dim_competencia, "fact_participacion": fact_participacion}
        for name, df in tables.items():
            df.to_csv(CSV_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

        sqlite_path = OUT_DIR / "olimpicos_bi.sqlite"
        if sqlite_path.exists():
            sqlite_path.unlink()
        with sqlite3.connect(sqlite_path) as conn:
            for name, df in tables.items():
                df.to_sql(name, conn, index=False, if_exists="replace")
        print(sqlite_path)
        """,
    )
    md_cell(cells, "## 5. Indicadores")
    code_cell(
        cells,
        """
        analitica = fact_participacion.merge(dim_equipo, on="equipo_id").merge(dim_edicion, on="edicion_id").merge(dim_competencia, on="competencia_id")
        indicadores = {
            "participaciones": len(fact_participacion),
            "medallas": int(fact_participacion["obtuvo_medalla"].sum()),
            "oro": int(fact_participacion["oro"].sum()),
            "plata": int(fact_participacion["plata"].sum()),
            "bronce": int(fact_participacion["bronce"].sum()),
            "tasa_medalla": fact_participacion["obtuvo_medalla"].mean(),
        }
        indicadores
        """,
    )
    md_cell(cells, "## 6. Visualizaciones con Plotly")
    code_cell(
        cells,
        """
        medallas = analitica[analitica["obtuvo_medalla"] == 1]

        top_noc = medallas.groupby(["noc", "medalla"], as_index=False).size().rename(columns={"size":"conteo"})
        top_noc_names = medallas.groupby("noc").size().sort_values(ascending=False).head(15).index
        px.bar(top_noc[top_noc["noc"].isin(top_noc_names)], x="conteo", y="noc", color="medalla", orientation="h", title="Top NOC por medallas").show()

        trend = medallas.groupby(["anio", "temporada"], as_index=False).size().rename(columns={"size":"medallas"})
        px.line(trend, x="anio", y="medallas", color="temporada", markers=True, title="Medallas por anio").show()

        sports = medallas.groupby(["deporte", "medalla"], as_index=False).size().rename(columns={"size":"conteo"})
        top_sports = medallas.groupby("deporte").size().sort_values(ascending=False).head(12).index
        px.bar(sports[sports["deporte"].isin(top_sports)], x="deporte", y="conteo", color="medalla", title="Medallas por deporte").show()

        sex_year = analitica.merge(dim_atleta[["atleta_id", "sexo"]], on="atleta_id").groupby(["anio", "sexo"], as_index=False).size().rename(columns={"size":"participaciones"})
        px.area(sex_year, x="anio", y="participaciones", color="sexo", title="Participaciones por sexo").show()
        """,
    )
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def write_sql_server(path: Path):
    path.write_text(
        """/*
Taller BI - Modelo estrella Juegos Olimpicos
1. Crear esta estructura en SQL Server.
2. En SSIS, cargar los CSV limpios de csv_powerbi hacia estas tablas.
3. En SSAS, usar fact_participacion como tabla de hechos y dim_* como dimensiones.
*/

CREATE DATABASE OlimpiadasBI;
GO
USE OlimpiadasBI;
GO

CREATE TABLE dbo.dim_atleta (
    atleta_id INT NOT NULL PRIMARY KEY,
    id_original_atleta INT NOT NULL,
    anio_registro INT NOT NULL,
    nombre_atleta NVARCHAR(200) NOT NULL,
    sexo CHAR(1) NOT NULL,
    edad FLOAT NULL,
    altura_cm FLOAT NULL,
    peso_kg FLOAT NULL
);

CREATE TABLE dbo.dim_equipo (
    equipo_id INT NOT NULL PRIMARY KEY,
    equipo NVARCHAR(200) NOT NULL,
    noc NVARCHAR(10) NOT NULL
);

CREATE TABLE dbo.dim_edicion (
    edicion_id INT NOT NULL PRIMARY KEY,
    juegos NVARCHAR(50) NOT NULL,
    anio INT NOT NULL,
    temporada NVARCHAR(20) NOT NULL,
    ciudad NVARCHAR(100) NOT NULL
);

CREATE TABLE dbo.dim_competencia (
    competencia_id INT NOT NULL PRIMARY KEY,
    deporte NVARCHAR(100) NOT NULL,
    evento NVARCHAR(250) NOT NULL,
    genero_evento NVARCHAR(30) NOT NULL
);

CREATE TABLE dbo.fact_participacion (
    participacion_id INT NOT NULL PRIMARY KEY,
    medalla NVARCHAR(20) NOT NULL,
    atleta_id INT NOT NULL,
    equipo_id INT NOT NULL,
    edicion_id INT NOT NULL,
    competencia_id INT NOT NULL,
    edad FLOAT NULL,
    altura_cm FLOAT NULL,
    peso_kg FLOAT NULL,
    obtuvo_medalla BIT NOT NULL,
    oro INT NOT NULL,
    plata INT NOT NULL,
    bronce INT NOT NULL,
    puntaje_medalla INT NOT NULL,
    CONSTRAINT FK_fact_atleta FOREIGN KEY (atleta_id) REFERENCES dbo.dim_atleta(atleta_id),
    CONSTRAINT FK_fact_equipo FOREIGN KEY (equipo_id) REFERENCES dbo.dim_equipo(equipo_id),
    CONSTRAINT FK_fact_edicion FOREIGN KEY (edicion_id) REFERENCES dbo.dim_edicion(edicion_id),
    CONSTRAINT FK_fact_competencia FOREIGN KEY (competencia_id) REFERENCES dbo.dim_competencia(competencia_id)
);

CREATE INDEX IX_fact_equipo ON dbo.fact_participacion(equipo_id);
CREATE INDEX IX_fact_edicion ON dbo.fact_participacion(edicion_id);
CREATE INDEX IX_fact_competencia ON dbo.fact_participacion(competencia_id);
CREATE INDEX IX_fact_medalla ON dbo.fact_participacion(medalla);
GO

CREATE VIEW dbo.vw_participaciones_detalle AS
SELECT
    f.participacion_id, f.medalla, f.obtuvo_medalla, f.oro, f.plata, f.bronce,
    f.puntaje_medalla, a.nombre_atleta, a.sexo, eq.equipo, eq.noc,
    ed.juegos, ed.anio, ed.temporada, ed.ciudad, c.deporte, c.evento,
    c.genero_evento, f.edad, f.altura_cm, f.peso_kg
FROM dbo.fact_participacion f
LEFT JOIN dbo.dim_atleta a ON f.atleta_id = a.atleta_id
LEFT JOIN dbo.dim_equipo eq ON f.equipo_id = eq.equipo_id
LEFT JOIN dbo.dim_edicion ed ON f.edicion_id = ed.edicion_id
LEFT JOIN dbo.dim_competencia c ON f.competencia_id = c.competencia_id;
GO
""",
        encoding="utf-8",
    )


def write_plotly_dashboard(path: Path, summary, figs):
    plotly_js = get_plotlyjs()
    fig1, fig2, fig3, fig4 = figs
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard BI - Juegos Olimpicos</title>
  <script>{plotly_js}</script>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f6f7f9; color: #20242a; }}
    header {{ padding: 22px 28px 14px; background: #fff; border-bottom: 1px solid #d9dee5; }}
    h1 {{ margin: 0; font-size: 28px; }}
    .sub {{ margin-top: 6px; color: #5c6470; font-size: 14px; }}
    main {{ padding: 18px 24px 28px; max-width: 1360px; margin: 0 auto; }}
    .kpis {{ display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 10px; margin-bottom: 14px; }}
    .kpi {{ background: #fff; border: 1px solid #d9dee5; border-radius: 8px; padding: 12px 14px; }}
    .kpi span {{ color: #66707c; font-size: 12px; display: block; }}
    .kpi strong {{ font-size: 22px; line-height: 1.3; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .panel {{ background: #fff; border: 1px solid #d9dee5; border-radius: 8px; padding: 8px; min-width: 0; }}
    .wide {{ grid-column: span 2; }}
    footer {{ color: #66707c; font-size: 12px; padding: 10px 4px; }}
    @media (max-width: 900px) {{ .kpis {{ grid-template-columns: repeat(2, 1fr); }} .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: span 1; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Dashboard BI - Juegos Olimpicos</h1>
    <div class="sub">Modelo estrella construido desde los CSV del taller. Usa leyendas, zoom y seleccion de Plotly para filtrar visualmente.</div>
  </header>
  <main>
    <section class="kpis">
      <div class="kpi"><span>Participaciones</span><strong>{summary['participaciones']:,}</strong></div>
      <div class="kpi"><span>Medallas</span><strong>{summary['medallas']:,}</strong></div>
      <div class="kpi"><span>Oro</span><strong>{summary['oro']:,}</strong></div>
      <div class="kpi"><span>Atletas</span><strong>{summary['atletas_originales']:,}</strong></div>
      <div class="kpi"><span>Deportes</span><strong>{summary['deportes']:,}</strong></div>
      <div class="kpi"><span>Ediciones</span><strong>{summary['ediciones']:,}</strong></div>
    </section>
    <section class="grid">
      <div class="panel">{fig1.to_html(full_html=False, include_plotlyjs=False, div_id='dash_top_noc')}</div>
      <div class="panel">{fig2.to_html(full_html=False, include_plotlyjs=False, div_id='dash_trend')}</div>
      <div class="panel wide">{fig3.to_html(full_html=False, include_plotlyjs=False, div_id='dash_sports')}</div>
      <div class="panel wide">{fig4.to_html(full_html=False, include_plotlyjs=False, div_id='dash_sex')}</div>
    </section>
    <footer>Fuente: archivos CSV ubicados en {SOURCE_DIR}. Generado por ETL Python y cargado en SQLite.</footer>
  </main>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    CSV_DIR.mkdir(exist_ok=True)
    IMG_DIR.mkdir(exist_ok=True)

    athletes_src = clean_text_columns(pd.read_csv(SOURCE_DIR / "Athletes_Games.csv"))
    editions_src = clean_text_columns(pd.read_csv(SOURCE_DIR / "Edition_Games.csv"))
    teams_src = clean_text_columns(pd.read_csv(SOURCE_DIR / "equipos_Games.csv"))
    events_src = clean_text_columns(pd.read_csv(SOURCE_DIR / "Events_Olimpycs.csv"))
    fact_src = clean_text_columns(pd.read_csv(SOURCE_DIR / "JJ.OO.csv"))

    dim_atleta = athletes_src.rename(
        columns={
            "athlete_id": "atleta_id",
            "ID": "id_original_atleta",
            "Year": "anio_registro",
            "Name": "nombre_atleta",
            "Sex": "sexo",
            "Age": "edad",
            "Height": "altura_cm",
            "Weight": "peso_kg",
        }
    )[
        [
            "atleta_id",
            "id_original_atleta",
            "anio_registro",
            "nombre_atleta",
            "sexo",
            "edad",
            "altura_cm",
            "peso_kg",
        ]
    ]
    dim_equipo = teams_src.rename(columns={"team_id": "equipo_id", "Team": "equipo", "NOC": "noc"})[
        ["equipo_id", "equipo", "noc"]
    ]
    dim_edicion = editions_src.rename(
        columns={"edition_id": "edicion_id", "Games": "juegos", "Year": "anio", "Season": "temporada", "City": "ciudad"}
    )[["edicion_id", "juegos", "anio", "temporada", "ciudad"]]
    dim_competencia = (
        events_src[["Competition_id", "Sport", "Event"]]
        .drop_duplicates()
        .rename(columns={"Competition_id": "competencia_id", "Sport": "deporte", "Event": "evento"})
        .sort_values("competencia_id")
        .reset_index(drop=True)
    )
    dim_competencia["genero_evento"] = dim_competencia["evento"].map(infer_event_gender)

    key_cols = ["Medal", "athlete_id", "team_id", "edition_id", "Competition_id"]
    if not fact_src[key_cols].reset_index(drop=True).equals(events_src[key_cols].reset_index(drop=True)):
        raise ValueError("JJ.OO.csv no coincide con Events_Olimpycs.csv en las llaves esperadas.")

    fact_participacion = fact_src.rename(
        columns={
            "id_participacion": "participacion_id",
            "Medal": "medalla",
            "athlete_id": "atleta_id",
            "team_id": "equipo_id",
            "edition_id": "edicion_id",
            "Competition_id": "competencia_id",
        }
    )[["participacion_id", "medalla", "atleta_id", "equipo_id", "edicion_id", "competencia_id"]].copy()
    fact_participacion["edad"] = pd.to_numeric(events_src["Age"], errors="coerce")
    fact_participacion["altura_cm"] = pd.to_numeric(events_src["Height"], errors="coerce")
    fact_participacion["peso_kg"] = pd.to_numeric(events_src["Weight"], errors="coerce")
    fact_participacion["obtuvo_medalla"] = (fact_participacion["medalla"] != "No Medal").astype(int)
    fact_participacion["oro"] = (fact_participacion["medalla"] == "Gold").astype(int)
    fact_participacion["plata"] = (fact_participacion["medalla"] == "Silver").astype(int)
    fact_participacion["bronce"] = (fact_participacion["medalla"] == "Bronze").astype(int)
    fact_participacion["puntaje_medalla"] = (
        fact_participacion["medalla"].map({"No Medal": 0, "Bronze": 1, "Silver": 2, "Gold": 3}).astype(int)
    )

    tables = {
        "dim_atleta": dim_atleta,
        "dim_equipo": dim_equipo,
        "dim_edicion": dim_edicion,
        "dim_competencia": dim_competencia,
        "fact_participacion": fact_participacion,
    }
    for name, df in tables.items():
        df.to_csv(CSV_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

    sqlite_path = OUT_DIR / "olimpicos_bi.sqlite"
    if sqlite_path.exists():
        sqlite_path.unlink()
    with sqlite3.connect(sqlite_path) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, index=False, if_exists="replace")
        conn.executescript(
            """
            CREATE INDEX idx_fact_atleta ON fact_participacion(atleta_id);
            CREATE INDEX idx_fact_equipo ON fact_participacion(equipo_id);
            CREATE INDEX idx_fact_edicion ON fact_participacion(edicion_id);
            CREATE INDEX idx_fact_competencia ON fact_participacion(competencia_id);
            CREATE INDEX idx_fact_medalla ON fact_participacion(medalla);

            CREATE VIEW vw_participaciones_detalle AS
            SELECT f.participacion_id, f.medalla, f.obtuvo_medalla, f.oro, f.plata, f.bronce,
                   f.puntaje_medalla, a.nombre_atleta, a.sexo, eq.equipo, eq.noc,
                   ed.juegos, ed.anio, ed.temporada, ed.ciudad, c.deporte, c.evento,
                   c.genero_evento, f.edad, f.altura_cm, f.peso_kg
            FROM fact_participacion f
            LEFT JOIN dim_atleta a ON f.atleta_id = a.atleta_id
            LEFT JOIN dim_equipo eq ON f.equipo_id = eq.equipo_id
            LEFT JOIN dim_edicion ed ON f.edicion_id = ed.edicion_id
            LEFT JOIN dim_competencia c ON f.competencia_id = c.competencia_id;

            CREATE VIEW vw_medallas_por_noc AS
            SELECT noc, equipo, COUNT(*) AS participaciones, SUM(obtuvo_medalla) AS medallas,
                   SUM(oro) AS oro, SUM(plata) AS plata, SUM(bronce) AS bronce
            FROM vw_participaciones_detalle
            GROUP BY noc, equipo
            ORDER BY medallas DESC;
            """
        )

    analitica = (
        fact_participacion.merge(dim_atleta[["atleta_id", "nombre_atleta", "sexo"]], on="atleta_id", how="left")
        .merge(dim_equipo, on="equipo_id", how="left")
        .merge(dim_edicion, on="edicion_id", how="left")
        .merge(dim_competencia, on="competencia_id", how="left")
    )
    medallas = analitica[analitica["obtuvo_medalla"] == 1].copy()
    summary = {
        "participaciones": int(len(fact_participacion)),
        "atletas_dim": int(dim_atleta["atleta_id"].nunique()),
        "atletas_originales": int(dim_atleta["id_original_atleta"].nunique()),
        "equipos": int(dim_equipo["equipo_id"].nunique()),
        "noc": int(dim_equipo["noc"].nunique()),
        "ediciones": int(dim_edicion["edicion_id"].nunique()),
        "competencias": int(dim_competencia["competencia_id"].nunique()),
        "deportes": int(dim_competencia["deporte"].nunique()),
        "medallas": int(fact_participacion["obtuvo_medalla"].sum()),
        "oro": int(fact_participacion["oro"].sum()),
        "plata": int(fact_participacion["plata"].sum()),
        "bronce": int(fact_participacion["bronce"].sum()),
        "anio_min": int(dim_edicion["anio"].min()),
        "anio_max": int(dim_edicion["anio"].max()),
    }
    summary["tasa_medalla"] = round(summary["medallas"] / summary["participaciones"] * 100, 2)
    quality = {
        "source_rows": {
            "Athletes_Games.csv": int(len(athletes_src)),
            "Edition_Games.csv": int(len(editions_src)),
            "equipos_Games.csv": int(len(teams_src)),
            "Events_Olimpycs.csv": int(len(events_src)),
            "JJ.OO.csv": int(len(fact_src)),
        },
        "duplicated_rows": {
            "Athletes_Games.csv": int(athletes_src.duplicated().sum()),
            "Edition_Games.csv": int(editions_src.duplicated().sum()),
            "equipos_Games.csv": int(teams_src.duplicated().sum()),
            "Events_Olimpycs.csv": int(events_src.duplicated().sum()),
            "JJ.OO.csv": int(fact_src.duplicated().sum()),
        },
        "nulls_total": {
            "Athletes_Games.csv": int(athletes_src.isna().sum().sum()),
            "Edition_Games.csv": int(editions_src.isna().sum().sum()),
            "equipos_Games.csv": int(teams_src.isna().sum().sum()),
            "Events_Olimpycs.csv": int(events_src.isna().sum().sum()),
            "JJ.OO.csv": int(fact_src.isna().sum().sum()),
        },
        "foreign_key_orphans": {
            "fact_atleta_no_dim": int((~fact_participacion["atleta_id"].isin(dim_atleta["atleta_id"])).sum()),
            "fact_equipo_no_dim": int((~fact_participacion["equipo_id"].isin(dim_equipo["equipo_id"])).sum()),
            "fact_edicion_no_dim": int((~fact_participacion["edicion_id"].isin(dim_edicion["edicion_id"])).sum()),
            "fact_competencia_no_dim": int((~fact_participacion["competencia_id"].isin(dim_competencia["competencia_id"])).sum()),
        },
    }
    (OUT_DIR / "resumen_calidad_datos.json").write_text(
        json.dumps({"summary": summary, "quality": quality}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    top_noc_total = (
        medallas.groupby("noc", as_index=False)
        .agg(medallas=("obtuvo_medalla", "sum"), oro=("oro", "sum"), plata=("plata", "sum"), bronce=("bronce", "sum"))
        .sort_values("medallas", ascending=False)
        .head(15)
    )
    medals_by_year = (
        medallas.groupby(["anio", "temporada"], as_index=False)
        .agg(medallas=("obtuvo_medalla", "sum"), oro=("oro", "sum"), plata=("plata", "sum"), bronce=("bronce", "sum"))
    )
    top_sports = medallas.groupby(["deporte", "medalla"], as_index=False).size().rename(columns={"size": "conteo"})
    top_sport_names = medallas.groupby("deporte").size().sort_values(ascending=False).head(12).index
    top_sports = top_sports[top_sports["deporte"].isin(top_sport_names)]
    sex_year = analitica.groupby(["anio", "sexo"], as_index=False).size().rename(columns={"size": "participaciones"})

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    top10 = top_noc_total.head(10).sort_values("medallas")
    ax.barh(top10["noc"], top10["medallas"], color="#2f6f8f")
    ax.set_title("Top 10 NOC por medallas")
    ax.set_xlabel("Medallas")
    ax.set_ylabel("NOC")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "top_10_noc_medallas.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5), dpi=140)
    trend = medals_by_year.groupby("anio", as_index=False)["medallas"].sum()
    ax.plot(trend["anio"], trend["medallas"], color="#bf5b45", linewidth=2)
    ax.set_title("Evolucion de medallas por anio")
    ax.set_xlabel("Anio")
    ax.set_ylabel("Medallas")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "evolucion_medallas_anio.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6), dpi=140)
    sport_total = medallas.groupby("deporte").size().sort_values(ascending=False).head(10).sort_values()
    ax.barh(sport_total.index, sport_total.values, color="#4b8f55")
    ax.set_title("Top 10 deportes por medallas")
    ax.set_xlabel("Medallas")
    ax.set_ylabel("Deporte")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "top_deportes_medallas.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5), dpi=140)
    sex_pivot = sex_year.pivot(index="anio", columns="sexo", values="participaciones").fillna(0)
    for col, color in [("F", "#8a5fbf"), ("M", "#d29c2f")]:
        if col in sex_pivot.columns:
            ax.plot(sex_pivot.index, sex_pivot[col], label=col, linewidth=2, color=color)
    ax.set_title("Participaciones por sexo a traves del tiempo")
    ax.set_xlabel("Anio")
    ax.set_ylabel("Participaciones")
    ax.legend(title="Sexo")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "participaciones_sexo_anio.png")
    plt.close(fig)

    medal_order = ["Gold", "Silver", "Bronze"]
    color_map = {"Gold": "#d6a22a", "Silver": "#9aa3ad", "Bronze": "#b66d3d"}
    fig1_data = medallas[medallas["noc"].isin(top_noc_total["noc"])].groupby(["noc", "medalla"], as_index=False).size()
    fig1_data = fig1_data.rename(columns={"size": "conteo"})
    fig1_data["noc"] = pd.Categorical(fig1_data["noc"], categories=top_noc_total["noc"][::-1], ordered=True)
    fig1 = px.bar(
        fig1_data.sort_values("noc"),
        x="conteo",
        y="noc",
        color="medalla",
        orientation="h",
        category_orders={"medalla": medal_order},
        color_discrete_map=color_map,
        labels={"conteo": "Medallas", "noc": "NOC", "medalla": "Tipo"},
        title="Top 15 NOC por medallas",
    )
    fig1.update_layout(height=520, margin=dict(l=60, r=20, t=55, b=40), legend_title_text="Medalla")
    fig2 = px.line(
        medals_by_year,
        x="anio",
        y="medallas",
        color="temporada",
        markers=True,
        labels={"anio": "Anio", "medallas": "Medallas", "temporada": "Temporada"},
        title="Evolucion de medallas por edicion",
    )
    fig2.update_layout(height=430, margin=dict(l=55, r=20, t=55, b=40))
    fig3 = px.bar(
        top_sports,
        x="deporte",
        y="conteo",
        color="medalla",
        category_orders={"medalla": medal_order},
        color_discrete_map=color_map,
        labels={"deporte": "Deporte", "conteo": "Medallas", "medalla": "Tipo"},
        title="Medallas por deporte y tipo",
    )
    fig3.update_layout(height=500, margin=dict(l=50, r=20, t=55, b=130), xaxis_tickangle=-35)
    fig4 = px.area(
        sex_year,
        x="anio",
        y="participaciones",
        color="sexo",
        color_discrete_map={"M": "#2f6f8f", "F": "#bf5b45"},
        labels={"anio": "Anio", "participaciones": "Participaciones", "sexo": "Sexo"},
        title="Participacion por sexo a traves del tiempo",
    )
    fig4.update_layout(height=430, margin=dict(l=55, r=20, t=55, b=40))
    write_plotly_dashboard(OUT_DIR / "dashboard_plotly_olimpicos.html", summary, (fig1, fig2, fig3, fig4))

    write_sql_server(OUT_DIR / "modelo_sqlserver.sql")
    write_notebook(OUT_DIR / "Taller_ETL_BI_Olimpicos.ipynb")
    (OUT_DIR / "etl_olimpicos.py").write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    powerbi_guide = """# Guia Power BI, SSIS y SSAS

## Fuente recomendada
Importar los archivos de `csv_powerbi`: `dim_atleta.csv`, `dim_equipo.csv`, `dim_edicion.csv`, `dim_competencia.csv` y `fact_participacion.csv`.

## Relaciones
- `dim_atleta[atleta_id]` -> `fact_participacion[atleta_id]`
- `dim_equipo[equipo_id]` -> `fact_participacion[equipo_id]`
- `dim_edicion[edicion_id]` -> `fact_participacion[edicion_id]`
- `dim_competencia[competencia_id]` -> `fact_participacion[competencia_id]`

## Medidas DAX sugeridas
```DAX
Participaciones = COUNTROWS(fact_participacion)
Total Medallas = SUM(fact_participacion[obtuvo_medalla])
Oro = SUM(fact_participacion[oro])
Plata = SUM(fact_participacion[plata])
Bronce = SUM(fact_participacion[bronce])
Tasa Medalla = DIVIDE([Total Medallas], [Participaciones])
Edad Promedio = AVERAGE(fact_participacion[edad])
```

## Dashboard solicitado
1. KPI: `Total Medallas`.
2. Barras: medallas por `noc` o `equipo`.
3. Linea: medallas por `anio`, segmentadas por `temporada`.
4. Columnas apiladas: medallas por `deporte` y `medalla`.
5. Filtro interactivo: slicer de `temporada`, `medalla` o `noc`.

## SSIS
Flujo sugerido: Flat File Source -> Data Conversion -> Derived Column -> Lookup de dimensiones -> OLE DB Destination. Cargar primero dimensiones y luego `fact_participacion`.

## SSAS
Modelo analitico: `fact_participacion` como tabla de hechos, dimensiones Atleta, Equipo, Edicion y Competencia. Medidas: participaciones, medallas, oro, plata, bronce, tasa de medalla, edad promedio, altura promedio y peso promedio.
"""
    (OUT_DIR / "guia_powerbi_ssis_ssas.md").write_text(powerbi_guide, encoding="utf-8")

    report_md = f"""# Informe del Proyecto BI - Juegos Olimpicos

## 1. Objetivo
Desarrollar un proceso completo de analitica de datos sobre una base historica de Juegos Olimpicos, usando Microsoft BI y Python.

## 2. Fuentes de datos
| Archivo | Filas | Rol en el modelo |
|---|---:|---|
| Athletes_Games.csv | {quality['source_rows']['Athletes_Games.csv']:,} | Dimension Atleta |
| Edition_Games.csv | {quality['source_rows']['Edition_Games.csv']:,} | Dimension Edicion |
| equipos_Games.csv | {quality['source_rows']['equipos_Games.csv']:,} | Dimension Equipo/NOC |
| Events_Olimpycs.csv | {quality['source_rows']['Events_Olimpycs.csv']:,} | Fuente enriquecida |
| JJ.OO.csv | {quality['source_rows']['JJ.OO.csv']:,} | Hechos de participacion |

## 3. Calidad de datos
No se encontraron filas duplicadas ni valores nulos. Las llaves de la tabla de hechos tienen integridad con las dimensiones: 0 registros huerfanos en atleta, equipo, edicion y competencia.

## 4. Proceso ETL
Extraccion desde CSV, limpieza de textos, renombrado de columnas, creacion de `dim_competencia`, indicadores de medalla y carga a SQLite/CSV.

## 5. Modelo analitico
Modelo estrella con `fact_participacion` como tabla de hechos y las dimensiones `dim_atleta`, `dim_equipo`, `dim_edicion` y `dim_competencia`.

Medidas principales: participaciones {summary['participaciones']:,}, medallas {summary['medallas']:,}, oro {summary['oro']:,}, plata {summary['plata']:,}, bronce {summary['bronce']:,}, tasa de medalla {summary['tasa_medalla']}%.

## 6. Dashboard Power BI
Importar los CSV de `csv_powerbi`, crear relaciones y usar KPI, barras por NOC, linea por anio, columnas por deporte/tipo y slicer de temporada, medalla o NOC.

## 7. Dashboard Python
Se genero `dashboard_plotly_olimpicos.html` con cuatro graficos interactivos.

![Top NOC](imagenes/top_10_noc_medallas.png)
![Evolucion](imagenes/evolucion_medallas_anio.png)
![Deportes](imagenes/top_deportes_medallas.png)
![Sexo](imagenes/participaciones_sexo_anio.png)

## 8. Analisis comparativo
| Criterio | Microsoft BI | Python |
|---|---|---|
| Facilidad | Visual y orientado a negocio. Requiere SQL Server, SSDT y Power BI. | Requiere programar, pero queda reproducible. |
| Flexibilidad | Fuerte en modelos gobernados y reporting corporativo. | Muy flexible para limpieza, automatizacion y visualizacion. |
| Escalabilidad | Alta con SQL Server, SSIS y SSAS. | Alta al integrarse con bases, Spark o nube. |
| Aplicabilidad | Publicacion empresarial y seguridad. | Exploracion, ciencia de datos y prototipos analiticos. |

## 9. Conclusiones
El modelo estrella permite analizar desempeno olimpico por NOC, deporte, evento, anio, temporada y sexo. Microsoft BI es conveniente para publicacion empresarial; Python aporta trazabilidad y automatizacion del ETL.
"""
    (OUT_DIR / "Informe_Taller_BI_Olimpicos.md").write_text(report_md, encoding="utf-8")

    report_html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Informe Taller BI - Juegos Olimpicos</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; color:#20242a; max-width:980px; margin:32px auto; line-height:1.55; padding:0 20px; }}
h1,h2 {{ color:#1f3b4d; }} table {{ border-collapse:collapse; width:100%; margin:16px 0; }}
th,td {{ border:1px solid #d9dee5; padding:8px; text-align:left; }} th {{ background:#eef2f5; }}
img {{ max-width:100%; border:1px solid #d9dee5; border-radius:6px; margin:10px 0 22px; }}
.kpi {{ display:inline-block; min-width:140px; padding:10px 12px; border:1px solid #d9dee5; border-radius:8px; margin:4px; background:#f8fafb; }}
.kpi span {{ display:block; color:#66707c; font-size:12px; }} .kpi strong {{ font-size:22px; }}
code {{ background:#f3f5f7; padding:2px 4px; border-radius:4px; }}
</style></head><body>
<h1>Informe del Proyecto BI - Juegos Olimpicos</h1>
<h2>Objetivo</h2><p>Desarrollar un proceso completo de analitica de datos sobre Juegos Olimpicos usando Microsoft BI y Python.</p>
<h2>Fuentes de datos</h2>
<table><tr><th>Archivo</th><th>Filas</th><th>Rol</th></tr>
<tr><td>Athletes_Games.csv</td><td>{quality['source_rows']['Athletes_Games.csv']:,}</td><td>Dimension Atleta</td></tr>
<tr><td>Edition_Games.csv</td><td>{quality['source_rows']['Edition_Games.csv']:,}</td><td>Dimension Edicion</td></tr>
<tr><td>equipos_Games.csv</td><td>{quality['source_rows']['equipos_Games.csv']:,}</td><td>Dimension Equipo/NOC</td></tr>
<tr><td>Events_Olimpycs.csv</td><td>{quality['source_rows']['Events_Olimpycs.csv']:,}</td><td>Fuente enriquecida</td></tr>
<tr><td>JJ.OO.csv</td><td>{quality['source_rows']['JJ.OO.csv']:,}</td><td>Hechos de participacion</td></tr></table>
<h2>Modelo analitico</h2><p>Modelo estrella con <code>fact_participacion</code> como tabla de hechos y dimensiones de atleta, equipo, edicion y competencia.</p>
<div class="kpi"><span>Participaciones</span><strong>{summary['participaciones']:,}</strong></div>
<div class="kpi"><span>Medallas</span><strong>{summary['medallas']:,}</strong></div>
<div class="kpi"><span>Oro</span><strong>{summary['oro']:,}</strong></div>
<div class="kpi"><span>Plata</span><strong>{summary['plata']:,}</strong></div>
<div class="kpi"><span>Bronce</span><strong>{summary['bronce']:,}</strong></div>
<div class="kpi"><span>Tasa medalla</span><strong>{summary['tasa_medalla']}%</strong></div>
<h2>ETL</h2><p>Se limpiaron columnas de texto, se validaron llaves, se construyeron dimensiones y se crearon indicadores de medalla. La carga se realizo en SQLite y CSV para Power BI.</p>
<h2>Visualizaciones Python</h2>
<img src="imagenes/top_10_noc_medallas.png" alt="Top NOC por medallas">
<img src="imagenes/evolucion_medallas_anio.png" alt="Evolucion de medallas por anio">
<img src="imagenes/top_deportes_medallas.png" alt="Top deportes por medallas">
<img src="imagenes/participaciones_sexo_anio.png" alt="Participaciones por sexo">
<h2>Microsoft BI</h2><p>Para SSIS, cargar primero dimensiones y luego la tabla de hechos. Para SSAS, construir el cubo con las dimensiones y medidas indicadas. Para Power BI, usar un KPI, tres visualizaciones y un slicer interactivo.</p>
<h2>Analisis comparativo</h2>
<table><tr><th>Criterio</th><th>Microsoft BI</th><th>Python</th></tr>
<tr><td>Facilidad</td><td>Visual y orientado a negocio.</td><td>Requiere codigo, pero es reproducible.</td></tr>
<tr><td>Flexibilidad</td><td>Fuerte en modelos gobernados.</td><td>Muy flexible para transformacion y analisis.</td></tr>
<tr><td>Escalabilidad</td><td>Alta con SQL Server, SSIS y SSAS.</td><td>Alta al integrarse con bases, Spark o nube.</td></tr>
<tr><td>Aplicabilidad</td><td>Reporting corporativo y dashboards publicados.</td><td>Exploracion, automatizacion y ciencia de datos.</td></tr></table>
<h2>Conclusion</h2><p>El modelo estrella permite analizar desempeno olimpico por NOC, deporte, evento, anio, temporada y sexo.</p>
</body></html>"""
    (OUT_DIR / "Informe_Taller_BI_Olimpicos.html").write_text(report_html, encoding="utf-8")

    annex = f"""# Anexos - Archivos del taller

## Fuentes originales
- `{SOURCE_DIR / 'Athletes_Games.csv'}`
- `{SOURCE_DIR / 'Edition_Games.csv'}`
- `{SOURCE_DIR / 'equipos_Games.csv'}`
- `{SOURCE_DIR / 'Events_Olimpycs.csv'}`
- `{SOURCE_DIR / 'JJ.OO.csv'}`
- `{PDF_PATH}`

## Entregables generados
- `etl_olimpicos.py`
- `Taller_ETL_BI_Olimpicos.ipynb`
- `olimpicos_bi.sqlite`
- `csv_powerbi/*.csv`
- `dashboard_plotly_olimpicos.html`
- `Informe_Taller_BI_Olimpicos.md`
- `Informe_Taller_BI_Olimpicos.html`
- `modelo_sqlserver.sql`
- `guia_powerbi_ssis_ssas.md`
- `imagenes/*.png`
- `resumen_calidad_datos.json`
"""
    (OUT_DIR / "Anexos_Archivos.md").write_text(annex, encoding="utf-8")

    readme = f"""# Entregables Taller BI - Juegos Olimpicos

Carpeta generada desde los CSV ubicados en `{SOURCE_DIR}`.

## Abrir primero
- Informe: `Informe_Taller_BI_Olimpicos.html`
- Dashboard Python: `dashboard_plotly_olimpicos.html`
- Notebook: `Taller_ETL_BI_Olimpicos.ipynb`

## Para Power BI
Importa los CSV de `csv_powerbi` y crea las relaciones descritas en `guia_powerbi_ssis_ssas.md`.

## Para regenerar
```powershell
python .\\etl_olimpicos.py
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    (OUT_DIR / "requirements.txt").write_text("pandas\nplotly\nmatplotlib\n", encoding="utf-8")

    print("OK")
    print(f"Carpeta: {OUT_DIR}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
