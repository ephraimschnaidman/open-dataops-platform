{{ config(materialized='table') }}

with date_bounds as (
    select created_at::date as activity_date
    from {{ ref('stg_customers') }}

    union all

    select order_ts::date as activity_date
    from {{ ref('stg_orders') }}

    union all

    select payment_ts::date as activity_date
    from {{ ref('stg_payments') }}

    union all

    select event_ts::date as activity_date
    from {{ ref('stg_web_events') }}
),

calendar_bounds as (
    select
        min(activity_date) as minimum_date,
        max(activity_date) as maximum_date
    from date_bounds
),

calendar as (
    select generate_series(
        minimum_date::timestamp,
        maximum_date::timestamp,
        interval '1 day'
    )::date as date_key
    from calendar_bounds
)

select
    date_key,
    extract(isodow from date_key)::integer as day_of_week_number,
    trim(to_char(date_key, 'Day')) as day_of_week_name,
    extract(day from date_key)::integer as day_of_month,
    extract(week from date_key)::integer as week_of_year,
    extract(month from date_key)::integer as month_number,
    trim(to_char(date_key, 'Month')) as month_name,
    extract(quarter from date_key)::integer as quarter_number,
    extract(year from date_key)::integer as year_number,
    extract(isodow from date_key)::integer in (6, 7) as is_weekend
from calendar
