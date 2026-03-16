-- TPC-H Q15: Top supplier s Query
--
-- This query determines the top supplier s based on revenue generated
-- from parts shipped during a specific quarter. It uses a Common Table
-- Expression (CTE) instead of a view for better compatibility.
--
-- Expected result: Variable (depends on data, but typically 1-5 suppliers)

with revenue0 as (
  select
    l.suppkey as supplier_no,
    sum(l.extendedprice * (1 - l.discount)) as total_revenue
  from
    lineitem l
  where
    l.shipdate >= date '1996-01-01'
    and l.shipdate < date '1996-01-01' + interval '3' month
  group by
    l.suppkey
)
select
  s.suppkey,
  s.name,
  s.address,
  s.phone,
  total_revenue
from
  supplier s,
  revenue0
where
  s.suppkey = supplier_no
  and total_revenue = (
    select
      max(total_revenue)
    from
      revenue0
  )
order by
  s.suppkey