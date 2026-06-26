CREATE DATABASE JuegosOlimpicos;
GO
USE JuegosOlimpicos;
GO

CREATE TABLE dim_edicion (
    edition_id   INT PRIMARY KEY,
    Games        VARCHAR(100),
    Year         INT,
    Season       VARCHAR(50),
    City         VARCHAR(100)
);

CREATE TABLE dim_atleta (
    athlete_id  INT PRIMARY KEY,
    ID          INT,
    Year        INT,
    Name        VARCHAR(200),
    Sex         CHAR(1),
    Age         VARCHAR(20),
    Height      VARCHAR(20),
    Weight      VARCHAR(20)
);

CREATE TABLE dim_equipo (
    team_id      INT PRIMARY KEY,
    Team         VARCHAR(100),
    NOC          VARCHAR(50)
);

CREATE TABLE dim_Competicion (
    Competition_id INT PRIMARY KEY,
    Sport          VARCHAR(150),
    Event          VARCHAR(300)
);

CREATE TABLE fact_participacion (
    id_participacion INT PRIMARY KEY,
    Medal            VARCHAR(50),
    athlete_id       INT FOREIGN KEY REFERENCES dim_atleta(athlete_id),
    team_id          INT FOREIGN KEY REFERENCES dim_equipo(team_id),
    edition_id       INT FOREIGN KEY REFERENCES dim_edicion(edition_id),
    Competition_id   INT FOREIGN KEY REFERENCES dim_Competicion(Competition_id)
);

-- Limpia valores problemáticos
UPDATE dim_atleta SET Age    = NULL WHERE LTRIM(RTRIM(Age))    = '' OR ISNUMERIC(Age)    = 0;
UPDATE dim_atleta SET Height = NULL WHERE LTRIM(RTRIM(Height)) = '' OR ISNUMERIC(Height) = 0;
UPDATE dim_atleta SET Weight = NULL WHERE LTRIM(RTRIM(Weight)) = '' OR ISNUMERIC(Weight) = 0;

-- Convierte a DECIMAL(6,2) — suficiente para edad, talla y peso
ALTER TABLE dim_atleta ALTER COLUMN Age    DECIMAL(6,2);
ALTER TABLE dim_atleta ALTER COLUMN Height DECIMAL(6,2);
ALTER TABLE dim_atleta ALTER COLUMN Weight DECIMAL(6,2);

USE JuegosOlimpicos;
SELECT 'dim_edicion'          AS tabla, COUNT(*) AS filas FROM dim_edicion
UNION ALL
SELECT 'dim_atleta',           COUNT(*) FROM dim_atleta
UNION ALL
SELECT 'dim_equipo',           COUNT(*) FROM dim_equipo
UNION ALL
SELECT 'dim_Competicion',           COUNT(*) FROM dim_Competicion
UNION ALL
SELECT 'fact_participacion',   COUNT(*) FROM fact_participacion;
