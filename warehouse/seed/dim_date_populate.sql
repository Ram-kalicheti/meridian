-- populates dim_date for 2024-01-01 through 2027-12-31 (1461 rows)
-- run once after CREATE TABLE dim_date executes
WITH date_series AS (
    SELECT CAST('2024-01-01' AS DATE) AS d
    UNION ALL
    SELECT DATEADD(DAY, 1, d)
    FROM date_series
    WHERE DATEADD(DAY, 1, d) <= '2027-12-31'
)
INSERT INTO dim_date (date_key, full_date, year, quarter, month, day, week_of_year, day_of_week, is_weekend)
SELECT
    CAST(FORMAT(d, 'yyyyMMdd') AS INT)                                          AS date_key,
    d                                                                           AS full_date,
    YEAR(d)                                                                     AS year,
    DATEPART(QUARTER, d)                                                        AS quarter,
    MONTH(d)                                                                    AS month,
    DAY(d)                                                                      AS day,
    DATEPART(ISO_WEEK, d)                                                       AS week_of_year,
    DATEPART(WEEKDAY, d)                                                        AS day_of_week,
    CASE WHEN DATEPART(WEEKDAY, d) IN (1, 7) THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_weekend
FROM date_series
OPTION (MAXRECURSION 1500);

-- verify
SELECT COUNT(*) AS row_count, MIN(full_date) AS min_date, MAX(full_date) AS max_date FROM dim_date;
