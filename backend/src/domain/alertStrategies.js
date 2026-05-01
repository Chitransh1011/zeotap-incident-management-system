export class AlertStrategy {
  evaluate() {
    return { severity: "P3", channel: "dashboard", responder: "sre-oncall" };
  }
}

export class RdbmsAlertStrategy extends AlertStrategy {
  evaluate() {
    return { severity: "P0", channel: "pager", responder: "database-oncall" };
  }
}

export class McpAlertStrategy extends AlertStrategy {
  evaluate() {
    return { severity: "P1", channel: "pager", responder: "platform-oncall" };
  }
}

export class CacheAlertStrategy extends AlertStrategy {
  evaluate() {
    return { severity: "P2", channel: "slack", responder: "cache-oncall" };
  }
}

export class QueueAlertStrategy extends AlertStrategy {
  evaluate() {
    return { severity: "P1", channel: "pager", responder: "async-oncall" };
  }
}

const strategies = {
  RDBMS: new RdbmsAlertStrategy(),
  MCP_HOST: new McpAlertStrategy(),
  CACHE: new CacheAlertStrategy(),
  QUEUE: new QueueAlertStrategy()
};

export function getAlertStrategy(componentType = "") {
  return strategies[componentType.toUpperCase()] ?? new AlertStrategy();
}
