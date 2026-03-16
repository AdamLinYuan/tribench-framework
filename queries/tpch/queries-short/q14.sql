-- TPC-H Q14

SELECT
    100.00 * SUM(CASE
        WHEN p.type LIKE 'PROMO%'
        THEN l.extendedprice * (1 - l.discount)
        ELSE 0
    END) / SUM(l.extendedprice * (1 - l.discount)) AS promo_revenue
FROM
    lineitem l,
    part p
WHERE
    l.partkey = p.partkey
    AND l.shipdate >= DATE '1995-09-01'
    AND l.shipdate < DATE '1995-10-01'
