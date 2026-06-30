from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .models import ExchangeRate

USD = "USD"
ROUNDING = Decimal("0.01")


def normalize_currency_code(value: str | None) -> str:
    return (value or "").strip().upper()


def latest_exchange_rate(currency_code: str) -> ExchangeRate | None:
    normalized = normalize_currency_code(currency_code)
    if not normalized or normalized == USD:
        return None
    return ExchangeRate.objects.filter(currency_code=normalized).order_by("-effective_date").first()


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(ROUNDING, rounding=ROUND_HALF_UP)


def _to_decimal(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def normalize_amount_to_usd(
    amount: Decimal | str | int | float | None,
    currency_code: str | None,
) -> tuple[Decimal | None, ExchangeRate | None, str]:
    amount = _to_decimal(amount)
    if amount is None:
        return None, None, "missing_amount"

    currency = normalize_currency_code(currency_code)
    if not currency:
        return None, None, "missing_currency"

    if currency == USD:
        return _round_money(amount), None, "native_usd"

    rate = latest_exchange_rate(currency)
    if rate is None:
        return None, None, "missing_exchange_rate"

    return _round_money(amount * rate.usd_rate), rate, "converted"


def normalize_university_costs(university, *, save: bool = False):
    """Derive USD cost fields without pretending non-USD values are already USD."""

    if university.tuition_original_amount is None and university.tuition_amount is not None:
        university.tuition_original_amount = university.tuition_amount
    if not university.tuition_original_currency and university.tuition_currency:
        university.tuition_original_currency = normalize_currency_code(university.tuition_currency)

    tuition_usd, tuition_rate, tuition_status = normalize_amount_to_usd(
        university.tuition_original_amount,
        university.tuition_original_currency,
    )
    university.tuition_usd_amount = tuition_usd

    total_usd, total_rate, total_status = normalize_amount_to_usd(
        university.total_cost_original_amount,
        university.total_cost_original_currency,
    )
    university.total_cost_usd_amount = total_usd

    rate = tuition_rate or total_rate
    if rate is not None:
        university.currency_conversion_rate = rate.usd_rate
        university.currency_conversion_date = rate.effective_date
        university.currency_conversion_source = rate.source
        university.currency_conversion_confidence = rate.confidence
    elif tuition_status == "native_usd" or total_status == "native_usd":
        university.currency_conversion_rate = Decimal("1.000000")
        university.currency_conversion_confidence = "high"
        if not university.currency_conversion_source:
            university.currency_conversion_source = "Original amount is already USD."
    elif tuition_status == "missing_exchange_rate" or total_status == "missing_exchange_rate":
        university.currency_conversion_confidence = "low"
        if "USD conversion not available yet." not in university.cost_notes:
            university.cost_notes = (
                f"{university.cost_notes}\nUSD conversion not available yet."
            ).strip()

    if save:
        university.save(
            update_fields=[
                "tuition_original_amount",
                "tuition_original_currency",
                "tuition_usd_amount",
                "total_cost_usd_amount",
                "currency_conversion_rate",
                "currency_conversion_date",
                "currency_conversion_source",
                "currency_conversion_confidence",
                "cost_notes",
                "updated_at",
            ]
        )

    return {
        "tuition_status": tuition_status,
        "total_cost_status": total_status,
        "rate": rate,
    }
