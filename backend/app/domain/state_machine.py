from datetime import datetime


TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"INVESTIGATING"},
    "INVESTIGATING": {"RESOLVED"},
    "RESOLVED": {"CLOSED", "INVESTIGATING"},
    "CLOSED": set(),
}

REQUIRED_RCA_FIELDS = {
    "startTime",
    "endTime",
    "rootCauseCategory",
    "fixApplied",
    "preventionSteps",
}


def is_complete_rca(rca: dict | None) -> bool:
    return bool(rca and all(rca.get(field) for field in REQUIRED_RCA_FIELDS))


def assert_transition(current: str, next_status: str, work_item: dict) -> None:
    if next_status not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition {current} -> {next_status}")
    if next_status == "CLOSED" and not is_complete_rca(work_item.get("rca")):
        raise ValueError("Cannot close incident without a complete RCA")


def calculate_mttr_ms(rca: dict | None) -> int | None:
    if not is_complete_rca(rca):
        return None
    start = parse_datetime(rca["startTime"])
    end = parse_datetime(rca["endTime"])
    return int((end - start).total_seconds() * 1000)


def parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
