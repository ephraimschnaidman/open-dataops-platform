# 005. Use Dimensional Modeling for Ecommerce Analytics

## Status

Accepted

## Context

The ecommerce staging models clean and standardize source data while preserving the shape of the operational entities. They are a dependable transformation boundary, but they do not define reusable business grains, safe aggregation paths, or governed analytical measures.

Analytics users need to answer questions about orders, products, customers, payments, and web behavior without repeatedly rebuilding joins and status logic. The data also contains one-to-many processes: an order can have several items and payment records, while a web event may be anonymous or may optionally reference a customer, product, or order.

## Decision

The ecommerce analytics layer will use dimensional modeling with conformed customer, product, and date dimensions; separate order, order-item, payment, and web-event facts; and downstream business aggregates.

The lineage is:

```text
raw source tables -> staging views -> dimension and fact tables -> aggregate tables
```

Every fact declares one stable grain:

- `fct_orders`: one row per source order.
- `fct_order_items`: one row per source order line.
- `fct_payments`: one row per source payment record.
- `fct_web_events`: one row per source web event.

Facts and dimensions are separated because they serve different responsibilities. Facts preserve measurable business events at an explicit grain. Dimensions provide reusable descriptive context shared by those processes. This separation prevents header-level order values from being multiplied across order lines or payment attempts and gives reports consistent customer, product, and calendar attributes.

Marts will depend only on dbt staging models, never directly on raw tables. Raw remains an auditable, source-like landing layer; staging owns type casting, trimming, and categorical normalization; marts own business-facing structure and metrics. This dependency boundary prevents raw source imperfections from leaking into analytics and gives marts a stable upstream contract.

All current mart and aggregate models are tables. None are incremental during this milestone because the demo dataset is small and deterministic. In production, `fct_web_events`, `fct_order_items`, `fct_payments`, and `fct_orders` are the leading incremental candidates. Customer and product dimensions may also become incremental at scale, while `dim_date` should remain a small, deterministic table. Late-arriving records, mutable order status, refunds, and source corrections require merge strategies and lookback windows rather than append-only processing.

## Consequences

- Business grains and relationships are explicit and testable.
- Conformed dimensions make analysis consistent across separate business processes.
- Aggregate models give common sales, customer lifetime, and product metrics stable interfaces.
- BI queries become simpler and less likely to introduce many-to-many fanout errors.
- Staging remains reusable and source-oriented instead of accumulating business logic.
- Additional models, tests, documentation, and storage are required compared with exposing staging views directly.
- Table materializations duplicate some staged data and take longer to rebuild than views.
- Current source IDs act as dimension keys; future Type 2 history would require surrogate keys and effective dating.
- Metric definitions such as delivered sales are intentionally opinionated and must evolve through governed business decisions.
- Fact-to-fact analysis still requires aggregation to compatible grains before joining.

## Alternatives considered

### Expose staging models directly

This would reduce model count and storage, but every consumer would need to recreate business joins and metrics. It would also make accidental double counting much more likely.

### Build one denormalized ecommerce table

A single wide table would be convenient for a narrow report but cannot naturally represent multiple order items, payment attempts, and web events without duplicating measures or losing detail.

### Use incremental models immediately

Incremental processing would add state, late-arrival, and update-handling complexity without a meaningful benefit for the small static demo dataset. The model grains and tests should be validated before production optimization.

## Non-goals

- No Airflow or other orchestration is introduced.
- No Metabase or other BI service is introduced.
- No external data quality framework is introduced.
- No production incremental strategy is implemented in this milestone.
