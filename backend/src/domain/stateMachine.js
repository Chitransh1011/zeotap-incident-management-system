const transitions = {
  OPEN: ["INVESTIGATING"],
  INVESTIGATING: ["RESOLVED"],
  RESOLVED: ["CLOSED", "INVESTIGATING"],
  CLOSED: []
};

export function assertTransition(current, next, workItem) {
  if (!transitions[current]?.includes(next)) {
    throw new Error(`Invalid transition ${current} -> ${next}`);
  }
  if (next === "CLOSED" && !isCompleteRca(workItem.rca)) {
    throw new Error("Cannot close incident without a complete RCA");
  }
}

export function isCompleteRca(rca) {
  return Boolean(
    rca?.startTime &&
      rca?.endTime &&
      rca?.rootCauseCategory &&
      rca?.fixApplied &&
      rca?.preventionSteps
  );
}

export function calculateMttrMs(rca) {
  if (!isCompleteRca(rca)) {
    return null;
  }
  return new Date(rca.endTime).getTime() - new Date(rca.startTime).getTime();
}
