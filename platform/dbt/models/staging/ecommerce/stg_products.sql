select
    trim(product_id) as product_id,
    trim(sku) as sku,
    trim(product_name) as product_name,
    lower(trim(category)) as category,
    trim(brand) as brand,
    unit_price::numeric(12, 2) as unit_price,
    upper(trim(currency)) as currency,
    is_active::boolean as is_active
from {{ source('ecommerce_raw', 'products') }}
