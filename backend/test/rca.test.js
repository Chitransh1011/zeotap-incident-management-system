import test from "node:test";
import assert from "node:assert/strict";
import { assertTransition, calculateMttrMs, isCompleteRca } from "../src/domain/stateMachine.js";

test("RCA validation rejects incomplete objects", () => {
  assert.equal(isCompleteRca({ rootCauseCategory: "CONFIG" }), false);
});

test("RCA validation accepts complete objects", () => {
  assert.equal(
    isCompleteRca({
      startTime: "2026-05-01T10:00:00.000Z",
      endTime: "2026-05-01T10:30:00.000Z",
      rootCauseCategory: "DATABASE",
      fixApplied: "Promoted standby",
      preventionSteps: "Add failover drill"
    }),
    true
  );
});

test("closed transition requires complete RCA", () => {
  assert.throws(
    () => assertTransition("RESOLVED", "CLOSED", { rca: null }),
    /complete RCA/
  );
});

test("MTTR is calculated from RCA timestamps", () => {
  const mttr = calculateMttrMs({
    startTime: "2026-05-01T10:00:00.000Z",
    endTime: "2026-05-01T10:30:00.000Z",
    rootCauseCategory: "DATABASE",
    fixApplied: "Promoted standby",
    preventionSteps: "Add failover drill"
  });
  assert.equal(mttr, 1_800_000);
});
