from dataclasses import dataclass


@dataclass(frozen=True)
class AlertDecision:
    severity: str
    channel: str
    responder: str


class AlertStrategy:
    def evaluate(self, signal: dict) -> AlertDecision:
        return AlertDecision("P3", "dashboard", "sre-oncall")


class RdbmsAlertStrategy(AlertStrategy):
    def evaluate(self, signal: dict) -> AlertDecision:
        return AlertDecision("P0", "pager", "database-oncall")


class McpAlertStrategy(AlertStrategy):
    def evaluate(self, signal: dict) -> AlertDecision:
        return AlertDecision("P1", "pager", "platform-oncall")


class CacheAlertStrategy(AlertStrategy):
    def evaluate(self, signal: dict) -> AlertDecision:
        return AlertDecision("P2", "slack", "cache-oncall")


class QueueAlertStrategy(AlertStrategy):
    def evaluate(self, signal: dict) -> AlertDecision:
        return AlertDecision("P1", "pager", "async-oncall")


STRATEGIES: dict[str, AlertStrategy] = {
    "RDBMS": RdbmsAlertStrategy(),
    "MCP_HOST": McpAlertStrategy(),
    "CACHE": CacheAlertStrategy(),
    "QUEUE": QueueAlertStrategy(),
}


def get_alert_strategy(component_type: str) -> AlertStrategy:
    return STRATEGIES.get(component_type.upper(), AlertStrategy())
