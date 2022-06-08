import pytest
from pyspark.sql import functions as f

from splink_data_generation.generate_data_random import generate_df_gammas_random
from splink_data_generation.match_prob import add_match_prob
from splink.default_settings import complete_settings_dict
from splink.iterate import iterate
from splink.model import Model
from copy import deepcopy


def _probabilities_from_freqs(freqs, m_gamma_0=0.05):
    """Very roughly come up with some plausible u probabilities
    for given frequencies

    if true input nodes were [john,john,john,matt,matt,robin]
    then freqs would be [3,2,1]

    For johns, there are 9 comparisons and 3 matches
    For matts, there are 4 comparisons and 2 matches
    For robins there is  1 comparison and 1 match
    """

    # m probabilities
    m_probs = [f / sum(freqs) for f in freqs]
    adj = 1 - m_gamma_0
    m_probs = [f * adj for f in m_probs]
    m_probs.insert(0, m_gamma_0)

    # Amongst truly non-matching records, what's the probability you observe a match on john?
    # 36 possibilities
    #   9/36 are john
    #   4/36 are matt
    #   1/36 are robin
    #   22/36 do not match

    sum_freqs_sq = sum(freqs) ** 2
    u_probs = [f**2 / sum_freqs_sq for f in freqs]
    remainder = 1 - sum(u_probs)
    u_probs.insert(0, remainder)

    return {
        "m_probabilities": m_probs,
        "u_probabilities": u_probs,
    }


