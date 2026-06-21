import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const runtimeRequire = createRequire(
  "/Users/ibrahim/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json",
);
const { chromium } = runtimeRequire("playwright");
const sharp = runtimeRequire("sharp");

const DEFAULT_BASE_URL =
  "http://127.0.0.1:8765/reports/modal_full_run/protein_folds/high_contrast";
const DEFAULT_INDEX =
  "reports/modal_full_run/protein_folds/high_contrast/images/render_only_labeled/render_image_index.csv";
const DEFAULT_OUT_DIR =
  "reports/modal_full_run/protein_folds/high_contrast/images/render_only_high_res";
const DEFAULT_CHROME =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function argValue(name, fallback) {
  const prefix = `--${name}=`;
  const value = process.argv.find((arg) => arg.startsWith(prefix));
  return value ? value.slice(prefix.length) : fallback;
}

function csvCells(line) {
  const cells = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      cells.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current);
  return cells;
}

async function readCsv(filePath) {
  const text = await fs.readFile(filePath, "utf8");
  const lines = text.trim().split(/\r?\n/);
  const headers = csvCells(lines.shift());
  return lines.map((line) => {
    const values = csvCells(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function comparisonSlug(row) {
  return path.basename(row.overlay_file).replace(/_DBEVAL-V0-\d+_overlay\.png$/, "");
}

function reportSlug(row) {
  return comparisonSlug(row).replace(/_DBEVAL.*/, "");
}

function ensureRelative(filePath) {
  return filePath.replace(/^\/Users\/ibrahim\/Coding\/DragonBench\//, "");
}

async function captureCanvas(page, selector, outputPath) {
  const canvas = page.locator(`${selector} canvas`).first();
  await canvas.waitFor({ state: "visible", timeout: 60_000 });
  await canvas.screenshot({ path: outputPath, animations: "disabled" });
}

async function makeTriptych(paths, outputPath) {
  const images = await Promise.all(paths.map((filePath) => sharp(filePath).metadata()));
  const width = Math.max(...images.map((image) => image.width ?? 0));
  const height = Math.max(...images.map((image) => image.height ?? 0));
  const canvas = sharp({
    create: {
      width: width * paths.length,
      height,
      channels: 4,
      background: "#f8fafc",
    },
  });
  await canvas
    .composite(
      paths.map((filePath, index) => ({
        input: filePath,
        left: width * index,
        top: 0,
      })),
    )
    .png()
    .toFile(outputPath);
}

function markdownIndex(rows) {
  const lines = [
    "# High-Resolution Protein Fold Render Image Index",
    "",
    "All paths are relative to this directory:",
    "`reports/modal_full_run/protein_folds/high_contrast/images/render_only_high_res/`",
    "",
    "The PNGs are unannotated canvas captures at higher resolution than `render_only_labeled/`.",
    "",
    "| Task | Good model | Good reward | Good render | Bad model | Bad reward | Bad render | Overlay | Triptych |",
    "|---|---|---:|---|---|---:|---|---|---|",
  ];
  for (const row of rows) {
    lines.push(
      `| ${row.task_id} | ${row.good_model} | ${Number(row.good_reward).toFixed(3)} | ` +
        `[${path.basename(row.good_file)}](${row.good_file}) | ${row.bad_model} | ` +
        `${Number(row.bad_reward).toFixed(3)} | [${path.basename(row.bad_file)}](${row.bad_file}) | ` +
        `[${path.basename(row.overlay_file)}](${row.overlay_file}) | ` +
        `[${path.basename(row.triptych_file)}](${row.triptych_file}) |`,
    );
  }
  return `${lines.join("\n")}\n`;
}

const baseUrl = argValue("base-url", DEFAULT_BASE_URL).replace(/\/$/, "");
const indexPath = argValue("index", DEFAULT_INDEX);
const outDir = argValue("out-dir", DEFAULT_OUT_DIR);
const chromePath = argValue("chrome", DEFAULT_CHROME);
const width = Number(argValue("width", "3600"));
const height = Number(argValue("height", "1500"));
const deviceScaleFactor = Number(argValue("device-scale-factor", "2"));
const waitMs = Number(argValue("wait-ms", "3000"));
const concurrency = Number(argValue("concurrency", "3"));

if (!Number.isInteger(concurrency) || concurrency < 1) {
  throw new Error("--concurrency must be a positive integer");
}

const rows = await readCsv(indexPath);
for (const subdir of [
  "individual",
  "individual_by_comparison",
  "individual_named",
  "overlays",
  "triptychs",
]) {
  await fs.mkdir(path.join(outDir, subdir), { recursive: true });
}

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
});

const outputRows = [];
const namedRows = new Map();
let nextIndex = 0;
let completed = 0;

try {
  async function worker(workerId) {
    const page = await browser.newPage({
      viewport: { width, height },
      deviceScaleFactor,
    });
    try {
      while (nextIndex < rows.length) {
        const row = rows[nextIndex];
        nextIndex += 1;

        const report = reportSlug(row);
        const slug = comparisonSlug(row);
        const url = `${baseUrl}/compare/${report}.html?task_id=${row.task_id}`;
        await page.goto(url, { waitUntil: "networkidle", timeout: 90_000 });
        await page.addStyleTag({
          content: `
            header, .summary, .viewer-title { display: none !important; }
            main { padding: 0 !important; }
            .viewer-grid { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; gap: 0 !important; }
            .viewer-card { border: 0 !important; border-radius: 0 !important; background: #f8fafc !important; }
            .viewer { height: ${height}px !important; background: #f8fafc !important; }
          `,
        });

        const toggle = page.locator("#toggleOffset");
        const toggleText = (await toggle.textContent({ timeout: 30_000 })).trim();
        if (toggleText.endsWith("On")) {
          await page.evaluate(() => document.querySelector("#toggleOffset")?.click());
        }
        await page.evaluate(() => document.querySelector("#resetView")?.click());
        await page.waitForTimeout(waitMs);

        const goodFile = path.basename(row.good_file);
        const badFile = path.basename(row.bad_file);
        const overlayFile = path.basename(row.overlay_file);
        const triptychFile = path.basename(row.triptych_file);
        const goodByComparison = path.join(outDir, "individual_by_comparison", goodFile);
        const badByComparison = path.join(outDir, "individual_by_comparison", badFile);
        const overlayPath = path.join(outDir, "overlays", overlayFile);
        const triptychPath = path.join(outDir, "triptychs", triptychFile);

        await captureCanvas(page, "#targetViewer", goodByComparison);
        await captureCanvas(page, "#predictionViewer", badByComparison);
        await captureCanvas(page, "#overlayViewer", overlayPath);
        await makeTriptych([goodByComparison, badByComparison, overlayPath], triptychPath);

        const goodShort = goodFile
          .replace(/__comparison_.+$/, "_vs_truth.png")
          .replace(/^DBEVAL-V0-(\d+)_/, "DBEVAL-V0-$1_");
        const badShort = badFile
          .replace(/__comparison_.+$/, "_vs_truth.png")
          .replace(/^DBEVAL-V0-(\d+)_/, "DBEVAL-V0-$1_");
        const goodNamed = path.join(outDir, "individual_named", goodShort);
        const badNamed = path.join(outDir, "individual_named", badShort);
        if (!namedRows.has(goodShort)) {
          await fs.copyFile(goodByComparison, goodNamed);
          namedRows.set(goodShort, {
            task_id: row.task_id,
            model: row.good_model,
            role: "higher_score",
            reward: row.good_reward,
            file: `individual_named/${goodShort}`,
          });
        }
        if (!namedRows.has(badShort)) {
          await fs.copyFile(badByComparison, badNamed);
          namedRows.set(badShort, {
            task_id: row.task_id,
            model: row.bad_model,
            role: "lower_score",
            reward: row.bad_reward,
            file: `individual_named/${badShort}`,
          });
        }

        await fs.copyFile(goodByComparison, path.join(outDir, "individual", `${row.task_id}_${slug}_good.png`));
        await fs.copyFile(badByComparison, path.join(outDir, "individual", `${row.task_id}_${slug}_bad.png`));

        outputRows.push({
          task_id: row.task_id,
          good_model: row.good_model,
          good_reward: row.good_reward,
          bad_model: row.bad_model,
          bad_reward: row.bad_reward,
          delta: row.delta,
          good_file: ensureRelative(path.relative(outDir, goodByComparison)),
          bad_file: ensureRelative(path.relative(outDir, badByComparison)),
          overlay_file: ensureRelative(path.relative(outDir, overlayPath)),
          triptych_file: ensureRelative(path.relative(outDir, triptychPath)),
        });
        completed += 1;
        console.log(`${completed}/${rows.length} worker=${workerId} ${row.task_id} ${report}`);
      }
    } finally {
      await page.close();
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, rows.length) }, (_, index) =>
      worker(index + 1),
    ),
  );
} finally {
  await browser.close();
}

outputRows.sort((a, b) => rows.findIndex((row) => row.task_id === a.task_id && row.bad_model === a.bad_model) -
  rows.findIndex((row) => row.task_id === b.task_id && row.bad_model === b.bad_model));

const header = [
  "task_id",
  "good_model",
  "good_reward",
  "bad_model",
  "bad_reward",
  "delta",
  "good_file",
  "bad_file",
  "overlay_file",
  "triptych_file",
];
const csv = [header.join(",")]
  .concat(outputRows.map((row) => header.map((key) => JSON.stringify(row[key] ?? "")).join(",")))
  .join("\n");
await fs.writeFile(path.join(outDir, "render_image_index.csv"), `${csv}\n`);
await fs.writeFile(path.join(outDir, "render_only_index.csv"), `${csv}\n`);
await fs.writeFile(path.join(outDir, "IMAGE_INDEX.md"), markdownIndex(outputRows));

const namedHeader = ["task_id", "model", "role", "reward", "file"];
const namedCsv = [namedHeader.join(",")]
  .concat(
    Array.from(namedRows.values()).map((row) =>
      namedHeader.map((key) => JSON.stringify(row[key] ?? "")).join(","),
    ),
  )
  .join("\n");
await fs.writeFile(path.join(outDir, "individual_named", "individual_named_index.csv"), `${namedCsv}\n`);
