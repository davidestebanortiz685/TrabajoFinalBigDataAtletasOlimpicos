/*
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
