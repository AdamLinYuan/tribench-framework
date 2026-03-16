"""
Remap standard TPC-H queries (prefixed column names) to Trino built-in
tpch connector naming (unprefixed, using table aliases for disambiguation).

Standard TPC-H:   l_shipdate, p_partkey, s_suppkey, ...
Trino built-in:   l.shipdate,  p.partkey,  s.suppkey, ... (via table alias)
"""
import re
import os
import glob

# Table name -> short alias
TABLE_TO_ALIAS = {
    "partsupp": "ps",
    "lineitem":  "l",
    "orders":    "o",
    "customer":  "c",
    "supplier":  "s",
    "part":      "p",
    "nation":    "n",
    "region":    "r",
}

# Column prefix -> alias  (ps_ first to beat p_ and s_)
PREFIX_REPLACEMENTS = [
    ("ps_", "ps"),
    ("l_",  "l"),
    ("o_",  "o"),
    ("c_",  "c"),
    ("s_",  "s"),
    ("p_",  "p"),
    ("n_",  "n"),
    ("r_",  "r"),
]


def replace_prefixed_columns(sql: str) -> str:
    """Replace prefix_col → alias.col using word-boundary regex."""
    for prefix, alias in PREFIX_REPLACEMENTS:
        sql = re.sub(
            r"\b" + re.escape(prefix) + r"(\w+)",
            alias + r".\1",
            sql,
        )
    return sql


def add_table_aliases(sql: str) -> str:
    """
    Add a short alias after bare table names that don't already have one.
    Works for comma-style FROM lists and JOIN syntax.
    """
    # Tables sorted longest-first to avoid partial matches (partsupp before part)
    tables_sorted = sorted(TABLE_TO_ALIAS.keys(), key=len, reverse=True)
    pattern = r"\b(" + "|".join(re.escape(t) for t in tables_sorted) + r")\b"

    def replacer(m):
        tbl = m.group(1).lower()
        alias = TABLE_TO_ALIAS[tbl]
        # Look ahead: if immediately followed by the alias or another word char, skip
        return m.group(0)

    # Simple approach: replace 'tablename' with 'tablename alias' where not already aliased
    for tbl, alias in sorted(TABLE_TO_ALIAS.items(), key=lambda x: -len(x[0])):
        # Match table name NOT immediately followed by its alias or another identifier
        sql = re.sub(
            r"\b" + re.escape(tbl) + r"\b(?!\s+" + re.escape(alias) + r"\b)(?=\s*[,\s])",
            tbl + " " + alias,
            sql,
            flags=re.IGNORECASE,
        )
    return sql


def transform_query(sql: str) -> str:
    sql = add_table_aliases(sql)
    sql = replace_prefixed_columns(sql)
    return sql


if __name__ == "__main__":
    src_dir = "queries/tpch/queries"
    dst_dir = "queries/tpch/queries-short"
    os.makedirs(dst_dir, exist_ok=True)

    for src_path in sorted(glob.glob(os.path.join(src_dir, "q*.sql"))):
        text = open(src_path).read()
        out_text = transform_query(text)
        fname = os.path.basename(src_path)
        dst_path = os.path.join(dst_dir, fname)
        open(dst_path, "w").write(out_text)
        print(f"  {fname}")

    print("Done.")
