select
    trim(payment_id) as payment_id,
    trim(order_id) as order_id,
    payment_ts::timestamptz as payment_ts,
    case lower(trim(payment_method))
        when 'paypal' then 'paypal'
        when 'apple_pay' then 'apple_pay'
        when 'card' then 'card'
        else lower(trim(payment_method))
    end as payment_method,
    case lower(trim(status))
        when 'succeeded' then 'paid'
        when 'paid' then 'paid'
        when 'failed payment' then 'failed'
        when 'declined' then 'failed'
        when 'failed' then 'failed'
        when 'refund issued' then 'refunded'
        when 'refunded' then 'refunded'
        else lower(trim(status))
    end as payment_status,
    amount::numeric(12, 2) as amount,
    upper(trim(currency)) as currency,
    nullif(trim(provider_transaction_id), '') as provider_transaction_id
from {{ source('ecommerce_raw', 'payments') }}
