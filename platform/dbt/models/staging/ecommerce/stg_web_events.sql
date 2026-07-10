select
    trim(event_id) as event_id,
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(anonymous_id), '') as anonymous_id,
    trim(session_id) as session_id,
    event_ts::timestamptz as event_ts,
    case lower(trim(event_type))
        when 'product viewed' then 'product_view'
        when 'product view' then 'product_view'
        when 'product_view' then 'product_view'
        when 'checkout complete' then 'checkout_completed'
        when 'purchase completed' then 'checkout_completed'
        when 'checkout_completed' then 'checkout_completed'
        when 'page view' then 'page_view'
        when 'page_view' then 'page_view'
        when 'site search' then 'search'
        when 'search' then 'search'
        when 'add to cart' then 'add_to_cart'
        when 'cart_add' then 'add_to_cart'
        when 'add_to_cart' then 'add_to_cart'
        else lower(trim(event_type))
    end as event_type,
    nullif(trim(product_id), '') as product_id,
    nullif(trim(order_id), '') as order_id,
    lower(trim(channel)) as channel,
    case lower(trim(device))
        when 'mobile web' then 'mobile'
        when 'iphone' then 'mobile'
        when 'android' then 'mobile'
        when 'mobile' then 'mobile'
        when 'desktop web' then 'desktop'
        when 'desktop' then 'desktop'
        else lower(trim(device))
    end as device
from {{ source('ecommerce_raw', 'web_events') }}
