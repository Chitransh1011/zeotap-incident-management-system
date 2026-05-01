import fs from "node:fs/promises";
import path from "node:path";
import { Mutex } from "./mutex.js";
import { retry } from "./retry.js";

export class FileStore {
  constructor(dataDir) {
    this.dataDir = dataDir;
    this.rawPath = path.join(dataDir, "raw-signals.jsonl");
    this.workItemsPath = path.join(dataDir, "work-items.json");
    this.aggregationsPath = path.join(dataDir, "aggregations.json");
    this.workItemMutex = new Mutex();
  }

  async init() {
    await fs.mkdir(this.dataDir, { recursive: true });
    await this.ensureJson(this.workItemsPath, []);
    await this.ensureJson(this.aggregationsPath, {});
    await fs.appendFile(this.rawPath, "");
  }

  async ensureJson(filePath, fallback) {
    try {
      await fs.access(filePath);
    } catch {
      await fs.writeFile(filePath, JSON.stringify(fallback, null, 2));
    }
  }

  async appendRawSignal(signal) {
    await retry(() => fs.appendFile(this.rawPath, `${JSON.stringify(signal)}\n`));
  }

  async listRawSignalsByIncident(incidentId) {
    const content = await fs.readFile(this.rawPath, "utf8");
    return content
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((signal) => signal.workItemId === incidentId);
  }

  async readWorkItems() {
    return JSON.parse(await fs.readFile(this.workItemsPath, "utf8"));
  }

  async writeWorkItems(workItems) {
    await retry(() => fs.writeFile(this.workItemsPath, JSON.stringify(workItems, null, 2)));
  }

  async transaction(updateFn) {
    return this.workItemMutex.runExclusive(async () => {
      const workItems = await this.readWorkItems();
      const result = await updateFn(workItems);
      await this.writeWorkItems(workItems);
      return result;
    });
  }

  async updateAggregations(signal) {
    const aggregations = JSON.parse(await fs.readFile(this.aggregationsPath, "utf8"));
    const minute = new Date(signal.receivedAt).toISOString().slice(0, 16);
    const key = `${minute}|${signal.componentId}|${signal.severity}`;
    aggregations[key] = (aggregations[key] ?? 0) + 1;
    await retry(() => fs.writeFile(this.aggregationsPath, JSON.stringify(aggregations, null, 2)));
  }

  async readAggregations() {
    return JSON.parse(await fs.readFile(this.aggregationsPath, "utf8"));
  }
}
