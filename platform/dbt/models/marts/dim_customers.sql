{{ config(materialized='table') }}

select
    customer_id as customer_key,
    customer_id,
    email,
    first_name,
    last_name,
    created_at as customer_created_at,
    created_at::date as customer_created_date,
    country,
    region,
    marketing_opt_in
from {{ ref('stg_customers') }}
