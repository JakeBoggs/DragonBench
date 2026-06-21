import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import load_jsonl
from dragonbench.scoring import parse_model_json, predicted_protein_coordinates, reference_protein_coordinates, score_answer


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DragonBench Protein Folding 3D Report</title>
  <script src="/vendor/3Dmol-min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f8;
      --panel: #ffffff;
      --border: #d9dee5;
      --text: #17202a;
      --muted: #52606d;
      --target: #22c55e;
      --prediction: #f97316;
      --model-b: #38bdf8;
      --reference: #94a3b8;
      --error: #cbd5e1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      padding: 14px 18px;
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }
    h1 { margin: 0; font-size: 18px; }
    .controls {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    select, button {
      border: 1px solid var(--border);
      background: white;
      border-radius: 6px;
      padding: 7px 9px;
      font: inherit;
    }
    button { cursor: pointer; }
    main {
      padding: 16px;
      display: grid;
      gap: 14px;
    }
    .summary {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
      display: grid;
      gap: 8px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfd;
    }
    .metric .label {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .metric .value {
      font-size: 18px;
      font-weight: 650;
    }
    .viewer-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .viewer-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      min-width: 0;
    }
    .viewer-title {
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-weight: 650;
    }
    .viewer-title .viewer-name {
      color: var(--text);
      font-weight: 650;
      font-size: 14px;
    }
    .viewer-title .viewer-subtitle {
      color: var(--muted);
      font-weight: 500;
      font-size: 12px;
    }
    .viewer {
      position: relative;
      height: 520px;
      background: #101820;
    }
    .legend {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 13px;
    }
    .swatch {
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      margin-right: 5px;
      vertical-align: -1px;
    }
    .note {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    @media (max-width: 1100px) {
      .viewer-grid { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .viewer { height: 420px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>DragonBench Protein Folding 3D Report</h1>
    <div class="controls">
      <label for="taskSelect">Task</label>
      <select id="taskSelect"></select>
      <button id="resetView">Reset View</button>
      <button id="toggleStyle">Toggle Style</button>
      <button id="toggleOffset">Offset Overlay: On</button>
    </div>
  </header>
  <main>
    <section class="summary">
      <div id="taskTitle"></div>
      <div class="metrics" id="metrics"></div>
      <div class="legend">
        <span id="legendTarget"><span class="swatch" style="background:var(--target)"></span>Ground truth structure</span>
        <span id="legendPrediction"><span class="swatch" style="background:var(--prediction)"></span>Model prediction</span>
        <span id="legendModelB" hidden><span class="swatch" style="background:var(--model-b)"></span>Model B prediction</span>
        <span id="legendReference" hidden><span class="swatch" style="background:var(--reference)"></span>Model-to-model distance links</span>
        <span id="legendError"><span class="swatch" style="background:var(--error)"></span>Residue error links</span>
      </div>
      <div class="note" id="modeNote">
        This uses 3Dmol.js. Drag to rotate, scroll to zoom, right-drag to pan. Submitted PDB/mmCIF structures render as protein cartoons when possible; parsed C-alpha coordinates drive geometry overlays.
      </div>
    </section>
    <section class="viewer-grid">
      <div class="viewer-card">
        <div class="viewer-title"><span id="panelATitle" class="viewer-name">Ground Truth</span> <span id="panelASubtitle" class="viewer-subtitle">RCSB PDB target</span></div>
        <div id="targetViewer" class="viewer"></div>
      </div>
      <div class="viewer-card">
        <div class="viewer-title"><span id="panelBTitle" class="viewer-name">Model Prediction</span> <span id="panelBSubtitle" class="viewer-subtitle">submitted coordinates</span></div>
        <div id="predictionViewer" class="viewer"></div>
      </div>
      <div class="viewer-card">
        <div class="viewer-title"><span id="panelCTitle" class="viewer-name">Overlay</span> <span id="panelCSubtitle" class="viewer-subtitle">green target, orange prediction</span></div>
        <div id="overlayViewer" class="viewer"></div>
      </div>
    </section>
  </main>
  <script>
  const DATA = __DATA__;
  const state = { taskIndex: 0, style: 'cartoon', offsetOverlay: true, renderVersion: 0 };
  const viewers = {};
  const COLORS = { target: 0x22c55e, prediction: 0xf97316, modelB: 0x38bdf8, reference: 0x94a3b8, error: 0xcbd5e1 };

  function fmt(value, digits = 3) {
    if (value === undefined || value === null || Number.isNaN(value)) return 'n/a';
    if (typeof value === 'string') return value;
    return Number(value).toFixed(digits);
  }

  function currentTask() {
    return DATA.tasks[state.taskIndex];
  }

  function applyInitialTaskFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const requestedId = params.get('task_id') || params.get('id');
    if (!requestedId) return;
    const index = DATA.tasks.findIndex(task => task.id === requestedId);
    if (index >= 0) {
      state.taskIndex = index;
    }
  }

  function updateTaskUrl(task) {
    if (!window.history || !window.history.replaceState || !task || !task.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('task_id', task.id);
    window.history.replaceState(null, '', url);
  }

  function initViewers() {
    viewers.target = $3Dmol.createViewer('targetViewer', { backgroundColor: '#101820' });
    viewers.prediction = $3Dmol.createViewer('predictionViewer', { backgroundColor: '#101820' });
    viewers.overlay = $3Dmol.createViewer('overlayViewer', { backgroundColor: '#101820' });
  }

  function setupControls() {
    const select = document.getElementById('taskSelect');
    DATA.tasks.forEach((task, index) => {
      const opt = document.createElement('option');
      opt.value = String(index);
      const pdb = task.pdb_id ? ` · ${task.pdb_id}:${task.chain_id}` : '';
      if (DATA.mode === 'compare') {
        opt.textContent = `${task.id}${pdb} · ${DATA.model_a_name} ${fmt(task.model_a.reward)} / ${DATA.model_b_name} ${fmt(task.model_b.reward)}`;
      } else {
        opt.textContent = `${task.id}${pdb} · reward ${fmt(task.reward)}`;
      }
      select.appendChild(opt);
    });
    select.value = String(state.taskIndex);
    select.addEventListener('change', () => {
      state.taskIndex = Number(select.value);
      updateTaskUrl(currentTask());
      render();
    });
    document.getElementById('resetView').addEventListener('click', () => zoomAll());
    document.getElementById('toggleStyle').addEventListener('click', () => {
      state.style = state.style === 'cartoon' ? 'trace' : 'cartoon';
      render();
    });
    document.getElementById('toggleOffset').addEventListener('click', () => {
      state.offsetOverlay = !state.offsetOverlay;
      document.getElementById('toggleOffset').textContent = `Offset Overlay: ${state.offsetOverlay ? 'On' : 'Off'}`;
      render();
    });
    window.addEventListener('resize', () => {
      Object.values(viewers).forEach(v => {
        v.resize();
        v.render();
      });
    });
  }

  function updateSummary(task) {
    const pdb = task.pdb_id ? ` · ${task.pdb_id} chain ${task.chain_id}` : '';
    let metrics;
    if (DATA.mode === 'compare') {
      const deltaReward = Number(task.model_b.reward || 0) - Number(task.model_a.reward || 0);
      const deltaDrmsd = Number(task.model_b.subscores.drmsd_angstrom || 0) - Number(task.model_a.subscores.drmsd_angstrom || 0);
      document.getElementById('taskTitle').innerHTML =
        `<strong>${task.id}${pdb}</strong><div class="note">${DATA.model_a_name}: ${task.model_a.scoring_explanation} · ${DATA.model_b_name}: ${task.model_b.scoring_explanation}</div>`;
      metrics = [
        [`${DATA.model_a_name} reward`, task.model_a.reward],
        [`${DATA.model_b_name} reward`, task.model_b.reward],
        ['Reward delta', deltaReward],
        [`${DATA.model_a_name} dRMSD`, task.model_a.subscores.drmsd_angstrom],
        [`${DATA.model_b_name} dRMSD`, task.model_b.subscores.drmsd_angstrom],
        ['dRMSD delta', deltaDrmsd],
      ];
    } else {
      document.getElementById('taskTitle').innerHTML =
        `<strong>${task.id}${pdb}</strong><div class="note">${task.scoring_explanation}</div>`;
      metrics = [
        ['Reward', task.reward],
        ['dRMSD score', task.subscores.distance_matrix_rmsd_score],
        ['Coverage', task.subscores.coordinate_coverage],
        ['Overlap residues', task.info && task.info.overlap],
        ['Pred / True residues', task.info ? `${task.info.n_pred || 0} / ${task.info.n_true || 0}` : null],
        ['dRMSD', task.subscores.drmsd_angstrom],
        ['Mean dist err', task.subscores.mean_distance_error_angstrom],
      ];
    }
    document.getElementById('metrics').innerHTML = metrics.map(([label, value]) =>
      `<div class="metric"><div class="label">${label}</div><div class="value">${fmt(value)}</div></div>`
    ).join('');
  }

  function updateModeChrome() {
    if (DATA.mode !== 'compare') {
      const modelName = DATA.model_a_name || 'Model';
      document.title = 'DragonBench Protein Folding Single-Answer Report';
      document.querySelector('h1').textContent = 'DragonBench Protein Folding Single-Answer Report';
      document.getElementById('panelATitle').textContent = 'Ground Truth';
      document.getElementById('panelASubtitle').textContent = 'reference structure';
      document.getElementById('panelBTitle').textContent = `${modelName} Prediction`;
      document.getElementById('panelBSubtitle').textContent = 'submitted model answer';
      document.getElementById('panelCTitle').textContent = `${modelName} vs Ground Truth`;
      document.getElementById('panelCSubtitle').textContent = 'green target, orange prediction';
      document.getElementById('legendPrediction').lastChild.textContent = `${modelName} prediction`;
      document.getElementById('modeNote').textContent =
        'Single-answer 3Dmol.js viewer for one submitted protein fold. Drag to rotate, scroll to zoom, right-drag to pan. Offset Overlay slightly separates the prediction from ground truth for readability; turn it off for exact aligned geometry.';
      return;
    }
    document.title = 'DragonBench Protein Folding Model Comparison';
    document.querySelector('h1').textContent = 'DragonBench Protein Folding Model Comparison';
    document.getElementById('panelATitle').textContent = `${DATA.model_a_name} vs Ground Truth`;
    document.getElementById('panelASubtitle').textContent = 'orange model, green target';
    document.getElementById('panelBTitle').textContent = `${DATA.model_b_name} vs Ground Truth`;
    document.getElementById('panelBSubtitle').textContent = 'blue model, green target';
    document.getElementById('panelCTitle').textContent = `${DATA.model_a_name} vs ${DATA.model_b_name}`;
    document.getElementById('panelCSubtitle').textContent = 'green truth, orange vs blue models';
    document.getElementById('legendPrediction').lastChild.textContent = `${DATA.model_a_name} prediction`;
    document.getElementById('legendModelB').hidden = false;
    document.getElementById('legendModelB').lastChild.textContent = `${DATA.model_b_name} prediction`;
    document.getElementById('legendReference').hidden = false;
    document.getElementById('modeNote').textContent =
      'This uses 3Dmol.js. Drag to rotate, scroll to zoom, right-drag to pan. Offset Overlay slightly separates overlapping models from ground truth for readability; turn it off for exact aligned geometry.';
  }

  function render() {
    const task = currentTask();
    const version = ++state.renderVersion;
    updateSummary(task);
    if (DATA.mode === 'compare') {
      renderModelVsTarget(viewers.target, task, task.model_a, COLORS.prediction);
      renderModelVsTarget(viewers.prediction, task, task.model_b, COLORS.modelB);
      renderModelComparison(viewers.overlay, task);
    } else {
      renderTarget(viewers.target, task);
      renderPrediction(viewers.prediction, task);
      renderOverlay(viewers.overlay, task);
    }
    if (version !== state.renderVersion) return;
    zoomAll();
  }

  function clearViewer(viewer) {
    viewer.removeAllModels();
    viewer.removeAllShapes();
    viewer.removeAllLabels();
  }

  function renderTarget(viewer, task) {
    clearViewer(viewer);
    if (!task.target_structure) {
      drawTrace(viewer, task.target_coordinates, COLORS.target, 0.2, 0.09);
      viewer.render();
      return;
    }
    addStructureModel(viewer, task.target_structure, COLORS.target, 1.0, 'target');
    viewer.render();
  }

  function renderPrediction(viewer, task) {
    clearViewer(viewer);
    if (task.predicted_structure && !useCoordinateTrace(task.info)) {
      addStructureModel(viewer, task.predicted_structure, COLORS.prediction, 1.0, 'prediction');
      viewer.render();
      return;
    }
    if (!task.predicted_coordinates || task.predicted_coordinates.length === 0) {
      viewer.addLabel('No coordinates submitted', { position: {x:0,y:0,z:0}, fontColor: 'white', backgroundColor: 'black' });
      viewer.render();
      return;
    }
    drawTrace(viewer, task.predicted_coordinates, COLORS.prediction, 0.34, 0.13);
    viewer.render();
  }

  function renderOverlay(viewer, task) {
    clearViewer(viewer);
    if (task.target_structure) {
      addStructureModel(viewer, task.target_structure, COLORS.target, 0.72, 'target');
    } else {
      drawTrace(viewer, task.target_coordinates, COLORS.target, 0.2, 0.08);
    }
    if (task.predicted_structure) {
      if (useCoordinateTrace(task.info)) {
        const offset = displayOffset(0.85);
        const coords = task.predicted_aligned_coordinates || task.predicted_coordinates;
        drawTrace(viewer, offsetCoords(coords, offset), COLORS.prediction, 0.3, 0.12);
        addErrorLinks(viewer, task.target_coordinates, offsetCoords(coords, offset));
      } else {
        addStructureModel(viewer, task.predicted_aligned_structure || task.predicted_structure, COLORS.prediction, 0.88, 'prediction', displayOffset(0.85));
      }
    } else if (task.predicted_coordinates && task.predicted_coordinates.length > 0) {
      const offset = displayOffset(0.85);
      const coords = task.predicted_aligned_coordinates || task.predicted_coordinates;
      drawTrace(viewer, offsetCoords(coords, offset), COLORS.prediction, 0.3, 0.12);
      addErrorLinks(viewer, task.target_coordinates, offsetCoords(coords, offset));
    }
    viewer.render();
  }

  function renderModelVsTarget(viewer, task, model, modelColor) {
    clearViewer(viewer);
    if (task.target_structure) {
      addStructureModel(viewer, task.target_structure, COLORS.target, 0.42, 'target');
    } else {
      drawTrace(viewer, task.target_coordinates, COLORS.target, 0.18, 0.07);
    }
    if (model.structure && !useCoordinateTrace(model.info)) {
      addStructureModel(viewer, model.aligned_structure || model.structure, modelColor, 0.9, 'prediction', displayOffset(0.85));
    } else if (model.coordinates && model.coordinates.length > 0) {
      const offset = displayOffset(0.85);
      const coords = model.aligned_coordinates || model.coordinates;
      drawTrace(viewer, offsetCoords(coords, offset), modelColor, 0.3, 0.12);
      addErrorLinks(viewer, task.target_coordinates, offsetCoords(coords, offset));
    } else {
      viewer.addLabel('No coordinates submitted', { position: {x:0,y:0,z:0}, fontColor: 'white', backgroundColor: 'black' });
    }
    viewer.render();
  }

  function renderModelComparison(viewer, task) {
    clearViewer(viewer);
    if (task.target_structure) {
      addStructureModel(viewer, task.target_structure, COLORS.target, 0.6, 'target');
    } else {
      drawTrace(viewer, task.target_coordinates, COLORS.target, 0.2, 0.08, 0.34);
    }
    if (task.model_a.structure && !useCoordinateTrace(task.model_a.info)) {
      addStructureModel(viewer, task.model_a.aligned_structure || task.model_a.structure, COLORS.prediction, 0.86, 'prediction', displayOffset(0.65));
    } else if (task.model_a.coordinates && task.model_a.coordinates.length > 0) {
      drawTrace(viewer, offsetCoords(task.model_a.aligned_coordinates || task.model_a.coordinates, displayOffset(0.65)), COLORS.prediction, 0.28, 0.11);
    }
    if (task.model_b.structure && !useCoordinateTrace(task.model_b.info)) {
      addStructureModel(viewer, task.model_b.aligned_structure || task.model_b.structure, COLORS.modelB, 0.86, 'prediction', displayOffset(-0.65));
    } else if (task.model_b.coordinates && task.model_b.coordinates.length > 0) {
      drawTrace(viewer, offsetCoords(task.model_b.aligned_coordinates || task.model_b.coordinates, displayOffset(-0.65)), COLORS.modelB, 0.28, 0.11);
    }
    addModelDeltaLinks(
      viewer,
      offsetCoords(task.model_a.aligned_coordinates || task.model_a.coordinates, displayOffset(0.65)),
      offsetCoords(task.model_b.aligned_coordinates || task.model_b.coordinates, displayOffset(-0.65))
    );
    viewer.render();
  }

  function useCoordinateTrace(info) {
    if (!info) return false;
    const backbone = Number(info.backbone_completeness);
    return Number.isFinite(backbone) && backbone < 0.5;
  }

  function addStructureModel(viewer, structure, color, opacity, kind, offset = null) {
    if (!structure || !structure.text) return null;
    const format = structure.format === 'mmcif' ? 'mmcif' : 'pdb';
    const text = offset && format === 'pdb' ? offsetPdbText(structure.text, offset) : structure.text;
    const model = viewer.addModel(text, format);
    if (state.style === 'cartoon') {
      model.setStyle({}, {
        cartoon: { color, opacity, thickness: kind === 'target' ? 0.44 : 0.38 }
      });
    } else {
      model.setStyle({}, {
        stick: { radius: kind === 'target' ? 0.12 : 0.14, color, opacity },
        sphere: { radius: kind === 'target' ? 0.18 : 0.2, color, opacity }
      });
    }
    return model;
  }

  function displayOffset(dx) {
    return state.offsetOverlay ? { x: dx, y: 0, z: 0 } : null;
  }

  function offsetCoords(coords, offset) {
    if (!offset) return coords || [];
    return (coords || []).map(c => ({
      ...c,
      x: Number(c.x) + offset.x,
      y: Number(c.y) + offset.y,
      z: Number(c.z) + offset.z,
    }));
  }

  function offsetPdbText(text, offset) {
    return text.split('\\n').map(line => {
      if (!(line.startsWith('ATOM') || line.startsWith('HETATM')) || line.length < 54) return line;
      const x = Number(line.slice(30, 38));
      const y = Number(line.slice(38, 46));
      const z = Number(line.slice(46, 54));
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return line;
      return `${line.slice(0, 30)}${formatPdbCoord(x + offset.x)}${formatPdbCoord(y + offset.y)}${formatPdbCoord(z + offset.z)}${line.slice(54)}`;
    }).join('\\n');
  }

  function formatPdbCoord(value) {
    return value.toFixed(3).padStart(8, ' ');
  }

  function drawTrace(viewer, coords, color, sphereRadius, tubeRadius, alpha = 1) {
    const clean = (coords || [])
      .map(c => ({
        residue_index: Number(c.residue_index),
        x: Number(c.x),
        y: Number(c.y),
        z: Number(c.z),
      }))
      .filter(c => Number.isFinite(c.residue_index) && Number.isFinite(c.x) && Number.isFinite(c.y) && Number.isFinite(c.z))
      .sort((a, b) => a.residue_index - b.residue_index);
    clean.forEach((c, i) => {
      viewer.addSphere({
        center: {x:c.x, y:c.y, z:c.z},
        radius: i % 5 === 0 ? sphereRadius * 1.2 : sphereRadius,
        color,
        alpha,
      });
      const next = clean[i + 1];
      if (!next || next.residue_index !== c.residue_index + 1) return;
      viewer.addCylinder({
        start: {x:c.x, y:c.y, z:c.z},
        end: {x:next.x, y:next.y, z:next.z},
        radius: tubeRadius,
        color,
        alpha,
      });
    });
  }

  function addErrorLinks(viewer, targetCoords, predCoords) {
    const predByIndex = new Map((predCoords || []).map(p => [p.residue_index, p]));
    (targetCoords || []).forEach(t => {
      if (t.residue_index % 5 !== 0) return;
      const p = predByIndex.get(t.residue_index);
      if (!p) return;
      viewer.addCylinder({
        start: {x:t.x, y:t.y, z:t.z},
        end: {x:p.x, y:p.y, z:p.z},
        radius: 0.045,
        color: COLORS.error,
        alpha: 0.42,
      });
    });
  }

  function addModelDeltaLinks(viewer, coordsA, coordsB) {
    const byIndex = new Map((coordsB || []).map(p => [p.residue_index, p]));
    (coordsA || []).forEach(a => {
      if (a.residue_index % 5 !== 0) return;
      const b = byIndex.get(a.residue_index);
      if (!b) return;
      viewer.addCylinder({
        start: {x:a.x, y:a.y, z:a.z},
        end: {x:b.x, y:b.y, z:b.z},
        radius: 0.04,
        color: COLORS.error,
        alpha: 0.36,
      });
    });
  }

  function zoomAll() {
    Object.values(viewers).forEach(v => {
      v.zoomTo();
      v.render();
    });
  }

  updateModeChrome();
  initViewers();
  applyInitialTaskFromUrl();
  setupControls();
  updateTaskUrl(currentTask());
  render();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 3Dmol protein folding report from DragonBench answer JSONL.")
    parser.add_argument("--dataset", default="eval/dragonbench_eval_v0.scoreable.jsonl")
    parser.add_argument("--answers", help="Single-model answer JSONL. Alias for --answers-a.")
    parser.add_argument("--answers-a", help="Model A answer JSONL.")
    parser.add_argument("--answers-b", default=None, help="Optional Model B answer JSONL for comparison mode.")
    parser.add_argument("--model-a-name", default="Model A")
    parser.add_argument("--model-b-name", default="Model B")
    parser.add_argument("--out", default="reports/protein_folding_3d.html")
    args = parser.parse_args()

    if args.answers_a and args.answers:
        parser.error("use either --answers-a or --answers, not both")
    if args.answers_a:
        answers_a_path = args.answers_a
    elif args.answers:
        answers_a_path = args.answers
    else:
        parser.error("one of --answers-a or --answers is required")
    cards = {row["id"]: row for row in load_jsonl(args.dataset)}
    answer_rows_a = {row["id"]: row for row in load_jsonl(answers_a_path)}
    answer_rows_b = {row["id"]: row for row in load_jsonl(args.answers_b)} if args.answers_b else None
    payload = build_report_payload(
        cards.values(),
        answer_rows_a,
        answer_rows_b=answer_rows_b,
        model_a_name=args.model_a_name,
        model_b_name=args.model_b_name,
    )
    write_report(args.out, payload)
    print(args.out)


def build_report_payload(cards, answer_rows_a, answer_rows_b=None, model_a_name="Model A", model_b_name="Model B"):
    tasks = []
    card_iter = cards.values() if isinstance(cards, dict) else cards
    for card in card_iter:
        if card["task"] not in {"KomodoProteinFold", "DragonProteinFolding"}:
            continue
        hidden = card["hidden_answer"]["answer"]
        target_structure = extract_reference_structure_payload(hidden)
        target_coord_map, _ = reference_protein_coordinates(hidden)
        target_coords = coordinates_to_rows(target_coord_map)
        task = {
            "id": card["id"],
            "task": card["task"],
            "pdb_id": hidden.get("pdb_id"),
            "chain_id": hidden.get("chain_id"),
            "target_coordinates": target_coords,
            "target_structure": target_structure,
        }
        model_a = build_model_payload(card, answer_for_task(answer_rows_a, card["id"], "model A"), target_coord_map)
        if answer_rows_b is not None:
            model_b = build_model_payload(card, answer_for_task(answer_rows_b, card["id"], "model B"), target_coord_map)
            task["model_a"] = model_a
            task["model_b"] = model_b
        else:
            task.update({
                "reward": model_a["reward"],
                "status": model_a["status"],
                "subscores": model_a["subscores"],
                "info": model_a["info"],
                "scoring_explanation": model_a["scoring_explanation"],
                "predicted_coordinates": model_a["coordinates"],
                "predicted_aligned_coordinates": model_a["aligned_coordinates"],
                "predicted_structure": model_a["structure"],
                "predicted_aligned_structure": model_a["aligned_structure"],
            })
        tasks.append(task)

    return {
        "mode": "compare" if answer_rows_b is not None else "single",
        "model_a_name": model_a_name,
        "model_b_name": model_b_name,
        "tasks": tasks,
    }


def answer_for_task(answer_rows, task_id, label):
    if task_id not in answer_rows:
        raise KeyError(f"missing {label} answer for {task_id}")
    row = answer_rows[task_id]
    if not isinstance(row, dict) or "answer" not in row:
        raise KeyError(f"{label} answer row for {task_id} must contain answer")
    return row["answer"]


def write_report(out_path, payload):
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(HTML_TEMPLATE.replace("__DATA__", json.dumps(payload)))
    return out


def build_single_task_report(card, answer, out_path, model_name="HUD Model"):
    payload = build_report_payload(
        [card],
        {card["id"]: {"id": card["id"], "answer": answer}},
        model_a_name=model_name,
    )
    return write_report(out_path, payload)


def build_model_payload(card, answer_text, target_coord_map):
    parsed, parse_error = parse_model_json(answer_text)
    result = score_answer(card, answer_text)
    coord_map = {}
    structure = None
    if parse_error is None and parsed is not None:
        coord_map, _, coordinate_error = predicted_protein_coordinates(parsed)
        if coordinate_error:
            coord_map = {}
        structure = extract_model_structure_payload(parsed)
    aligned_structure = align_structure_payload(structure, coord_map, target_coord_map)
    aligned_coord_map = align_coordinate_map(coord_map, target_coord_map)
    return {
        "reward": result.reward,
        "status": result.status,
        "subscores": result.subscores,
        "info": result.info,
        "scoring_explanation": protein_explanation(result),
        "coordinates": coordinates_to_rows(coord_map),
        "aligned_coordinates": coordinates_to_rows(aligned_coord_map),
        "structure": structure,
        "aligned_structure": aligned_structure,
    }


def coordinates_to_rows(coord_map):
    return [
        {"residue_index": idx, "x": xyz[0], "y": xyz[1], "z": xyz[2]}
        for idx, xyz in sorted(coord_map.items())
    ]


def align_coordinate_map(moving_coords, target_coords):
    common = sorted(set(moving_coords).intersection(target_coords))
    if len(common) < 3:
        return {}
    transform = kabsch_transform(
        [moving_coords[idx] for idx in common],
        [target_coords[idx] for idx in common],
    )
    if transform is None:
        return {}
    return {
        idx: transform_point(point, transform)
        for idx, point in moving_coords.items()
    }


def extract_model_structure_payload(record):
    if not isinstance(record, dict):
        return None
    if isinstance(record.get("pdb"), str) and record["pdb"].strip():
        return structure_payload(record["pdb"], "pdb")
    if isinstance(record.get("mmcif"), str) and record["mmcif"].strip():
        return structure_payload(record["mmcif"], "mmcif")
    return None


def extract_reference_structure_payload(record):
    if not isinstance(record, dict):
        return None
    if isinstance(record.get("pdb"), str) and record["pdb"].strip():
        return structure_payload(record["pdb"], "pdb")
    if isinstance(record.get("mmcif"), str) and record["mmcif"].strip():
        return structure_payload(record["mmcif"], "mmcif")
    raw_path = record.get("raw_pdb_path")
    if isinstance(raw_path, str) and raw_path:
        path = Path(raw_path)
        if path.exists():
            return structure_payload(path.read_text(errors="ignore"), "pdb")
    return None


def structure_payload(text, fmt):
    if not isinstance(text, str) or not text.strip():
        return None
    return {"text": text.strip(), "format": "mmcif" if fmt == "mmcif" else "pdb"}


def kabsch_transform(moving, target):
    moving_array = np.asarray(moving, dtype=float)
    target_array = np.asarray(target, dtype=float)
    if moving_array.shape != target_array.shape or moving_array.ndim != 2 or moving_array.shape[1] != 3:
        return None
    moving_centroid = moving_array.mean(axis=0)
    target_centroid = target_array.mean(axis=0)
    moving_centered = moving_array - moving_centroid
    target_centered = target_array - target_centroid
    covariance = moving_centered.T @ target_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T
    return {
        "rotation": rotation.tolist(),
        "moving_centroid": moving_centroid.tolist(),
        "target_centroid": target_centroid.tolist(),
    }


def transform_point(point, transform):
    x = point[0] - transform["moving_centroid"][0]
    y = point[1] - transform["moving_centroid"][1]
    z = point[2] - transform["moving_centroid"][2]
    r = transform["rotation"]
    return (
        r[0][0] * x + r[0][1] * y + r[0][2] * z + transform["target_centroid"][0],
        r[1][0] * x + r[1][1] * y + r[1][2] * z + transform["target_centroid"][1],
        r[2][0] * x + r[2][1] * y + r[2][2] * z + transform["target_centroid"][2],
    )


def transform_pdb_coordinates(text, transform):
    lines = []
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 54:
            try:
                xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            except ValueError:
                lines.append(line)
                continue
            x, y, z = transform_point(xyz, transform)
            lines.append(f"{line[:30]}{x:8.3f}{y:8.3f}{z:8.3f}{line[54:]}")
        else:
            lines.append(line)
    return "\n".join(lines)


def align_structure_payload(structure, moving_coords, target_coords):
    if not structure or structure.get("format") != "pdb":
        return None
    common = sorted(set(moving_coords).intersection(target_coords))
    if len(common) < 3:
        return None
    transform = kabsch_transform(
        [moving_coords[idx] for idx in common],
        [target_coords[idx] for idx in common],
    )
    if transform is None:
        return None
    aligned_text = transform_pdb_coordinates(structure["text"], transform)
    return structure_payload(aligned_text, "pdb")


def protein_explanation(result):
    s = result.subscores
    if result.status != "scored":
        return f"status={result.status}; reward={result.reward:.3f}; info={json.dumps(result.info, sort_keys=True)}"
    return (
        f"reward=coverage * local_structure_score; "
        f"coverage={s['coordinate_coverage']:.3f}, "
        f"local_structure={s['local_structure_score']:.3f}, "
        f"dRMSD score={s['distance_matrix_rmsd_score']:.3f}, "
        f"dRMSD={s['drmsd_angstrom']:.3f}"
    )


if __name__ == "__main__":
    main()
