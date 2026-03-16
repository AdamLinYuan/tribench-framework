-- TPC-H Q13
select c.count, count(*) as custdist
from (
    select
        c.custkey,
        count(o.orderkey) as c.count
    from
        customer c left outer join orders o on
            c.custkey = o.custkey
            and o.comment not like '%special%requests%'
    group by  
        c.custkey
    ) as c.orders
group by  
    c.count
order by
    custdist desc,
    c.count desc