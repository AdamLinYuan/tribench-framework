-- TPC-H Q1: Pricing Summary Report Query (Builtin TPC-H Catalog Version)
--
-- This query reports the amount of business billed, shipped, and returned.
-- Uses UNPREFIXED column names for Trino's built-in TPC-H catalog.
--
-- Expected result: 4 rows (returnflag × linestatus combinations)

SELECT
    returnflag,
    linestatus,
    SUM(quantity) AS sum_qty,
    SUM(extendedprice) AS sum_base_price,
    SUM(extendedprice * (1 - discount)) AS sum_disc_price,
    SUM(extendedprice * (1 - discount) * (1 + tax)) AS sum_charge,
    AVG(quantity) AS avg_qty,
    AVG(extendedprice) AS avg_price,
    AVG(discount) AS avg_disc,
    COUNT(*) AS count_order
FROM
    lineitem
WHERE
    shipdate <= DATE '1998-12-01' - INTERVAL '90' DAY
GROUP BY
    returnflag,
    linestatus
ORDER BY
    returnflag,
    linestatus
