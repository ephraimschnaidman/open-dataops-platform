{{ config(materialized='table') }}

select
    payments.payment_id,
    payments.order_id,
    payments.payment_ts::date as payment_date_key,
    payments.payment_ts as paid_at,
    payments.payment_method,
    payments.payment_status,
    payments.amount as payment_amount,
    payments.currency,
    payments.provider_transaction_id,
    1 as payment_attempt_count
from {{ ref('stg_payments') }} as payments
