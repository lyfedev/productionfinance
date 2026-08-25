"""Proof that ``ROUND_HALF_UP`` is in effect at ``engine.rounding.quantize_money``'s
single quantisation call site — not merely imported or declared.

Every assertion below is paired: the pinned result, AND the value Python's
default ``Decimal`` context (``ROUND_HALF_EVEN``) would have produced for the
same input, on a value where the two modes genuinely disagree. A test that
only asserted the pinned result would still pass if someone deleted the
``rounding=`` argument from ``quantize_money`` — that is exactly the
regression this file exists to catch (``02-RESEARCH.md`` Pitfall 2).
"""

from decimal import ROUND_HALF_EVEN, Decimal

from engine.rounding import CENT, DOLLAR, quantize_money


def test_half_cent_diverges_from_bankers_rounding():
    """Decimal('0.005') quantised to cents: ROUND_HALF_UP -> 0.01,
    ROUND_HALF_EVEN (Python's default context) -> 0.00. The two modes
    genuinely disagree here, which is what makes the pinned-result
    assertion non-vacuous."""
    value = Decimal("0.005")

    pinned = quantize_money(value, to=CENT)
    default_context = value.quantize(CENT, rounding=ROUND_HALF_EVEN)

    assert pinned == Decimal("0.01")
    assert default_context == Decimal("0.00")
    assert pinned != default_context


def test_half_dollar_diverges_from_bankers_rounding():
    """Decimal('2.5') quantised to whole dollars: ROUND_HALF_UP -> 3,
    ROUND_HALF_EVEN -> 2. Same divergence proof, at the whole-dollar
    quantisation ``quantize_money`` actually performs by default (``to``
    defaults to ``DOLLAR``)."""
    value = Decimal("2.5")

    pinned = quantize_money(value)
    default_context = value.quantize(DOLLAR, rounding=ROUND_HALF_EVEN)

    assert pinned == Decimal("3")
    assert default_context == Decimal("2")
    assert pinned != default_context


def test_connecticut_christmas_always_regression_not_a_proof():
    """Connecticut's committed 'Christmas Always' fixture computes to
    exactly $1,159,501.50 before rounding ($3,865,005 x 30%); the disclosed
    figure is $1,159,502. ROUND_HALF_UP and ROUND_HALF_EVEN both happen to
    agree on this specific value — this test is a real regression anchor
    for that fixture, but per 02-RESEARCH.md Finding 2 it proves nothing
    about which rounding mode is actually in effect (the two tests above
    are what prove that)."""
    value = Decimal("1159501.50")

    pinned = quantize_money(value)
    default_context = value.quantize(DOLLAR, rounding=ROUND_HALF_EVEN)

    assert pinned == Decimal("1159502")
    # Explicitly documenting the agreement, not merely leaving it implicit —
    # this is the exact false-confidence trap 02-RESEARCH.md Pitfall 2 names.
    assert pinned == default_context, (
        "This fixture value is expected to agree under both rounding modes "
        "— if this assertion fails, the fixture no longer demonstrates the "
        "false-confidence case Pitfall 2 describes."
    )
