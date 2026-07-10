{{ config(materialized='table') }}

select
    events.event_id,
    customers.customer_id as customer_key,
    products.product_id as product_key,
    events.order_id,
    events.event_ts::date as event_date_key,
    events.event_ts as occurred_at,
    events.anonymous_id,
    events.session_id,
    events.event_type,
    events.channel,
    events.device,
    1 as event_count
from {{ ref('stg_web_events') }} as events
left join {{ ref('stg_customers') }} as customers
    on events.customer_id = customers.customer_id
left join {{ ref('stg_products') }} as products
    on events.product_id = products.product_id
