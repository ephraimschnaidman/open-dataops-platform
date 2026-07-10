select
    trim(order_item_id) as order_item_id,
    trim(order_id) as order_id,
    trim(product_id) as product_id,
    quantity::integer as quantity,
    unit_price::numeric(12, 2) as unit_price,
    discount_amount::numeric(12, 2) as discount_amount,
    line_total::numeric(12, 2) as line_total
from {{ source('ecommerce_raw', 'order_items') }}
