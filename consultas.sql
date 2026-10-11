-- Consultas listas para data/historico.db (la crea analizar.cmd / analizar.sh).
--
-- Como usarlas: abre data/historico.db en DB Browser for SQLite, pestaña
-- "Ejecutar SQL", pega UNA consulta y pulsa Ctrl+Enter (Cmd+Enter en Mac).
--
-- Tablas:
--   ofertas      una fila por oferta (todo lo que el scraper vio alguna vez)
--   habilidades  que pide cada oferta (id, habilidad, grupo). Solo existe para las
--                ofertas que traen descripcion: Multitrabajos y la mayoria de Indeed.
--
-- Dos detalles que conviene saber:
--   * Busca palabras en titulo_normalizado, no en title: esta en minusculas y sin
--     tildes, asi que '%analisis%' encuentra "Análisis", "ANÁLISIS" y "analisis".
--   * date_posted falta en ~40% de las ofertas (no todos los sitios la dan). Para
--     ordenar por fecha se usa la de publicacion y, si falta, el dia en que el scraper
--     la vio por primera vez.


-- 1. Las ofertas mas recientes que coinciden con tus palabras --------------------
-- Cambia las palabras (minusculas, sin tildes) y la ciudad. Para todas las
-- ciudades, borra la linea de ciudad.
SELECT COALESCE(NULLIF(date_posted, ''), visto_primera_vez) AS fecha,
       title, empresa, ciudad, site, job_url
FROM ofertas
WHERE (titulo_normalizado LIKE '%analista%'
    OR titulo_normalizado LIKE '%datos%'
    OR titulo_normalizado LIKE '%procesos%')
  AND titulo_normalizado NOT LIKE '%pasante%'
  AND ciudad = 'Quito'
  AND es_oferta_real = 1
ORDER BY fecha DESC
LIMIT 50;


-- 2. Las que mejor encajan con tu perfil (ultimos 30 dias) -----------------------
-- puntaje sale de los terminos de perfil.py; las vetadas por EXCLUIDOS no salen.
SELECT puntaje, terminos, title, empresa, ciudad, job_url
FROM ofertas
WHERE motivo_exclusion = ''
  AND es_oferta_real = 1
  AND puntaje > 0
  AND COALESCE(NULLIF(date_posted, ''), visto_primera_vez) >= date('now', '-30 day')
ORDER BY puntaje DESC
LIMIT 30;


-- 3. Ofertas por ciudad (ultimos 30 dias) ----------------------------------------
SELECT COALESCE(NULLIF(ciudad, ''), provincia || ' (prov.)') AS ciudad,
       COUNT(*) AS ofertas
FROM ofertas
WHERE es_oferta_real = 1
  AND COALESCE(NULLIF(date_posted, ''), visto_primera_vez) >= date('now', '-30 day')
GROUP BY 1
ORDER BY ofertas DESC;


-- 4. Que tipo de puestos se buscan (familias) ------------------------------------
-- Las familias estan en FAMILIAS de reporte.py.
SELECT familia,
       COUNT(*) AS ofertas,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM ofertas WHERE es_oferta_real = 1), 1)
           AS porcentaje
FROM ofertas
WHERE es_oferta_real = 1
GROUP BY familia
ORDER BY ofertas DESC;


-- 5. Empresas que mas publican ---------------------------------------------------
-- Sin las "confidenciales", que juntan ~20 formas de ocultar el nombre.
SELECT empresa, COUNT(*) AS ofertas
FROM ofertas
WHERE empresa_confidencial = 0
  AND empresa IS NOT NULL AND empresa != ''
GROUP BY empresa
ORDER BY ofertas DESC
LIMIT 20;


-- 6. Habilidades mas pedidas -----------------------------------------------------
-- El porcentaje es sobre las ofertas que traen descripcion, no sobre todas: el
-- titulo solo no dice que herramientas piden.
SELECT h.grupo, h.habilidad,
       COUNT(DISTINCT h.id) AS ofertas,
       ROUND(100.0 * COUNT(DISTINCT h.id) /
             (SELECT COUNT(DISTINCT id) FROM habilidades), 1) AS porcentaje
FROM habilidades h
GROUP BY h.grupo, h.habilidad
ORDER BY ofertas DESC;


-- 7. Habilidades que piden para un tipo de puesto --------------------------------
-- Cambia la familia ('Datos/BI', 'Desarrollador/TI', ...; ver la consulta 4).
SELECT h.habilidad, COUNT(DISTINCT h.id) AS ofertas
FROM habilidades h
JOIN ofertas o ON o.id = h.id
WHERE o.familia = 'Datos/BI'
GROUP BY h.habilidad
ORDER BY ofertas DESC;


-- 8. Ofertas nuevas por semana ---------------------------------------------------
-- Por el dia en que el scraper las vio: mide cuanto se mueve el mercado.
SELECT strftime('%Y-%W', visto_primera_vez) AS semana, COUNT(*) AS ofertas
FROM ofertas
WHERE es_oferta_real = 1
GROUP BY semana
ORDER BY semana;


-- 9. Ofertas por sitio -----------------------------------------------------------
SELECT site, COUNT(*) AS ofertas
FROM ofertas
GROUP BY site
ORDER BY ofertas DESC;
