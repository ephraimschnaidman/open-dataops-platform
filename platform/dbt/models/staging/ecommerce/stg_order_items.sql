select
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_amount,
    line_total
from {{ source('ecommerce_raw', 'order_items') }}
