select
    event_id,
    customer_id,
    anonymous_id,
    session_id,
    event_ts,
    event_type,
    product_id,
    order_id,
    channel,
    device
from {{ source('ecommerce_raw', 'web_events') }}
