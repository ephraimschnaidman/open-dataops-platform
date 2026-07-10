# E-Commerce Demo Domain

The e-commerce domain is the first demo domain for Open DataOps Platform. It is intentionally separate from the platform core so the warehouse, ingestion, transformation, and quality layers can remain domain-agnostic.

This directory contains small, realistic CSV fixtures that can be used to demonstrate ingestion, modeling, testing, lineage, and analytics workflows. The fixtures intentionally include source-system variation so the staging layer has meaningful cleaning work to perform.

## Sample Data

The sample files live in `domains/ecommerce/sample_data`.

| File | Approximate rows | Description |
| --- | ---: | --- |
| `customers.csv` | 20 | Customer profiles with geography, marketing opt-in state, mixed-case emails, and inconsistent region labels. |
| `products.csv` | 30 | Product catalog across apparel, home, electronics, beauty, outdoor, and pets, with inconsistent category casing. |
| `orders.csv` | 50 | Order headers with customer, status, and order-level financial amounts, including status spelling variation. |
| `order_items.csv` | 80 | Line-item detail for each order, including product, quantity, and line discounts. |
| `payments.csv` | 50 | One payment attempt or outcome per order, including paid, failed, and refunded cases with realistic status and transaction ID variation. |
| `web_events.csv` | 150 | Clickstream-style events for converting and non-converting sessions, including event and device label variation. |

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

- Customer emails include mixed casing and text fields include occasional leading or trailing whitespace.
- Region values include abbreviations and fuller source labels, such as `CA`, `California`, `Ontario`, and `British Columbia`.
- Product categories include inconsistent casing, such as `Apparel`, `APPAREL`, and `apparel`.
- Failed payments are represented in `payments.csv` with several source labels, including `failed`, `failed payment`, and `declined`.
- Failed payments may have no provider transaction ID because some processors do not return one for declined attempts.
- Refunded payments and orders are represented with multiple realistic source labels, such as `refunded`, `Refunded`, and `refund issued`.
- Canceled orders are represented with both `canceled` and `cancelled` spellings.
- Web events include source variants such as `Product Viewed`, `product view`, `checkout complete`, `Purchase Completed`, `site search`, and `cart_add`.
- Device values include application-style labels such as `mobile web`, `desktop web`, `iPhone`, and `Android`.
- Several customers have multiple orders, including `CUST001`, `CUST002`, and `CUST003`.
- Products `PROD028`, `PROD029`, and `PROD030` appear in web events but not in order items, creating products with browsing activity and no sales.
- Many web sessions do not convert and have no `order_id`.

## Modeling Notes

These CSVs are raw demo inputs. The bootstrap loader loads them into the `raw` schema as-is so raw tables remain source-like and auditable. Cleaning belongs in dbt staging views, where strings are trimmed, emails are lowercased, timestamps and numerics are cast, and source-specific categorical variants are standardized.

The platform should not hard-code e-commerce assumptions outside the domain and modeling layers; this domain is a reusable example, not the product boundary.
