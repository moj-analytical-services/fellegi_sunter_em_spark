import pandas as pd
import pytest

import splink.duckdb.duckdb_comparison_template_library as ctld
import splink.spark.spark_comparison_template_library as ctls
from splink.duckdb.duckdb_linker import DuckDBLinker
from splink.spark.spark_linker import SparkLinker

## date_comparison


@pytest.mark.parametrize(
    ("ctl"),
    [
        pytest.param(ctld, id="DuckDB Date Comparison Simple Run Test"),
        pytest.param(ctls, id="Spark Date Comparison Simple Run Test"),
    ],
)
def test_date_comparison_run(ctl):
    ctl.date_comparison("date")


@pytest.mark.parametrize(
    ("ctl"),
    [
        pytest.param(ctld, id="DuckDB Date Comparison Levenshtein Test"),
        pytest.param(ctls, id="Spark Date Comparison Levenshtein Test"),
    ],
)
def test_date_comparison_dl_run(ctl):
    ctl.date_comparison(
        "date", levenshtein_thresholds=[1], damerau_levenshtein_thresholds=[]
    )


@pytest.mark.parametrize(
    ("ctl", "Linker"),
    [
        pytest.param(ctld, DuckDBLinker, id="DuckDB Date Comparison Integration Tests"),
        pytest.param(ctls, SparkLinker, id="Spark Date Comparison Integration Tests"),
    ],
)
def test_datediff_levels(spark, ctl, Linker):
    df = pd.DataFrame(
        [
            {
                "unique_id": 1,
                "first_name": "Tom",
                "dob": "2000-01-01",
            },
            {
                "unique_id": 2,
                "first_name": "Robin",
                "dob": "2000-01-20",
            },
            {
                "unique_id": 3,
                "first_name": "Zoe",
                "dob": "1995-09-30",
            },
            {
                "unique_id": 4,
                "first_name": "Sam",
                "dob": "1966-07-30",
            },
            {
                "unique_id": 5,
                "first_name": "Andy",
                "dob": "1996-03-25",
            },
            {
                "unique_id": 6,
                "first_name": "Andy's Twin",
                "dob": "1996-03-25",
            },
            {
                "unique_id": 7,
                "first_name": "Alice",
                "dob": "1999-12-28",
            },
            {
                "unique_id": 8,
                "first_name": "Afua",
                "dob": "2000-01-01",
            },
            {
                "unique_id": 9,
                "first_name": "Ross",
                "dob": "2000-10-20",
            },
        ]
    )

    # Generate our various settings objs
    settings = {
        "link_type": "dedupe_only",
        "comparisons": [ctl.date_comparison("dob", cast_strings_to_date=True)],
    }

    # We need to put our column in datetime format for this to work

    if Linker == SparkLinker:
        df = spark.createDataFrame(df)
        df.persist()
    linker = Linker(df, settings)
    linker_output = linker.predict().as_pandas_dataframe()

    # # Dict key: {gamma_level value: size}
    size_gamma_lookup = {0: 8, 1: 15, 2: 5, 3: 5, 4: 1, 5: 2}

    # Check gamma sizes are as expected
    for gamma, expected_size in size_gamma_lookup.items():
        print(f"gamma={gamma} and gamma_lookup={expected_size}")
        assert sum(linker_output["gamma_dob"] == gamma) == expected_size

    # Check individual IDs are assigned to the correct gamma values
    # Dict key: {gamma_value: tuple of ID pairs}
    size_gamma_lookup = {
        5: [[1, 8]],
        4: [(2, 9)],
        3: [(7, 8)],
        2: [(1, 9)],
        1: [(3, 7)],
        0: [(1, 4)],
    }

    for gamma, id_pairs in size_gamma_lookup.items():
        for left, right in id_pairs:
            print(f"Checking IDs: {left}, {right}")

            assert (
                linker_output.loc[
                    (linker_output.unique_id_l == left)
                    & (linker_output.unique_id_r == right)
                ]["gamma_dob"].values[0]
                == gamma
            )


@pytest.mark.parametrize(
    ("ctl"),
    [
        pytest.param(ctld, id="DuckDB Datediff Error Checks"),
        pytest.param(ctls, id="Spark Datediff Error Checks"),
    ],
)
def test_date_comparison_error_logger(ctl):
    # Differing lengths between thresholds and units
    with pytest.raises(ValueError):
        ctl.date_comparison(
            "date", datediff_thresholds=[1, 2], datediff_metrics=["month"]
        )
    # Check metric and threshold are the correct way around
    with pytest.raises(ValueError):
        ctld.date_comparison(
            "date", datediff_thresholds=["month"], datediff_metrics=[1]
        )
    # Invalid metric
    with pytest.raises(ValueError):
        ctl.date_comparison("date", datediff_thresholds=[1], datediff_metrics=["dy"])
    # Threshold len == 0
    with pytest.raises(ValueError):
        ctl.date_comparison("date", datediff_thresholds=[], datediff_metrics=["day"])
    # Metric len == 0
    with pytest.raises(ValueError):
        ctl.date_comparison("date", datediff_thresholds=[1], datediff_metrics=[])


