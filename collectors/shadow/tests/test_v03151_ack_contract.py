from __future__ import annotations

import pytest

from collectors.shadow.acknowledgement import AckContractError, make_ack, validate_ack
from collectors.shadow.tests.behavioral_helpers import events


@pytest.mark.parametrize("status,error,outcome", [
    ("accepted", "none", "success"),
    ("duplicate", "none", "success"),
    ("rejected_temporary", "timeout", "retryable_failure"),
    ("rate_limited", "rate_limit", "retryable_failure"),
    ("rejected_permanent", "authorization", "permanent_rejection"),
])
def test_ack_status_matrix(status, error, outcome):
    event = events(1)[0]
    assert validate_ack(make_ack(event, status, error), event).outcome == outcome


@pytest.mark.parametrize("mutation", [
    lambda ack: ack.pop("protocol_version"),
    lambda ack: ack.update(status="mystery"),
    lambda ack: ack.update(idempotency_key="0" * 64),
    lambda ack: ack.update(status="accepted", error_class="timeout"),
    lambda ack: ack.update(status="accepted", retryable=True),
])
def test_malformed_and_unknown_ack_rejected(mutation):
    event = events(1)[0]
    ack = make_ack(event)
    mutation(ack)
    with pytest.raises(AckContractError):
        validate_ack(ack, event)
