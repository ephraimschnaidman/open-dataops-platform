CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id text,
    email text,
    first_name text,
    last_name text,
    created_at timestamptz,
    country text,
    region text,
    marketing_opt_in boolean
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id text,
    sku text,
    product_name text,
    category text,
    brand text,
    unit_price numeric(12, 2),
    currency text,
    is_active boolean
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id text,
    customer_id text,
    order_ts timestamptz,
    status text,
    subtotal numeric(12, 2),
    discount_amount numeric(12, 2),
    shipping_amount numeric(12, 2),
    tax_amount numeric(12, 2),
    total_amount numeric(12, 2),
    currency text
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_item_id text,
    order_id text,
    product_id text,
    quantity integer,
    unit_price numeric(12, 2),
    discount_amount numeric(12, 2),
    line_total numeric(12, 2)
);

CREATE TABLE IF NOT EXISTS raw.payments (
    payment_id text,
    order_id text,
    payment_ts timestamptz,
    payment_method text,
    status text,
    amount numeric(12, 2),
    currency text,
    provider_transaction_id text
);

CREATE TABLE IF NOT EXISTS raw.web_events (
    event_id text,
    customer_id text,
    anonymous_id text,
    session_id text,
    event_ts timestamptz,
    event_type text,
    product_id text,
    order_id text,
    channel text,
    device text
);
