from enum import Enum
from importlib.resources import files
from typing import Mapping


class FileFormatGeneration(Enum):
    ONE = 1
    TWO = 2


FORMATS_BY_HEADER: Mapping[tuple[str, ...], FileFormatGeneration] = {
    (
        "tripduration",
        "starttime",
        "stoptime",
        "start station id",
        "start station name",
        "start station latitude",
        "start station longitude",
        "end station id",
        "end station name",
        "end station latitude",
        "end station longitude",
        "bikeid",
        "usertype",
        "birth year",
        "gender",
    ): FileFormatGeneration.ONE,
    (
        "Trip Duration",
        "Start Time",
        "Stop Time",
        "Start Station ID",
        "Start Station Name",
        "Start Station Latitude",
        "Start Station Longitude",
        "End Station ID",
        "End Station Name",
        "End Station Latitude",
        "End Station Longitude",
        "Bike ID",
        "User Type",
        "Birth Year",
        "Gender",
    ): FileFormatGeneration.ONE,
    (
        "ride_id",
        "rideable_type",
        "started_at",
        "ended_at",
        "start_station_name",
        "start_station_id",
        "end_station_name",
        "end_station_id",
        "start_lat",
        "start_lng",
        "end_lat",
        "end_lng",
        "member_casual",
    ): FileFormatGeneration.TWO,
}

SQL_TEMPLATES = {
    FileFormatGeneration.ONE: (
        files("citibike_extractor.templates") / "f1-import.sql"
    ).read_text(),
    FileFormatGeneration.TWO: (
        files("citibike_extractor.templates") / "f2-import.sql"
    ).read_text(),
}

READ_CSV_ARGS = {
    FileFormatGeneration.ONE: {
        "columns": {
            "trip_duration": "INTERVAL",
            "start_time": "VARCHAR",
            "stop_time": "VARCHAR",
            "start_station_id": "VARCHAR",
            "start_station_name": "VARCHAR",
            "start_station_latitude": "DOUBLE",
            "start_station_longitude": "DOUBLE",
            "end_station_id": "VARCHAR",
            "end_station_name": "VARCHAR",
            "end_station_latitude": "DOUBLE",
            "end_station_longitude": "DOUBLE",
            "bike_id": "VARCHAR",
            "user_type": "VARCHAR",
            "birth_year": "VARCHAR",
            "gender": "INTEGER",
        },
        "quotechar": '"',
        "header": False,
        "skiprows": 1,
    },
    FileFormatGeneration.TWO: {
        "columns": {
            "ride_id": "VARCHAR",
            "rideable_type": "VARCHAR",
            "started_at": "TIMESTAMP",
            "ended_at": "TIMESTAMP",
            "start_station_name": "VARCHAR",
            "start_station_id": "VARCHAR",
            "end_station_name": "VARCHAR",
            "end_station_id": "VARCHAR",
            "start_lat": "DOUBLE",
            "start_lng": "DOUBLE",
            "end_lat": "DOUBLE",
            "end_lng": "DOUBLE",
            "member_casual": "VARCHAR",
        },
    },
}
