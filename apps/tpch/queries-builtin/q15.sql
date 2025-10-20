-- TPC-H Q15: Top Supplier Query (Builtin TPC-H Catalog Version)
--
-- This query determines the top supplier based on revenue generated
-- from parts shipped during a specific quarter.
-- Uses UNPREFIXED column names for Trino's built-in TPC-H catalog.
--
-- Expected result: Variable (typically 1-5 suppliers with max revenue)

WITH revenue0 AS (
  SELECT
    suppkey AS supplier_no,
    SUM(extendedprice * (1 - discount)) AS total_revenue
  FROM
    lineitem
  WHERE
    shipdate >= DATE '1996-01-01'
    AND shipdate < DATE '1996-01-01' + INTERVAL '3' MONTH
  GROUP BY
    suppkey
)
SELECT
  s.suppkey,
  s.name,
  s.address,
  s.phone,
  total_revenue
FROM
  supplier s,
  revenue0
WHERE
  s.suppkey = supplier_no
  AND total_revenue = (
    SELECT
      MAX(total_revenue)
    FROM
      revenue0
  )
ORDER BY
  s.suppkey
