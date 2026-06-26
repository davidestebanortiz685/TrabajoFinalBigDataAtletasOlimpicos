# Guia Power BI, SSIS y SSAS

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
