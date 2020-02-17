import pytest
import sqlite3
import pandas as pd

from sparklink.blocking import sql_gen_block_using_rules
from sparklink.settings import _get_columns_to_retain
from sparklink.gammas import complete_settings_dict

def data_into_table(data, table_name, con):
    cur = con.cursor()

    keys = data[0].keys()
    cols = ", ".join(keys)

    sql = f"""
    create table if not exists {table_name} ({cols})
    """

    cur.execute(sql)

    question_marks = ", ".join("?" for k in keys)
    insert_statement = f"insert into {table_name} values ({question_marks})"

    for d in data:
        values = tuple(d.values())
        cur.execute(insert_statement, values)


@pytest.fixture(scope='function')
def link_dedupe_data():

     # Create the database and the database table
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row

    data_l = [
    {"unique_id": 1, "surname": "Linacre", "first_name": "Robin"},
    {"unique_id": 2, "surname": "Smith", "first_name": "John"}
    ]

    data_into_table(data_l, "df_l", con)

    data_r = [
    {"unique_id": 7, "surname": "Linacre", "first_name": "Robin"},
    {"unique_id": 8, "surname": "Smith", "first_name": "John"},
    {"unique_id": 9, "surname": "Smith", "first_name": "Robin"}
    ]

    data_into_table(data_r, "df_r", con)

    yield con

def test_link_only(link_dedupe_data):

    settings = {
        "link_type": "link_only",
        "comparison_columns": [{"col_name": "first_name"},
                            {"col_name": "surname"}],
        "blocking_rules": [
            "l.first_name = r.first_name",
            "l.surname = r.surname"
        ]
    }
    settings = complete_settings_dict(settings)
    ctr = _get_columns_to_retain(settings)
    sql = sql_gen_block_using_rules("link_only", ctr, settings["blocking_rules"])
    df  = pd.read_sql(sql, link_dedupe_data)
    df = df.sort_values(["unique_id_l", "unique_id_r"])

    assert list(df["unique_id_l"]) == [1,1,2,2]
    assert list(df["unique_id_r"]) == [7,9,8,9]
