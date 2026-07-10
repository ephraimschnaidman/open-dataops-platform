{{ config(materialized='table') }}

with delivered_order_items as (
    select
        order_items.order_item_id,
        order_items.product_key,
        order_items.order_id,
        order_items.quantity,
        order_items.line_discount_amount,
        order_items.line_total_amount
    from {{ ref('fct_order_items') }} as order_items
    inner join {{ ref('fct_orders') }} as orders
        on order_items.order_id = orders.order_id
    where orders.order_status = 'delivered'
)

select
    products.product_key,
    products.product_id,
    products.sku,
    products.product_name,
    products.product_category,
    products.product_brand,
    count(distinct order_items.order_id) as order_count,
    coalesce(sum(order_items.quantity), 0) as units_sold,
    coalesce(sum(order_items.line_discount_amount), 0) as line_discount_amount,
    coalesce(sum(order_items.line_total_amount), 0) as merchandise_revenue
from {{ ref('dim_products') }} as products
left join delivered_order_items as order_items
    on products.product_key = order_items.product_key
group by
    products.product_key,
    products.product_id,
    products.sku,
    products.product_name,
    products.product_category,
    products.product_brand
