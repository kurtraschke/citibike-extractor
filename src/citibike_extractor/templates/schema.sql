create table tripdata
(
    ride_id                VARCHAR,
    rideable_type          VARCHAR,
    started_at             TIMESTAMP,
    ended_at               TIMESTAMP,
    trip_duration          INTERVAL,
    start_station_name     VARCHAR,
    start_station_id       VARCHAR,
    start_station_location GEOMETRY,
    end_station_name       VARCHAR,
    end_station_id         VARCHAR,
    end_station_location   GEOMETRY,
    member_casual          VARCHAR,
    bike_id                VARCHAR,
    birth_year             USMALLINT,
    gender                 UTINYINT,
    archive                VARCHAR,
    filename               VARCHAR,
    started_year           USMALLINT GENERATED ALWAYS AS (EXTRACT('year' FROM started_at)) VIRTUAL,
    started_month          UTINYINT GENERATED ALWAYS AS (EXTRACT('month' FROM started_at)) VIRTUAL
);