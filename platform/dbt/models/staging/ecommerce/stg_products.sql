select
    product_id,
    sku,
    product_name,
    category,
    brand,
    unit_price,
    currency,
    is_active
from {{ source('ecommerce_raw', 'products') }}