## name_comparison


@pytest.mark.parametrize(
    ("ctl"),
    [
        pytest.param(ctld, id="DuckDB Name Comparison Simple Run Test"),
        pytest.param(ctls, id="Spark Name Comparison Simple Run Test"),
    ],
)
def test_name_comparison_run(ctl):
    ctl.name_comparison("first_name")


@pytest.mark.parametrize(
    ("ctl", "Linker"),
    [
        pytest.param(ctld, DuckDBLinker, id="DuckDB Name Comparison Integration Tests"),
        pytest.param(ctls, SparkLinker, id="Spark Name Comparison Integration Tests"),
    ],
)
def test_name_comparison_levels(spark, ctl, Linker):
    df = pd.DataFrame(
        [
            {
                "unique_id": 1,
                "first_name": "Robert",
                "first_name_metaphone": "RBRT",
                "dob": "1996-03-25",
            },
            {
                "unique_id": 2,
                "first_name": "Rob",
                "first_name_metaphone": "RB",
                "dob": "1996-03-25",
            },
            {
                "unique_id": 3,
                "first_name": "Robbie",
                "first_name_metaphone": "RB",
                "dob": "1999-12-28",
            },
            {
                "unique_id": 4,
                "first_name": "Bobert",
                "first_name_metaphone": "BB",
                "dob": "2000-01-01",
            },
            {
                "unique_id": 5,
                "first_name": "Bobby",
                "first_name_metaphone": "BB",
                "dob": "2000-10-20",
            },
            {
                "unique_id": 6,
                "first_name": "Robert",
                "first_name_metaphone": "RBRT",
                "dob": "1996-03-25",
            },
        ]
    )

    settings = {
        "link_type": "dedupe_only",
        "comparisons": [
            ctl.name_comparison(
                "first_name",
                phonetic_col_name="first_name_metaphone",
            )
        ],
    }

    if Linker == SparkLinker:
        df = spark.createDataFrame(df)
        df.persist()
    linker = Linker(df, settings)
    linker_output = linker.predict().as_pandas_dataframe()

    # # Dict key: {gamma_level value: size}
    size_gamma_lookup = {0: 6, 1: 4, 2: 0, 3: 2, 4: 2, 5: 1}
    # 5: exact_match
    # 4: dmetaphone exact match
    # 3: damerau_levenshtein <= 1
    # 2: jaro_winkler > 0.9
    # 1: jaro_winkler > 0.8
    # 0: else

    # Check gamma sizes are as expected
    for gamma, expected_size in size_gamma_lookup.items():
        print(f"gamma={gamma} and gamma_lookup={expected_size}")

        assert (
            sum(linker_output["gamma_custom_first_name_first_name_metaphone"] == gamma)
            == expected_size
        )

    # Check individual IDs are assigned to the correct gamma values
    # Dict key: {gamma_value: tuple of ID pairs}
    size_gamma_lookup = {
        5: [[1, 6]],
        4: [(2, 3), (4, 5)],
        3: [(4, 6)],
        2: [],
        1: [(1, 2), (2, 6)],
        0: [(2, 4), (5, 6)],
    }

    for gamma, id_pairs in size_gamma_lookup.items():
        for left, right in id_pairs:
            print(f"Checking IDs: {left}, {right}")

            assert (
                linker_output.loc[
                    (linker_output.unique_id_l == left)
                    & (linker_output.unique_id_r == right)
                ]["gamma_custom_first_name_first_name_metaphone"].values[0]
                == gamma
            )


@pytest.mark.parametrize(
    ("ctl"),
    [
        pytest.param(ctld, id="DuckDB Forename Surname Comparison Simple Run Test"),
        pytest.param(ctls, id="Spark Forename Surname Comparison Simple Run Test"),
    ],
)
def test_forename_surname_comparison_run(ctl):
    ctl.forename_surname_comparison("first_name", "surname")


## forename_surname_comparison


