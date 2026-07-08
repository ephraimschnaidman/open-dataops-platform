# E-Commerce Demo Domain

The e-commerce domain is the first demo domain for Open DataOps Platform. It is intentionally separate from the platform core so the warehouse, ingestion, transformation, and quality layers can remain domain-agnostic.

This directory contains small, realistic CSV fixtures that can be used later to demonstrate ingestion, modeling, testing, lineage, and analytics workflows. No ingestion code is included in this milestone.

## Sample Data

The sample files live in `domains/ecommerce/sample_data`.

| File | Approximate rows | Description |
| --- | ---: | --- |
| `customers.csv` | 20 | Customer profiles with geography and marketing opt-in state. |
| `products.csv` | 30 | Product catalog across apparel, home, electronics, beauty, outdoor, and pets. |
| `orders.csv` | 50 | Order headers with customer, status, and order-level financial amounts. |
| `order_items.csv` | 80 | Line-item detail for each order, including product, quantity, and line discounts. |
| `payments.csv` | 50 | One payment attempt or outcome per order, including paid, failed, and refunded cases. |
| `web_events.csv` | 150 | Clickstream-style events for converting and non-converting sessions. |

## Relationships

- `orders.customer_id` references `customers.customer_id`.
- `order_items.order_id` references `orders.order_id`.
- `order_items.product_id` references `products.product_id`.
- `payments.order_id` references `orders.order_id`.
- `web_events.customer_id` references `customers.customer_id` when the visitor is known.
- `web_events.product_id` references `products.product_id` for product-level events.
- `web_events.order_id` references `orders.order_id` for checkout completion events.

Anonymous web events use `anonymous_id` and leave `customer_id` empty. Non-product events leave `product_id` empty. Events that do not convert leave `order_id` empty.

## Intentional Edge Cases

- Failed payments are represented in `payments.csv` with `status = failed`.
- Refunded payments are represented in `payments.csv` with `status = refunded` and matching refunded orders.
- Canceled orders are represented in `orders.csv` with `status = canceled`.
- Several customers have multiple orders, including `CUST001`, `CUST002`, and `CUST003`.
- Products `PROD028`, `PROD029`, and `PROD030` appear in web events but not in order items, creating products with browsing activity and no sales.
- Many web sessions do not convert and have no `order_id`.

## Modeling Notes

These CSVs are raw demo inputs. Future milestones may load them into the `raw` schema, validate relationships, and transform them into staging and marts models. The platform should not hard-code e-commerce assumptions; this domain is a reusable example, not the product boundary.
