import { randomUUID } from "node:crypto";
import { getAlertStrategy } from "../domain/alertStrategies.js";

const DEBOUNCE_WINDOW_MS = 10_000;

export class SignalProcessor {
  constructor(store, dashboardCache) {
    this.store = store;
    this.dashboardCache = dashboardCache;
    this.queue = [];
    this.maxQueueSize = 50_000;
    this.processing = false;
    this.debounceByComponent = new Map();
    this.metrics = { accepted: 0, processed: 0, rejected: 0 };
  }

  enqueue(signal) {
    if (this.queue.length >= this.maxQueueSize) {
      this.metrics.rejected += 1;
      return false;
    }
    this.queue.push({ ...signal, receivedAt: new Date().toISOString() });
    this.metrics.accepted += 1;
    this.processSoon();
    return true;
  }

  processSoon() {
    if (!this.processing) {
      this.processing = true;
      setImmediate(() => this.drain());
    }
  }

  async drain() {
    while (this.queue.length > 0) {
      const signal = this.queue.shift();
      await this.processSignal(signal);
    }
    this.processing = false;
  }

  async processSignal(signal) {
    const workItem = await this.findOrCreateWorkItem(signal);
    const linkedSignal = { ...signal, workItemId: workItem.id };
    await this.store.appendRawSignal(linkedSignal);
    await this.store.updateAggregations(linkedSignal);
    this.dashboardCache.upsert(workItem);
    this.metrics.processed += 1;
  }

  async findOrCreateWorkItem(signal) {
    const now = Date.now();
    const existing = this.debounceByComponent.get(signal.componentId);
    if (existing && now - existing.windowStartedAt <= DEBOUNCE_WINDOW_MS) {
      const updated = await this.store.transaction(async (workItems) => {
        const item = workItems.find((workItem) => workItem.id === existing.workItem.id);
        if (!item) {
          return existing.workItem;
        }
        item.signalCount += 1;
        item.lastSignalAt = signal.receivedAt;
        item.updatedAt = signal.receivedAt;
        return item;
      });
      existing.workItem = updated;
      return updated;
    }

    const alert = getAlertStrategy(signal.componentType).evaluate(signal);
    const workItem = {
      id: randomUUID(),
      componentId: signal.componentId,
      componentType: signal.componentType,
      title: `${signal.componentId} failure detected`,
      status: "OPEN",
      severity: alert.severity,
      alertChannel: alert.channel,
      responder: alert.responder,
      signalCount: 1,
      firstSignalAt: signal.receivedAt,
      lastSignalAt: signal.receivedAt,
      rca: null,
      mttrMs: null,
      createdAt: signal.receivedAt,
      updatedAt: signal.receivedAt
    };

    const saved = await this.store.transaction(async (workItems) => {
      workItems.push(workItem);
      return workItem;
    });

    this.debounceByComponent.set(signal.componentId, { windowStartedAt: now, workItem: saved });
    return saved;
  }
}
