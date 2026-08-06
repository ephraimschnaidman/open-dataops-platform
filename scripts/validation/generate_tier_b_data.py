from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

random.seed(42)

OUTPUT_DIR = Path("domains/ecommerce/validation_data/tier_b")

CUSTOMER_COUNT = 50_000
PRODUCT_COUNT = 10_000
ORDER_COUNT = 200_000
ORDER_ITEM_COUNT = 400_000
PAYMENT_COUNT = 200_000
WEB_EVENT_COUNT = 140_000

BASE_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def iso_timestamp(offset_minutes: int) -> str:
    value = BASE_DATE + timedelta(minutes=offset_minutes)
    return value.isoformat().replace("+00:00", "Z")


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def write_customers() -> None:
    path = OUTPUT_DIR / "customers.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "customer_id",
                "email",
                "first_name",
                "last_name",
                "created_at",
                "country",
                "region",
                "marketing_opt_in",
            ]
        )

        for number in range(1, CUSTOMER_COUNT + 1):
            writer.writerow(
                [
                    f"CUST{number:06d}",
                    f"customer{number}@example.com",
                    f"First{number}",
                    f"Last{number}",
                    iso_timestamp(number),
                    "US",
                    ["California", "New York", "Texas", "Washington"][number % 4],
                    str(number % 3 != 0).lower(),
                ]
            )


def write_products() -> dict[str, Decimal]:
    path = OUTPUT_DIR / "products.csv"
    product_prices: dict[str, Decimal] = {}

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "product_id",
                "sku",
                "product_name",
                "category",
                "brand",
                "unit_price",
                "currency",
                "is_active",
            ]
        )

        for number in range(1, PRODUCT_COUNT + 1):
            product_id = f"PROD{number:06d}"
            price = Decimal(10 + number % 190) + Decimal("0.99")
            product_prices[product_id] = price

            writer.writerow(
                [
                    product_id,
                    f"SKU-{number:06d}",
                    f"Validation Product {number}",
                    ["Apparel", "Electronics", "Home", "Outdoor"][number % 4],
                    f"Brand{number % 25:02d}",
                    money(price),
                    "USD",
                    "true",
                ]
            )

    return product_prices


def write_orders_items_and_payments(
    product_prices: dict[str, Decimal],
) -> None:
    orders_path = OUTPUT_DIR / "orders.csv"
    items_path = OUTPUT_DIR / "order_items.csv"
    payments_path = OUTPUT_DIR / "payments.csv"

    with (
        orders_path.open("w", newline="", encoding="utf-8") as orders_file,
        items_path.open("w", newline="", encoding="utf-8") as items_file,
        payments_path.open("w", newline="", encoding="utf-8") as payments_file,
    ):
        orders_writer = csv.writer(orders_file)
        items_writer = csv.writer(items_file)
        payments_writer = csv.writer(payments_file)

        orders_writer.writerow(
            [
                "order_id",
                "customer_id",
                "order_ts",
                "status",
                "subtotal",
                "discount_amount",
                "shipping_amount",
                "tax_amount",
                "total_amount",
                "currency",
            ]
        )

        items_writer.writerow(
            [
                "order_item_id",
                "order_id",
                "product_id",
                "quantity",
                "unit_price",
                "discount_amount",
                "line_total",
            ]
        )

        payments_writer.writerow(
            [
                "payment_id",
                "order_id",
                "payment_ts",
                "payment_method",
                "status",
                "amount",
                "currency",
                "provider_transaction_id",
            ]
        )

        item_number = 1

        for order_number in range(1, ORDER_COUNT + 1):
            order_id = f"ORD{order_number:07d}"
            customer_id = f"CUST{((order_number - 1) % CUSTOMER_COUNT) + 1:06d}"
            order_timestamp = iso_timestamp(10_000 + order_number)

            status = ["delivered", "completed", "cancelled", "refunded"][
                order_number % 4
            ]

            subtotal = Decimal("0.00")

            for item_position in range(2):
                product_number = (
                    ((order_number * 2 + item_position) - 1) % PRODUCT_COUNT
                ) + 1
                product_id = f"PROD{product_number:06d}"
                unit_price = product_prices[product_id]
                quantity = 1 + ((order_number + item_position) % 3)
                line_total = unit_price * quantity

                items_writer.writerow(
                    [
                        f"OI{item_number:08d}",
                        order_id,
                        product_id,
                        quantity,
                        money(unit_price),
                        "0.00",
                        money(line_total),
                    ]
                )

                subtotal += line_total
                item_number += 1

            if status == "cancelled":
                shipping = Decimal("0.00")
                tax = Decimal("0.00")
                total = Decimal("0.00")
            else:
                shipping = Decimal("6.99") if subtotal < Decimal("100") else Decimal("0.00")
                tax = subtotal * Decimal("0.08")
                total = subtotal + shipping + tax

            orders_writer.writerow(
                [
                    order_id,
                    customer_id,
                    order_timestamp,
                    status,
                    money(subtotal),
                    "0.00",
                    money(shipping),
                    money(tax),
                    money(total),
                    "USD",
                ]
            )

            payment_status = {
                "delivered": "paid",
                "completed": "succeeded",
                "cancelled": "failed",
                "refunded": "refunded",
            }[status]

            payments_writer.writerow(
                [
                    f"PAY{order_number:07d}",
                    order_id,
                    iso_timestamp(10_001 + order_number),
                    ["card", "paypal", "apple_pay"][order_number % 3],
                    payment_status,
                    money(total),
                    "USD",
                    (
                        ""
                        if payment_status == "failed"
                        else f"txn_validation_{order_number:07d}"
                    ),
                ]
            )


def write_web_events() -> None:
    path = OUTPUT_DIR / "web_events.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "event_id",
                "customer_id",
                "anonymous_id",
                "session_id",
                "event_ts",
                "event_type",
                "product_id",
                "order_id",
                "channel",
                "device",
            ]
        )

        for number in range(1, WEB_EVENT_COUNT + 1):
            customer_id = f"CUST{((number - 1) % CUSTOMER_COUNT) + 1:06d}"
            product_id = f"PROD{((number - 1) % PRODUCT_COUNT) + 1:06d}"

            linked_order = (
                f"ORD{number:07d}"
                if number <= ORDER_COUNT and number % 5 == 0
                else ""
            )

            writer.writerow(
                [
                    f"EVT{number:08d}",
                    customer_id,
                    "",
                    f"SESS{number:08d}",
                    iso_timestamp(50_000 + number),
                    [
                        "product_view",
                        "add_to_cart",
                        "checkout_completed",
                        "page_view",
                        "search",
                    ][number % 5],
                    product_id,
                    linked_order,
                    ["email", "paid_search", "organic", "direct"][number % 4],
                    ["mobile", "desktop"][number % 2],
                ]
            )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_customers()
    product_prices = write_products()
    write_orders_items_and_payments(product_prices)
    write_web_events()

    expected_rows = (
        CUSTOMER_COUNT
        + PRODUCT_COUNT
        + ORDER_COUNT
        + ORDER_ITEM_COUNT
        + PAYMENT_COUNT
        + WEB_EVENT_COUNT
    )

    print(f"Tier A data generated in: {OUTPUT_DIR}")
    print(f"Expected total data rows: {expected_rows:,}")


if __name__ == "__main__":
    main()