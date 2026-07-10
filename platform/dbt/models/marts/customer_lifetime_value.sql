{{ config(materialized='table') }}

select
    customers.customer_key,
    customers.customer_id,
    customers.customer_created_date,
    customers.country,
    customers.region,
    count(orders.order_id) as lifetime_order_count,
    coalesce(sum(orders.order_total_amount), 0) as lifetime_order_value,
    coalesce(avg(orders.order_total_amount), 0) as lifetime_average_order_value,
    min(orders.ordered_at) as first_ordered_at,
    max(orders.ordered_at) as most_recent_ordered_at
from {{ ref('dim_customers') }} as customers
left join {{ ref('fct_orders') }} as orders
    on customers.customer_key = orders.customer_key
    and orders.order_status = 'delivered'
group by
    customers.customer_key,
    customers.customer_id,
    customers.customer_created_date,
    customers.country,
    customers.region
