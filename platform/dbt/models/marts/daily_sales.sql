{{ config(materialized='table') }}

select
    md5(orders.order_date_key::text || '|' || orders.currency) as daily_sales_key,
    orders.order_date_key as sales_date,
    orders.currency,
    count(*) as order_count,
    count(distinct orders.customer_key) as purchasing_customer_count,
    sum(orders.merchandise_subtotal) as merchandise_subtotal,
    sum(orders.order_discount_amount) as order_discount_amount,
    sum(orders.shipping_amount) as shipping_amount,
    sum(orders.tax_amount) as tax_amount,
    sum(orders.order_total_amount) as order_total_amount,
    avg(orders.order_total_amount) as average_order_value
from {{ ref('fct_orders') }} as orders
where orders.order_status = 'delivered'
group by
    orders.order_date_key,
    orders.currency
