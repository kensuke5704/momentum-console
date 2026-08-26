import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export async function snapshotFileSet(paths: string[]): Promise<Map<string, Buffer | null>> {
  const snapshot = new Map<string, Buffer | null>();
  for (const path of paths) {
    try { snapshot.set(path, await readFile(path)); }
    catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT") snapshot.set(path, null); else throw error; }
  }
  return snapshot;
}

export async function restoreFileSet(snapshot: Map<string, Buffer | null>): Promise<void> {
  for (const [path, contents] of snapshot) {
    if (contents === null) await rm(path, { force: true });
    else { await mkdir(dirname(path), { recursive: true }); await writeFile(path, contents); }
  }
}
