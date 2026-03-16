-- TPC-H Q01
SELECT
    l.returnflag,
    l.linestatus,
    SUM(l.quantity) AS sum_qty,
    SUM(l.extendedprice) AS sum_base_price,
    SUM(l.extendedprice * (1 - l.discount)) AS sum_disc_price,
    SUM(l.extendedprice * (1 - l.discount) * (1 + l.tax)) AS sum_charge,
    AVG(l.quantity) AS avg_qty,
    AVG(l.extendedprice) AS avg_price,
    AVG(l.discount) AS avg_disc,
    COUNT(*) AS count_order
FROM
    lineitem l
WHERE
    l.shipdate <= DATE '1998-09-02'
GROUP BY
    l.returnflag,
    l.linestatus
ORDER BY
    l.returnflag,
    l.linestatus
