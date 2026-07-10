{{ config(materialized='table') }}

select
    order_items.order_item_id,
    order_items.order_id,
    products.product_id as product_key,
    order_items.quantity,
    order_items.unit_price as unit_selling_price,
    order_items.discount_amount as line_discount_amount,
    order_items.line_total as line_total_amount
from {{ ref('stg_order_items') }} as order_items
inner join {{ ref('stg_products') }} as products
    on order_items.product_id = products.product_id
