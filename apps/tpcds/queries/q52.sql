-- TPC-DS Query 52
-- Item sales by brand

SELECT
    dt.d_year,
    item.i_brand_id AS brand_id,
    item.i_brand AS brand,
    SUM(ss_ext_sales_price) AS ext_price
FROM date_dim dt, store_sales, item
WHERE d_date_sk = ss_sold_date_sk
  AND ss_item_sk = i_item_sk
  AND i_manager_id = 1
  AND d_moy = 12
  AND d_year = 2000
GROUP BY dt.d_year, item.i_brand, item.i_brand_id
ORDER BY dt.d_year, ext_price DESC, brand_id
LIMIT 100
