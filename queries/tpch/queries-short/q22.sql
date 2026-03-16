-- TPC-H Q22
select
  cntrycode,
  count(*) as numcust,
  sum(c.acctbal) as totacctbal
from
  (
    select
      substring(c.phone, 1, 2) as cntrycode,
      c.acctbal
    from
      customer c
    where
      substring(c.phone, 1, 2) in
        ('13', '31', '23', '29', '30', '18', '17')
      and c.acctbal > (
        select
          avg(c.acctbal)
        from
          customer c
        where
          c.acctbal > 0.00
          and substring(c.phone, 1, 2) in
            ('13', '31', '23', '29', '30', '18', '17')
      )   
      and not exists (
        select
          *
        from
          orders o
        where
          o.custkey = c.custkey
      )   
  ) as custsale
group by
  cntrycode
order by
  cntrycode