import argparse
import contextlib
import csv
import io
import logging
from collections.abc import Callable
from functools import partial
from importlib.resources import files
from os import PathLike
from pathlib import Path, PurePath
from typing import Iterable, Tuple, IO
from zipfile import ZipFile, ZipInfo

import duckdb
from duckdb import DuckDBPyConnection, connect
from tqdm import tqdm
from tqdm.contrib.logging import tqdm_logging_redirect

from citibike_extractor.constants import FORMATS_BY_HEADER, SQL_TEMPLATES, READ_CSV_ARGS

LOG = logging.getLogger(__name__)

BARE_CSV = "*.csv"
ONE_LEVEL_NESTED_CSV = "*-citibike-tripdata/*.csv"

CAN_HAVE_TWO_LEVEL_NESTED_CSV = "**/201[4-79]-citibike-tripdata.zip"
TWO_LEVEL_NESTED_CSV = "*-citibike-tripdata/*/*.csv"

NESTED_ZIP = "*/*.zip"

IGNORE_FILES = "2018-citibike-tripdata/201804-citibike-tripdata_[12].csv"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        choices=[v for (k, v) in logging._levelToName.items() if k != logging.NOTSET],
        type=str.upper,
        help="Set logging level (default: INFO)",
    )

    parser.add_argument(
        "output_database", type=Path, help="Path to output DuckDB database"
    )
    parser.add_argument("input_files", nargs="*", type=Path, help="Path to input files")

    args = parser.parse_args()

    LOG.setLevel(args.log_level)

    output_database: Path = args.output_database
    input_files: Iterable[Path] = args.input_files

    with connect(
        output_database, config={"storage_compatibility_version": "latest"}
    ) as con:
        con.sql("INSTALL spatial")
        con.sql("LOAD spatial")
        con.sql((files("citibike_extractor.templates") / "schema.sql").read_text())

        with tqdm_logging_redirect(
            sorted(input_files, key=lambda f: f.name), unit="archive"
        ) as pb:
            handler = partial(handle_csv_file, con, pb)

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


def b(v: bool):
    return "✅" if v else "❎"


def is_valid_csv(input_file: PurePath, p: PurePath):
    """
    Test if a pathname in a Zip archive is a 'valid' CSV file.

    Valid CSV files are those which can be ingested without fear of causing
    duplicates. This includes all bare CSV files (in the root of the archive)
    and those nested one level deep in a folder.

    In some cases, CSV files nested two levels deep are permitted, but this is
    gated on the name of the enclosing Zip archive.

    Certain files are not to be imported even if they match one of the preceding
    rules.
    """

    bare_csv = p.full_match(BARE_CSV)
    one_level_nested_csv = p.full_match(ONE_LEVEL_NESTED_CSV)

    can_have_two_level_nested_csv = input_file.full_match(CAN_HAVE_TWO_LEVEL_NESTED_CSV)
    two_level_nested_csv = p.full_match(TWO_LEVEL_NESTED_CSV)

    is_ignored = p.full_match(IGNORE_FILES)

    LOG.debug(
        "%s %s %s %s %s\t%s\t\t%s",
        *map(
            b,
            (
                bare_csv,
                one_level_nested_csv,
                can_have_two_level_nested_csv,
                two_level_nested_csv,
                is_ignored,
            ),
        ),
        input_file.name,
        p,
    )

    return (
        bare_csv
        or one_level_nested_csv
        or (can_have_two_level_nested_csv and two_level_nested_csv)
    ) and not is_ignored


def handle_zip_file(
    input_file: str | PathLike[str] | IO[bytes],
    operations: Iterable[
        Tuple[Callable[[PurePath], bool], Callable[[ZipFile, ZipInfo], None]]
    ],
):
    with ZipFile(input_file, "r") as zf:
        for zi in sorted(zf.infolist(), key=lambda f: f.filename):
            p = PurePath(zi.filename)

            for entry_test, handler in operations:
                if entry_test(p):
                    handler(zf, zi)


def handle_nested_zip(
    csv_handler: Callable[[ZipFile, ZipInfo], None], zf: ZipFile, zi: ZipInfo
):
    with zf.open(zi) as nz:
        handle_zip_file(
            nz,
            (
                (
                    lambda p: p.full_match(BARE_CSV),
                    csv_handler,
                ),
            ),
        )


def handle_csv_file(con: DuckDBPyConnection, pb: tqdm, zf: ZipFile, zi: ZipInfo):
    with zf.open(zi) as f, io.TextIOWrapper(f) as w:
        cr = csv.reader(w)
        header_row = next(cr)

        fmt = FORMATS_BY_HEADER[tuple(header_row)]

    with (
        zf.open(zi) as f,
        contextlib.closing(
            con.read_csv(f, na_values=["NULL", r"\N", ""], **READ_CSV_ARGS[fmt])
        ) as raw_input_table,
    ):
        archive_filename = PurePath(zf.filename).name
        entry_filename = PurePath(zi.filename).name

        input_table = raw_input_table.project(  # noqa: F841
            duckdb.StarExpression(),
            duckdb.ConstantExpression(archive_filename).alias("archive"),
            duckdb.ConstantExpression(entry_filename).alias("filename"),
        )

        pb.set_postfix(
            {
                "rows": con.table("tripdata").count("*").fetchone()[0],
                "file": entry_filename,
            }
        )

        con.sql(SQL_TEMPLATES[fmt])


if __name__ == "__main__":
    main()
