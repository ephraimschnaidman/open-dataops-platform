select
    customer_id,
    email,
    first_name,
    last_name,
    created_at,
    country,
    region,
    marketing_opt_in
from {{ source('ecommerce_raw', 'customers') }}
