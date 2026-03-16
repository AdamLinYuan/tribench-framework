-- TPC-H Q11
select
  ps.partkey,
  sum(ps.supplycost * ps.availqty) as value
from
  partsupp ps,
  supplier s,
  nation n
where
  ps.suppkey = s.suppkey
  and s.nationkey = n.nationkey
  and n.name = 'GERMANY'
group by
  ps.partkey having
    sum(ps.supplycost * ps.availqty) > (
      select
        sum(ps.supplycost * ps.availqty) * 0.000001
      from
        partsupp ps,
        supplier s,
        nation n
      where
        ps.suppkey = s.suppkey
        and s.nationkey = n.nationkey
        and n.name = 'GERMANY'
    )   
order by
  value desc
