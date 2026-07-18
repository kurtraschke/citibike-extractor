citibike-extractor
==================

This is `citibike-extractor`, a Python utility designed to scrub and ingest the [Citi Bike](https://citibikenyc.com/) [trip-level history](https://citibikenyc.com/system-data) [dataset](https://s3.amazonaws.com/tripdata/index.html) into a [DuckDB](https://duckdb.org/) database.

More details available in [this blog post](https://kurtraschke.com/2026/07/citibike-extractor).

Usage
-----

(We assume you have [`rclone`](https://rclone.org/) and [`uv`](https://docs.astral.sh/uv/) installed.)

1. Download the contents of the `tripdata` S3 bucket into a temporary directory: `rclone copy :s3:tripdata tripdata --filter "+ *-citibike-tripdata*.zip`
2. Run `citibike-extractor`: `uvx run --from git+https://github.com/kurtraschke/citibike-extractor.git citibike-extractor tripdata.db tripdata/*.zip`
3. Optionally, open the resulting DuckDB database: `duckdb -ui tripdata.db`


If you prefer to analyze the data with something other than DuckDB, you can export to Parquet:

```sql
COPY (FROM tripdata ORDER BY started_at, ended_at, ride_id)
TO 'tripdata' (
    FORMAT PARQUET, COMPRESSION 'zstd',
    PARTITION_BY (started_year, started_month)
);
```