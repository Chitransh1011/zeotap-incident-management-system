import pytest

from app.domain.state_machine import assert_transition, calculate_mttr_ms, is_complete_rca


def test_rca_validation_rejects_incomplete_objects():
    assert is_complete_rca({"rootCauseCategory": "CONFIG"}) is False


def test_rca_validation_accepts_complete_objects():
    assert (
        is_complete_rca(
            {
                "startTime": "2026-05-01T10:00:00+00:00",
                "endTime": "2026-05-01T10:30:00+00:00",
                "rootCauseCategory": "DATABASE",
                "fixApplied": "Promoted standby",
                "preventionSteps": "Add failover drill",
            }
        )
        is True
    )


def test_closed_transition_requires_complete_rca():
    with pytest.raises(ValueError, match="complete RCA"):
        assert_transition("RESOLVED", "CLOSED", {"rca": None})


def test_mttr_is_calculated_from_rca_timestamps():
    mttr = calculate_mttr_ms(
        {
            "startTime": "2026-05-01T10:00:00+00:00",
            "endTime": "2026-05-01T10:30:00+00:00",
            "rootCauseCategory": "DATABASE",
            "fixApplied": "Promoted standby",
            "preventionSteps": "Add failover drill",
        }
    )
    assert mttr == 1_800_000