def test_term_frequency_adjustments(spark):

    # The strategy is going to be to create a fake dataframe
    # where we have different levels to model frequency imbalance
    # gamma=3 is where name matches and name is robin (unusual name)
    # gamma=2 is where name matches and name is matt (normal name)
    # gamma=1 is where name matches and name is john (v common name)

    # We simulate the term frequency imbalance
    # by pooling this together, setting all gamma >0
    # to equal 1

    # We then expect that
    # term frequency adjustments should adjust up the
    # robins but adjust down the johns

    # We also expect that the tf adjusted match probability should be more accurate

    forename_probs = _probabilities_from_freqs([3, 2, 1])
    surname_probs = _probabilities_from_freqs([10, 5, 1])

    from pyspark.sql.functions import col, create_map, lit
    from itertools import chain

    tf_forename = {"Robin": 1 / 6, "Matt": 2 / 6, "John": 3 / 6}
    tf_surname = {"Linacre": 1 / 16, "Hughes": 5 / 16, "Smith": 10 / 16}

    forename_mapping = create_map([lit(x) for x in chain(*tf_forename.items())])
    surname_mapping = create_map([lit(x) for x in chain(*tf_surname.items())])

    settings_true = {
        "link_type": "dedupe_only",
        "proportion_of_matches": 0.5,
        "comparison_columns": [
            {
                "col_name": "forename",
                "term_frequency_adjustments": True,
                "m_probabilities": forename_probs["m_probabilities"],
                "u_probabilities": forename_probs["u_probabilities"],
                "num_levels": 4,
            },
            {
                "col_name": "surname",
                "term_frequency_adjustments": True,
                "m_probabilities": surname_probs["m_probabilities"],
                "u_probabilities": surname_probs["u_probabilities"],
                "num_levels": 4,
            },
            {
                "col_name": "cat_20",
                "m_probabilities": [0.2, 0.8],
                "u_probabilities": [19 / 20, 1 / 20],
            },
        ],
    }

    settings_true = complete_settings_dict(settings_true, spark)

    df = generate_df_gammas_random(10000, settings_true)

    # Create new binary columns that binarise the more granular gammas to 0 and 1
    df["gamma_forename_binary"] = df["gamma_forename"].where(
        df["gamma_forename"] == 0, 1
    )

    df["gamma_surname_binary"] = df["gamma_surname"].where(df["gamma_surname"] == 0, 1)

    # Populate non matches with random value
    # Then assign left and right values ased on the gamma values
    df["forename_binary_l"] = df["unique_id_l"]
    df["forename_binary_r"] = df["unique_id_r"]

    f1 = df["gamma_forename"] == 3
    df.loc[f1, "forename_binary_l"] = "Robin"
    df.loc[f1, "forename_binary_r"] = "Robin"

    f1 = df["gamma_forename"] == 2
    df.loc[f1, "forename_binary_l"] = "Matt"
    df.loc[f1, "forename_binary_r"] = "Matt"

    f1 = df["gamma_forename"] == 1
    df.loc[f1, "forename_binary_l"] = "John"
    df.loc[f1, "forename_binary_r"] = "John"

    # Populate non matches with random value
    df["surname_binary_l"] = df["unique_id_l"]
    df["surname_binary_r"] = df["unique_id_r"]

    f1 = df["gamma_surname"] == 3
    df.loc[f1, "surname_binary_l"] = "Linacre"
    df.loc[f1, "surname_binary_r"] = "Linacre"

    f1 = df["gamma_surname"] == 2
    df.loc[f1, "surname_binary_l"] = "Hughes"
    df.loc[f1, "surname_binary_r"] = "Hughes"

    f1 = df["gamma_surname"] == 1
    df.loc[f1, "surname_binary_l"] = "Smith"
    df.loc[f1, "surname_binary_r"] = "Smith"

    # cat20
    df["cat_20_l"] = df["unique_id_l"]
    df["cat_20_r"] = df["unique_id_r"]

    f1 = df["gamma_cat_20"] == 1
    df.loc[f1, "cat_20_l"] = "a"
    df.loc[f1, "cat_20_r"] = "a"

    df = add_match_prob(df, settings_true)
    df["match_probability"] = df["true_match_probability_l"]

    df_e_no_tf = spark.createDataFrame(df)
    df_e_tf = spark.createDataFrame(df)

    def four_to_two(probs):
        return [probs[0], sum(probs[1:])]

    settings_binary_tf = {
        "link_type": "dedupe_only",
        "proportion_of_matches": 0.5,
        "comparison_columns": [
            {
                "col_name": "forename_binary",
                "term_frequency_adjustments": True,
                "num_levels": 2,
                "m_probabilities": four_to_two(forename_probs["m_probabilities"]),
                "u_probabilities": four_to_two(forename_probs["u_probabilities"]),
            },
            {
                "col_name": "surname_binary",
                "term_frequency_adjustments": True,
                "num_levels": 2,
                "m_probabilities": four_to_two(surname_probs["m_probabilities"]),
                "u_probabilities": four_to_two(surname_probs["u_probabilities"]),
            },
            {
                "col_name": "cat_20",
                "m_probabilities": [0.2, 0.8],
                "u_probabilities": [19 / 20, 1 / 20],
            },
        ],
        "retain_intermediate_calculation_columns": True,
        "max_iterations": 0,
        "additional_columns_to_retain": ["true_match_probability"],
    }

    settings_binary_no_tf = deepcopy(settings_binary_tf)
    settings_binary_no_tf["comparison_columns"][0]["term_frequency_adjustments"] = False
    settings_binary_no_tf["comparison_columns"][1]["term_frequency_adjustments"] = False
    settings_binary_no_tf["comparison_columns"][2]["term_frequency_adjustments"] = False

    # Can't use linker = Splink() because we have df_gammas, not df
    settings_binary_tf = complete_settings_dict(settings_binary_tf, spark)
    model_tf = Model(settings_binary_tf, spark)

    settings_binary_no_tf = complete_settings_dict(settings_binary_no_tf, spark)
    model_no_tf = Model(settings_binary_no_tf, spark)

    # Need to populate term frequencies despite not having the underlying data
    # Note tfs of random data (names other than robin, matt john)
    # don't matter because they are never used
    df_e_tf = (
        df_e_tf.withColumn(
            "tf_forename_binary_l", forename_mapping[f.col("forename_binary_l")]
        )
        .withColumn(
            "tf_forename_binary_r", forename_mapping[f.col("forename_binary_r")]
        )
        .withColumn("tf_surname_binary_l", surname_mapping[f.col("surname_binary_l")])
        .withColumn("tf_surname_binary_r", surname_mapping[f.col("surname_binary_r")])
    )

    df_e_tf = df_e_tf.fillna(
        1,
        subset=[
            "tf_forename_binary_l",
            "tf_forename_binary_r",
            "tf_surname_binary_l",
            "tf_surname_binary_r",
        ],
    )

    df_e_tf = iterate(df_e_tf, model_tf, spark)

    df_tf = df_e_tf.toPandas()

    df_e_no_tf = (
        df_e_no_tf.withColumn(
            "tf_forename_binary_l", forename_mapping[f.col("forename_binary_l")]
        )
        .withColumn(
            "tf_forename_binary_r", forename_mapping[f.col("forename_binary_r")]
        )
        .withColumn("tf_surname_binary_l", surname_mapping[f.col("surname_binary_l")])
        .withColumn("tf_surname_binary_r", surname_mapping[f.col("surname_binary_r")])
    )

    df_e_no_tf = df_e_no_tf.fillna(
        1,
        subset=[
            "tf_forename_binary_l",
            "tf_forename_binary_r",
            "tf_surname_binary_l",
            "tf_surname_binary_r",
        ],
    )

    df_e_no_tf = iterate(df_e_no_tf, model_no_tf, spark)

    df_no_tf = df_e_no_tf.toPandas()

    #########
    # Tests start here
    #########

    # Test that overall square error is better for tf adjusted match prob
    df_no_tf["e1"] = (
        df_no_tf["match_probability"] - df_no_tf["true_match_probability_l"]
    ) ** 2
    df_tf["e2"] = (df_tf["match_probability"] - df_tf["true_match_probability_l"]) ** 2
    assert df_no_tf["e1"].sum() > df_tf["e2"].sum()

    # We expect Johns to be adjusted down...
    f1 = df_tf["forename_binary_l"] == "John"
    df_filtered = df_tf[f1]
    adj = df_filtered["bf_tf_adj_forename_binary"].mean()
    assert adj <= 1.0

    # And Robins to be adjusted up
    f1 = df_tf["forename_binary_l"] == "Robin"
    df_filtered = df_tf[f1]
    adj = df_filtered["bf_tf_adj_forename_binary"].mean()
    assert adj > 1.0

    # We expect Smiths to be adjusted down...
    f1 = df_tf["surname_binary_l"] == "Smith"
    df_filtered = df_tf[f1]
    adj = df_filtered["bf_tf_adj_surname_binary"].mean()
    assert adj < 1.0

    # And Linacres to be adjusted up
    f1 = df_tf["surname_binary_l"] == "Linacre"
    df_filtered = df_tf[f1]
    adj = df_filtered["bf_tf_adj_surname_binary"].mean()
    assert adj > 1.0

    # Check adjustments are applied correctly

    f1 = df_tf["forename_binary_l"] == "Robin"
    f2 = df_tf["surname_binary_l"] == "Linacre"
    df_filtered = df_tf[f1 & f2]
    row_tf = df_filtered.head(1).to_dict(orient="records")[0]

    f1 = df_no_tf["forename_binary_l"] == "Robin"
    f2 = df_no_tf["surname_binary_l"] == "Linacre"
    df_filtered = df_no_tf[f1 & f2]
    row_no_tf = df_filtered.head(1).to_dict(orient="records")[0]

    prior = row_no_tf["match_probability"]
    posterior = row_tf["match_probability"]

    b1 = row_tf["bf_tf_adj_forename_binary"]
    b2 = row_tf["bf_tf_adj_surname_binary"]

    expected_post_bf = (prior / (1 - prior)) * b1 * b2
    expected_post = expected_post_bf / (1 + expected_post_bf)
    assert posterior == pytest.approx(expected_post)

    #  We expect match probability to be equal to tf_adjusted match probability in cases where surname and forename don't match
    f1 = df_tf["surname_binary_l"] != df_tf["surname_binary_r"]
    f2 = df_tf["forename_binary_l"] != df_tf["forename_binary_r"]
    df_filtered_tf = df[f1 & f2]

    f1 = df_no_tf["surname_binary_l"] != df_no_tf["surname_binary_r"]
    f2 = df_no_tf["forename_binary_l"] != df_no_tf["forename_binary_r"]
    df_filtered_no_tf = df[f1 & f2]

    sum_difference = (
        df_filtered_tf["match_probability"] - df_filtered_no_tf["match_probability"]
    ).sum()

    assert 0 == pytest.approx(sum_difference)
