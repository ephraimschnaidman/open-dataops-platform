select
    payment_id,
    order_id,
    payment_ts,
    payment_method,
    status,
    amount,
    currency,
    provider_transaction_id
from {{ source('ecommerce_raw', 'payments') }}
