import argparse
import contextlib
import csv
import io
from collections.abc import Callable
from enum import Enum
from functools import partial
from importlib.resources import files
from os import PathLike
from pathlib import Path, PurePath
from typing import Iterable, Mapping, Tuple, IO
from zipfile import ZipFile, ZipInfo

from duckdb import DuckDBPyConnection, connect
from tqdm import tqdm

BARE_CSV = "*.csv"
ONE_LEVEL_NESTED_CSV = "*-citibike-tripdata/*.csv"

CAN_HAVE_TWO_LEVEL_NESTED_CSV = "**/201[4-79]-citibike-tripdata.zip"
TWO_LEVEL_NESTED_CSV = "*-citibike-tripdata/*/*.csv"

NESTED_ZIP = "*/*.zip"

IGNORE_FILES = "2018-citibike-tripdata/201804-citibike-tripdata_[12].csv"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("output_database", type=Path)
    parser.add_argument("input_files", nargs="*", type=Path)

    args = parser.parse_args()

    output_database: Path = args.output_database
    input_files: Iterable[Path] = args.input_files

    with connect(
        output_database, config={"storage_compatibility_version": "latest"}
    ) as con:
        con.sql("INSTALL spatial")
        con.sql("LOAD spatial")
        con.sql((files("citibike_extractor.templates") / "schema.sql").read_text())

        with tqdm(input_files, unit="archive") as pb:
            handler = partial(handle_file, con, pb)

            for input_file in pb:
                handle_zip_file(
                    input_file,
                    (
                        (partial(is_valid_csv, input_file), handler),
                        (
                            lambda p: p.full_match(NESTED_ZIP),
                            partial(handle_nested_zip, handler),
                        ),
                    ),
                )


def is_valid_csv(input_file: PurePath, p: PurePath):
    return (
        p.full_match(BARE_CSV)
        or p.full_match(ONE_LEVEL_NESTED_CSV)
        or (
            input_file.full_match(CAN_HAVE_TWO_LEVEL_NESTED_CSV)
            and p.full_match(TWO_LEVEL_NESTED_CSV)
        )
    ) and not p.full_match(IGNORE_FILES)


def handle_zip_file(
    input_file: str | PathLike[str] | IO[bytes],
    operations: Iterable[
        Tuple[Callable[[PurePath], bool], Callable[[ZipFile, ZipInfo], None]]
    ],
):
    with ZipFile(input_file, "r") as zf:
        for zi in zf.infolist():
            p = PurePath(zi.filename)

            for entry_test, handler in operations:
                if entry_test(p):
                    handler(zf, zi)


def handle_nested_zip(
    handler: Callable[[ZipFile, ZipInfo], None], zf: ZipFile, zi: ZipInfo
):
    with zf.open(zi) as nz:
        handle_zip_file(
            nz,
            (
                (
                    lambda p: p.full_match(BARE_CSV),
                    handler,
                ),
            ),
        )


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


def handle_file(con: DuckDBPyConnection, pb: tqdm, zf: ZipFile, zi: ZipInfo):
    with zf.open(zi) as f, io.TextIOWrapper(f) as w:
        cr = csv.reader(w)
        header_row = next(cr)

        fmt = FORMATS_BY_HEADER[tuple(header_row)]

    with (
        zf.open(zi) as f,
        contextlib.closing(
            con.read_csv(f, na_values=["NULL", r"\N", ""], **READ_CSV_ARGS[fmt])
        ) as input_table,  # noqa: F841
    ):
        pb.set_postfix(
            {
                "rows": con.table("tripdata").count("*").fetchone()[0],
                "file": PurePath(zi.filename).name,
            }
        )
        con.sql(SQL_TEMPLATES[fmt])


if __name__ == "__main__":
    main()