@pytest.mark.parametrize(
    ("ctl", "Linker"),
    [
        pytest.param(
            ctld,
            DuckDBLinker,
            id="DuckDB Forename Surname Comparison Integration Tests",
        ),
        pytest.param(
            ctls, SparkLinker, id="Spark Forename Surname Comparison Integration Tests"
        ),
    ],
)
def test_forename_surname_comparison_levels(spark, ctl, Linker):
    df = pd.DataFrame(
        [
            {
                "unique_id": 1,
                "forename": "Robert",
                "surname": "Smith",
            },
            {
                "unique_id": 2,
                "forename": "Robert",
                "surname": "Smith",
            },
            {
                "unique_id": 3,
                "forename": "Smith",
                "surname": "Robert",
            },
            {
                "unique_id": 4,
                "forename": "Bobert",
                "surname": "Franks",
            },
            {
                "unique_id": 5,
                "forename": "Bobby",
                "surname": "Smith",
            },
            {
                "unique_id": 6,
                "forename": "Robert",
                "surname": "Jones",
            },
            {
                "unique_id": 7,
                "forename": "James",
                "surname": "Smyth",
            },
        ]
    )

    settings = {
        "link_type": "dedupe_only",
        "comparisons": [ctl.forename_surname_comparison("forename", "surname")],
    }

    if Linker == SparkLinker:
        df = spark.createDataFrame(df)
        df.persist()
    linker = Linker(df, settings)
    linker_output = linker.predict().as_pandas_dataframe()

    # # Dict key: {gamma_level value: size}
    size_gamma_lookup = {0: 8, 1: 3, 2: 3, 3: 2, 4: 2, 5: 2, 6: 1}
    # 6: exact_match
    # 5: reversed_cols
    # 4: surname match
    # 3: forename match
    # 2: surname jaro_winkler > 0.88
    # 1: forename jaro_winkler > 0.88
    # 0: else

    # Check gamma sizes are as expected
    for gamma, expected_size in size_gamma_lookup.items():
        print(f"gamma={gamma} and gamma_lookup={expected_size}")
        gamma_matches = linker_output.filter(like="gamma_custom") == gamma
        gamma_matches_size = gamma_matches.sum().values[0]
        assert gamma_matches_size == expected_size

    # Check individual IDs are assigned to the correct gamma values
    # Dict key: {gamma_value: tuple of ID pairs}
    size_gamma_lookup = {
        6: [(1, 2)],
        5: [(2, 3)],
        4: [(2, 5)],
        3: [(1, 6)],
        2: [(5, 7)],
        1: [(1, 4), (4, 6)],
        0: [(3, 4), (6, 7)],
    }
    print(linker_output)
    for gamma, id_pairs in size_gamma_lookup.items():
        for left, right in id_pairs:
            print(f"Checking IDs: {left}, {right}")

            assert (
                linker_output.loc[
                    (linker_output.unique_id_l == left)
                    & (linker_output.unique_id_r == right)
                ]
                .filter(like="gamma_custom")
                .values[0][0]
                == gamma
            )


# postcode_comparison


@pytest.mark.parametrize(
    ("ctl", "Linker"),
    [
        pytest.param(ctld, DuckDBLinker, id="DuckDB Postcode Comparison Template Test"),
        pytest.param(ctls, SparkLinker, id="Spark Postcode Comparison Template Test"),
    ],
)
def test_postcode_comparison_levels(spark, ctl, Linker):
    df = pd.DataFrame(
        [
            {
                "unique_id": 1,
                "first_name": "Andy",
                "postcode": "SE1P 0NY",
                "lat": 53.95,
                "long": -1.08,
            },
            {
                "unique_id": 2,
                "first_name": "Andy's twin",
                "postcode": "SE1P 0NY",
                "lat": 53.95,
                "long": -1.08,
            },
            {
                "unique_id": 3,
                "first_name": "Tom",
                "postcode": "SE1P 0PZ",
                "lat": 53.95,
                "long": -1.08,
            },
            {
                "unique_id": 4,
                "first_name": "Robin",
                "postcode": "SE1P 4UY",
                "lat": 53.95,
                "long": -1.08,
            },
            {
                "unique_id": 5,
                "first_name": "Sam",
                "postcode": "SE2 7TR",
                "lat": 53.95,
                "long": -1.08,
            },
            {
                "unique_id": 6,
                "first_name": "Zoe",
                "postcode": "sw15 8uy",
                "lat": 53.95,
                "long": -1.08,
            },
        ]
    )

    # Generate our various settings objs
    settings = {
        "link_type": "dedupe_only",
        "comparisons": [
            ctl.postcode_comparison(
                "postcode",
                lat_col="lat",
                long_col="long",
                km_thresholds=5,
            )
        ],
    }

    if Linker == SparkLinker:
        df = spark.createDataFrame(df)
        df.persist()
    linker = Linker(df, settings)
    linker_output = linker.predict().as_pandas_dataframe()

    # Check individual IDs are assigned to the correct gamma values
    # Dict key: {gamma_level: tuple of ID pairs}
    size_gamma_lookup = {
        5: [(1, 2)],
        4: [(1, 3), (2, 3)],
        3: [(1, 4), (2, 4), (3, 4)],
        2: [(1, 5), (2, 5), (3, 5), (4, 5)],
        1: [(1, 6), (2, 6), (3, 6), (4, 6), (5, 6)],
    }

    for gamma, id_pairs in size_gamma_lookup.items():
        for left, right in id_pairs:
            print(f"Checking IDs: {left}, {right}")
            assert (
                linker_output.loc[
                    (linker_output.unique_id_l == left)
                    & (linker_output.unique_id_r == right)
                ]["gamma_postcode"].values[0]
                == gamma
            )
