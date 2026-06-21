import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const runtimeRequire = createRequire(
  "/Users/ibrahim/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json",
);
const { chromium } = runtimeRequire("playwright");

const DEFAULT_BASE_URL =
  "http://127.0.0.1:8765/reports/hackathon_visualizations/protein_folds";
const DEFAULT_OUT_DIR = "reports/hackathon_images/protein_all";
const DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const PROTEIN_TASK_IDS = Array.from({ length: 20 }, (_, index) => {
  return `DBEVAL-V0-${String(41 + index).padStart(3, "0")}`;
});

const REPORTS = [
  ["single", "gpt5_vs_truth", "single/gpt5_vs_truth.html"],
  ["single", "gpt54_vs_truth", "single/gpt54_vs_truth.html"],
  ["single", "gpt5mini_vs_truth", "single/gpt5mini_vs_truth.html"],
  ["single", "gpt54mini_vs_truth", "single/gpt54mini_vs_truth.html"],
  ["single", "gpt4o_vs_truth", "single/gpt4o_vs_truth.html"],
  ["compare", "gpt5_vs_gpt54", "compare/gpt5_vs_gpt54.html"],
  ["compare", "gpt5_vs_gpt5mini", "compare/gpt5_vs_gpt5mini.html"],
  ["compare", "gpt5_vs_gpt54mini", "compare/gpt5_vs_gpt54mini.html"],
  ["compare", "gpt54_vs_gpt5mini", "compare/gpt54_vs_gpt5mini.html"],
  ["compare", "gpt54_vs_gpt54mini", "compare/gpt54_vs_gpt54mini.html"],
  ["compare", "gpt5mini_vs_gpt54mini", "compare/gpt5mini_vs_gpt54mini.html"],
  ["compare", "gpt54_vs_gpt4o", "compare/gpt54_vs_gpt4o.html"],
];

function argValue(name, fallback) {
  const prefix = `--${name}=`;
  const value = process.argv.find((arg) => arg.startsWith(prefix));
  return value ? value.slice(prefix.length) : fallback;
}

const baseUrl = argValue("base-url", DEFAULT_BASE_URL).replace(/\/$/, "");
const outDir = argValue("out-dir", DEFAULT_OUT_DIR);
const chromePath = argValue("chrome", DEFAULT_CHROME);
const width = Number(argValue("width", "1800"));
const height = Number(argValue("height", "1200"));
const waitMs = Number(argValue("wait-ms", "3500"));
const offsetOverlay = argValue("offset-overlay", "off");
const concurrency = Number(argValue("concurrency", "6"));

if (!["on", "off"].includes(offsetOverlay)) {
  throw new Error("--offset-overlay must be either 'on' or 'off'");
}

if (!Number.isInteger(concurrency) || concurrency < 1) {
  throw new Error("--concurrency must be a positive integer");
}

async function setOffsetOverlay(page) {
  const toggle = page.locator("#toggleOffset");
  const currentText = (await toggle.textContent({ timeout: 10_000 })).trim();
  const isOn = currentText.endsWith("On");
  if ((offsetOverlay === "on") !== isOn) {
    await toggle.click();
    await page.waitForTimeout(500);
  }
  await page.locator("#resetView").click();
  await page.waitForTimeout(500);
}

await fs.mkdir(outDir, { recursive: true });

const jobs = [];
for (const [group, reportName, reportPath] of REPORTS) {
  const groupDir = path.join(outDir, group);
  await fs.mkdir(groupDir, { recursive: true });
  for (const taskId of PROTEIN_TASK_IDS) {
    jobs.push({
      groupDir,
      reportName,
      url: `${baseUrl}/${reportPath}?task_id=${taskId}`,
      outputPath: path.join(groupDir, `${reportName}_${taskId}.png`),
    });
  }
}

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
});

try {
  let count = 0;
  let nextIndex = 0;

  async function worker(workerId) {
    const page = await browser.newPage({
      viewport: { width, height },
      deviceScaleFactor: 1,
    });
    try {
      while (nextIndex < jobs.length) {
        const job = jobs[nextIndex];
        nextIndex += 1;

        await page.goto(job.url, { waitUntil: "networkidle", timeout: 60_000 });
        await setOffsetOverlay(page);
        await page.waitForTimeout(waitMs);
        await page.screenshot({ path: job.outputPath, fullPage: false });
        count += 1;
        console.log(
          `${count}/${jobs.length} worker=${workerId} ${job.outputPath}`,
        );
      }
    } finally {
      await page.close();
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, jobs.length) }, (_, index) =>
      worker(index + 1),
    ),
  );
} finally {
  await browser.close();
}
