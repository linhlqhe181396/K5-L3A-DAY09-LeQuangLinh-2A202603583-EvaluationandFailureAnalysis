"""Regression test for the first wrong step in the public C-002 ticket-trust case."""

import pytest

pytestmark = pytest.mark.student


def test_ticket_override_is_first_failure_and_fixed_shape_passes():
    from lab9.trace_case import investigate

    failing = investigate("seeded_regression", "C-002", 11)["trial"]
    fixed = investigate("fixed", "C-002", 11)["trial"]
    kinds = [event.get("kind") for event in failing["events"]]
    assert kinds.index("model_override") < kinds.index("quote")
    assert failing["lab8_pass"] is False
    assert fixed["lab8_pass"] is True
