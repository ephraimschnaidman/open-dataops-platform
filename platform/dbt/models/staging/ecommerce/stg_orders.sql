select
    order_id,
    customer_id,
    order_ts,
    status,
    subtotal,
    discount_amount,
    shipping_amount,
    tax_amount,
    total_amount,
    currency
from {{ source('ecommerce_raw', 'orders') }}
