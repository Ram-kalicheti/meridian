CREATE TABLE dim_date (
    date_key     INT      NOT NULL,
    full_date    DATE     NOT NULL,
    year         INT      NOT NULL,
    quarter      INT      NOT NULL,
    month        INT      NOT NULL,
    day          INT      NOT NULL,
    week_of_year INT      NOT NULL,
    day_of_week  INT      NOT NULL,  -- 1=Sun, 7=Sat (DATEPART weekday default)
    is_weekend   BIT      NOT NULL
);
