import assert from "node:assert/strict";
import { chromium } from "playwright";

const FRONT = "https://igptm-matrix-artifact-preview.onrender.com/";
const browser = await chromium.launch({ headless: true, args: ["--disable-gpu", "--no-sandbox"] });

function getSnapshot(page) {
  return page.locator("canvas.matrix-tunnel-canvas").evaluate((canvas) => {
    const el = canvas;
    return { width: el.width, height: el.height, image: el.toDataURL("image/png"), motion: el.dataset.motion, speed: el.dataset.speed };
  });
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.goto(FRONT, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.locator("canvas.matrix-tunnel-canvas").waitFor({ timeout: 15000 });
  await page.waitForTimeout(950);
  const first = await getSnapshot(page);
  assert(first.width >= 1000 && first.height >= 700, "The canvas must render at viewport dimensions");
  assert.equal(first.motion, "running");
  await page.waitForTimeout(900);
  const second = await getSnapshot(page);
  assert.notEqual(first.image, second.image, "Realtime tunnel frames must visibly change in the browser");
  console.log("DESKTOP REALTIME MATRIX: PASS", { width: first.width, height: first.height, speed: first.speed });

  await page.getByRole("button", { name: "Pause Matrix movement" }).click();
  await page.waitForTimeout(350);
  const paused1 = await getSnapshot(page);
  await page.waitForTimeout(600);
  const paused2 = await getSnapshot(page);
  assert.equal(paused1.motion, "paused");
  assert.equal(paused1.image, paused2.image, "Paused tunnel must stop repainting");
  console.log("MATRIX PAUSE: PASS");

  await page.getByRole("button", { name: "Resume Matrix movement" }).click();
  await page.waitForTimeout(500);
  const resumed = await getSnapshot(page);
  assert.equal(resumed.motion, "running");
  assert.notEqual(paused2.image, resumed.image, "Resume must restart frame motion");
  console.log("MATRIX RESUME: PASS");

  await page.getByRole("button", { name: /Matrix speed:/ }).click();
  await page.waitForTimeout(200);
  assert.equal((await getSnapshot(page)).speed, "warp");
  console.log("WARP SPEED: PASS");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(1100);
  const mobile1 = await getSnapshot(page);
  assert(mobile1.width > 300 && mobile1.width <= 500, "Responsive canvas size");
  await page.waitForTimeout(950);
  const mobile2 = await getSnapshot(page);
  assert.notEqual(mobile1.image, mobile2.image, "Realtime tunnel must animate at mobile viewport");
  console.log("MOBILE REALTIME MATRIX: PASS", { width: mobile1.width, height: mobile1.height });

  assert.deepEqual(errors, [], "No page JavaScript errors");
  console.log("BROWSER JAVASCRIPT ERRORS: NONE");

  const reduced = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await reduced.goto(FRONT, { waitUntil: "domcontentloaded", timeout: 45000 });
  await reduced.locator("canvas.matrix-tunnel-canvas").waitFor();
  await reduced.waitForTimeout(800);
  const still1 = await getSnapshot(reduced);
  await reduced.waitForTimeout(900);
  const still2 = await getSnapshot(reduced);
  assert.equal(still1.motion, "paused");
  assert.equal(still1.image, still2.image, "Reduced-motion preference must not animate by default");
  console.log("REDUCED MOTION: PASS");
  await reduced.close();
  await page.close();
} finally {
  await browser.close();
}
