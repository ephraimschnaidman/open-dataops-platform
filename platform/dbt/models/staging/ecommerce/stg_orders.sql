select
    trim(order_id) as order_id,
    trim(customer_id) as customer_id,
    order_ts::timestamptz as order_ts,
    case lower(trim(status))
        when 'completed' then 'delivered'
        when 'delivered' then 'delivered'
        when 'cancelled' then 'canceled'
        when 'canceled' then 'canceled'
        when 'refund issued' then 'refunded'
        when 'returned_refund' then 'refunded'
        when 'refunded' then 'refunded'
        else lower(trim(status))
    end as order_status,
    subtotal::numeric(12, 2) as subtotal,
    discount_amount::numeric(12, 2) as discount_amount,
    shipping_amount::numeric(12, 2) as shipping_amount,
    tax_amount::numeric(12, 2) as tax_amount,
    total_amount::numeric(12, 2) as total_amount,
    upper(trim(currency)) as currency
from {{ source('ecommerce_raw', 'orders') }}
