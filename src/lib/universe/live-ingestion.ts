import type { NportFiling } from "../types";

export type LiveNportSnapshot = {
  generatedAt: string;
  source: string;
  baselineMaxFilingDate: string;
  scanStart: string;
  scanEnd: string;
  indexedDays: number;
  discovered: number;
  parsedNew: number;
  parseFailed: number;
  unresolvedAccessions: string[];
  filings: NportFiling[];
};

export type LiveSnapshotRequirements = {
  requireDiscovery?: boolean;
  expectedScanEnd?: string;
};

export function validateLiveNportSnapshot(
  snapshot: LiveNportSnapshot,
  requirements: LiveSnapshotRequirements = {},
): void {
  if (!snapshot.scanStart || !snapshot.scanEnd || snapshot.scanStart > snapshot.scanEnd) {
    throw new Error("Live N-PORT snapshot has an invalid scan range; refusing to update Universe");
  }
  if (requirements.expectedScanEnd && snapshot.scanEnd < requirements.expectedScanEnd) {
    throw new Error(`Live N-PORT scan ends at ${snapshot.scanEnd}, before required ${requirements.expectedScanEnd}; refusing to update Universe`);
  }
  if (!Number.isInteger(snapshot.indexedDays) || snapshot.indexedDays < 1) {
    throw new Error("SEC daily index was not available for any scanned day; refusing to update Universe");
  }
  if (!Number.isInteger(snapshot.discovered) || ((requirements.requireDiscovery ?? true) && snapshot.discovered < 1)) {
    throw new Error("No NPORT-P filings were discovered in the scanned SEC indexes; refusing to update Universe");
  }
  if (!Number.isInteger(snapshot.parseFailed) || !Array.isArray(snapshot.unresolvedAccessions) || !Array.isArray(snapshot.filings)) {
    throw new Error("Live N-PORT snapshot validation metadata is incomplete; refusing to update Universe");
  }
  if (snapshot.parseFailed > 0 || snapshot.unresolvedAccessions.length > 0) {
    throw new Error(`Live N-PORT parsing is incomplete (${snapshot.parseFailed} failed, ${snapshot.unresolvedAccessions.length} unresolved); refusing to update Universe`);
  }
}
