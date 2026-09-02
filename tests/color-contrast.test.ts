import assert from "node:assert/strict";
import test from "node:test";
import { contrastRatio, contrastingTextColor } from "../src/lib/color-contrast";

const light = "#f8faf6";
const dark = "#10140f";

test("allocation text color is selected from the segment background", () => {
  assert.equal(contrastingTextColor("#174f32"), light);
  assert.equal(contrastingTextColor("#c8cec5"), dark);
});

test("selected allocation text always has the stronger palette contrast", () => {
  for (const background of ["#174f32", "#397357", "#89a797", "#c8cec5", "#68776b"]) {
    const selected = contrastingTextColor(background);
    const rejected = selected === light ? dark : light;
    assert.ok(contrastRatio(background, selected) >= contrastRatio(background, rejected));
  }
});
