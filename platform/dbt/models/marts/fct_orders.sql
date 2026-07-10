{{ config(materialized='table') }}

select
    orders.order_id,
    customers.customer_id as customer_key,
    orders.order_ts::date as order_date_key,
    orders.order_ts as ordered_at,
    orders.order_status,
    orders.subtotal as merchandise_subtotal,
    orders.discount_amount as order_discount_amount,
    orders.shipping_amount,
    orders.tax_amount,
    orders.total_amount as order_total_amount,
    orders.currency,
    1 as order_count
from {{ ref('stg_orders') }} as orders
inner join {{ ref('stg_customers') }} as customers
    on orders.customer_id = customers.customer_id
