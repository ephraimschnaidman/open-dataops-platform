{{ config(materialized='table') }}

select
    product_id as product_key,
    product_id,
    sku,
    product_name,
    category as product_category,
    brand as product_brand,
    unit_price as current_unit_price,
    currency,
    is_active
from {{ ref('stg_products') }}
