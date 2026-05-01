import { assertTransition, calculateMttrMs, isCompleteRca } from "../domain/stateMachine.js";

export class IncidentService {
  constructor(store, dashboardCache) {
    this.store = store;
    this.dashboardCache = dashboardCache;
  }

  async getIncident(id) {
    const workItems = await this.store.readWorkItems();
    const item = workItems.find((workItem) => workItem.id === id);
    if (!item) {
      return null;
    }
    const rawSignals = await this.store.listRawSignalsByIncident(id);
    return { ...item, rawSignals };
  }

  async transition(id, nextStatus) {
    return this.store.transaction(async (workItems) => {
      const item = workItems.find((workItem) => workItem.id === id);
      if (!item) {
        throw new Error("Incident not found");
      }
      assertTransition(item.status, nextStatus, item);
      item.status = nextStatus;
      item.updatedAt = new Date().toISOString();
      this.dashboardCache.upsert(item);
      if (item.status === "CLOSED") {
        this.dashboardCache.remove(item.id);
      }
      return item;
    });
  }

  async submitRca(id, rca) {
    if (!isCompleteRca(rca)) {
      throw new Error("RCA is incomplete");
    }
    return this.store.transaction(async (workItems) => {
      const item = workItems.find((workItem) => workItem.id === id);
      if (!item) {
        throw new Error("Incident not found");
      }
      item.rca = rca;
      item.mttrMs = calculateMttrMs(rca);
      item.updatedAt = new Date().toISOString();
      this.dashboardCache.upsert(item);
      return item;
    });
  }
}
