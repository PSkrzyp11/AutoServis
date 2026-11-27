from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
PERCENT_DIVISOR = Decimal(100)
ALLOWED_VAT_RATES = frozenset({Decimal(23), Decimal(8), Decimal(5), Decimal(0)})


def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def gross_from_net(net_amount: Decimal, vat_rate: Decimal) -> Decimal:
    return round_money(net_amount * (1 + vat_rate / PERCENT_DIVISOR))
