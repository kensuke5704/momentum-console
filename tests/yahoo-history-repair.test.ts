import assert from "node:assert/strict";
import test from "node:test";
import { mergeHistoryPoints } from "../src/lib/yahoo";
import type { PricePoint } from "../src/lib/types";

const point=(date:string,close:number,source?:PricePoint["source"]):PricePoint=>({date,open:close,close,...(source?{source}: {})});

test("recent Yahoo history repairs an isolated gap in the long-range response",()=>{
 const full=[point("2026-08-27",100),point("2026-08-31",102)];
 const recent=[point("2026-08-28",101,"yahoo-validated-regular-close")];
 assert.deepEqual(mergeHistoryPoints(full,recent).map(row=>row.date),["2026-08-27","2026-08-28","2026-08-31"]);
});

test("recent Yahoo history replaces the same date from the long-range response",()=>{
 const merged=mergeHistoryPoints([point("2026-08-28",0.01,"yahoo-daily-adjusted")],[point("2026-08-28",101,"yahoo-validated-regular-close")]);
 assert.equal(merged[0].close,101);
 assert.equal(merged[0].source,"yahoo-validated-regular-close");
});
