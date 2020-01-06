# https://github.com/moj-analytical-services/sparklink/issues/17

# This first implementation enables term freq adjustments to be made for just a single column
# However, it's designed to be flexible enough to accomodate multiple columns later i.e. shouldn't
# need to be re-written from scratch, just extended.

# ----

# Input is the final df_e and params after all iterations have completed
# Output is the match_probability_adjusted column.

def sql_gen_bayes_string(probs):
    """Convenience function for computing an updated probability using bayes' rule

    e.g. if probs = ['p1', 'p2', 0.3]

    return the sql expression 'p1*p2*0.3/(p1*p2*0.3 + (1-p1)*(1-p2)*(1-0.3))'

    Args:
        probs: Array of column names or constant values

    Returns:
        string: a sql expression
    """

    # Needed in case e.g. float constant value passed
    probs = [str(p) for p in probs]

    inverse_probs = [f"(1 - {p})" for p in probs]

    probs_multiplied = " * ".join(probs)
    inverse_probs_multiplied = " * ".join(inverse_probs)

    return f"""
    {probs_multiplied}/
    (  {probs_multiplied} + {inverse_probs_multiplied} )
    """


def sql_gen_generate_adjusted_lambda(column_name, params, table_name='df_e'):

    sql = f"""
    with temp_adj as
    (
    select {column_name}_l, {column_name}_r, sum(match_probability)/count(match_probability) as adj_lambda
    from {table_name}
    where {column_name}_l = {column_name}_r
    group by {column_name}_l, {column_name}_r
    )

    select {column_name}_l, {column_name}_r, {sql_gen_bayes_string(["adj_lambda", 1-params.params["λ"]])}
    as {column_name}_adjustment_nulls
    from temp_adj
    """

    return sql

def sql_gen_add_adjumentments_to_df_e(term_freq_column_list):

    coalesce_template = "coalesce({c}_adjustment_nulls, 0.5) as {c}_adjustment"
    coalesces =  [coalesce_template.format(c=c) for c in term_freq_column_list]
    coalesces = ",\n ".join(coalesces)

    left_join_template = """
     left join
    {c}_lookup
    on {c}_lookup.{c}_l = e.{c}_l
    and {c}_lookup.{c}_l = e.{c}_r
    """

    left_joins = [left_join_template.format(c=c) for c in term_freq_column_list]
    left_joins = "\n ".join(left_joins)


    sql = f"""
    select *, {coalesces}
    from df_e as e

    {left_joins}
    """

    return sql


def sql_gen_compute_final_group_membership_prob_from_adjustments(term_freq_column_list, table_name="df_e_adj"):

    term_freq_column_list = [c + "_adjustment" for c in term_freq_column_list]
    term_freq_column_list.insert(0, "match_probability")
    sql = f"""
    select *, {sql_gen_bayes_string(term_freq_column_list)} as final_group_memebership_prob
    from {table_name}
    """

    return sql