const severityOrder = { P0: 0, P1: 1, P2: 2, P3: 3 };

export class DashboardCache {
  constructor() {
    this.items = new Map();
  }

  hydrate(workItems) {
    workItems.forEach((item) => this.upsert(item));
  }

  upsert(item) {
    this.items.set(item.id, item);
  }

  remove(id) {
    this.items.delete(id);
  }

  listActive() {
    return [...this.items.values()]
      .filter((item) => item.status !== "CLOSED")
      .sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity] || a.createdAt.localeCompare(b.createdAt));
  }
}
