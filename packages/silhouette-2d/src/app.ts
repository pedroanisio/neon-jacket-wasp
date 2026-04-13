/**
 * Main application — wires mesh, bones, animation, renderer, and UI.
 */

import {
  buildBoneDefs,
  buildBoneIndex,
  computeVertexWeights,
  deformMesh,
  getWeights,
  initBones,
  updateBones,
} from "./bones.js";
import { loadV4Json, type LoadedData } from "./loader.js";
import { buildMesh } from "./mesh.js";
import { DEFAULT_PRESET, PRESETS } from "./presets.js";
import {
  drawCoM,
  drawGrid,
  drawJoints,
  drawMeshFill,
  drawMeshWireframe,
  drawOutline,
  drawSkeleton,
  drawStrokes,
  setViewport,
} from "./renderer.js";
import type {
  BoneState,
  DisplayToggles,
  Mesh,
  SkinWeights,
  StrokeInput,
  Vec2,
} from "./types.js";

// ── State ──

let mesh: Mesh;
let bones: BoneState[];
let boneIndex: Map<string, number>;
let vertexWeights: SkinWeights[];
let strokeData: StrokeInput[] = [];
let strokeWeights: SkinWeights[][] = [];
let comWeights: SkinWeights = [[0, 1.0]];
let activePreset: string = DEFAULT_PRESET;
let manualOverrides: Record<string, number> = {};
let animTime = 0;
let lastTs = 0;
let speed = 1.0;
let playing = true;
let mirrored = true;

const display: DisplayToggles = {
  fill: true, outline: true, strokes: true, skeleton: true,
  joints: true, labels: false, com: true, grid: false, mesh: false,
};

// ── Canvas ──

const canvas = document.getElementById("canvas") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;
let W = 0;
let H = 0;

function resize(): void {
  const panelW = 280;
  W = canvas.width = window.innerWidth - panelW;
  H = canvas.height = window.innerHeight;
  setViewport(W, H);
}

// ── Data loading ──

function initFromData(data: LoadedData): void {
  mirrored = data.mirrored;

  // Build mesh with proper leg topology
  mesh = buildMesh(
    data.contour,
    data.mirrored,
    data.scanlines ?? undefined,
    data.crotchDy ?? undefined,
  );

  // Build bone system — pass width profile and figure height for
  // adaptive placement on armored/clothed figures.
  const defs = buildBoneDefs(data.landmarks, data.widthProfile, data.figureHeight);
  bones = initBones(defs);
  boneIndex = buildBoneIndex(bones);

  // Compute per-vertex skin weights — pass body regions and width
  // profile for region-aware blending.
  vertexWeights = computeVertexWeights(
    mesh.vertices,
    data.landmarks,
    boneIndex,
    data.widthProfile,
    data.bodyRegions,
    data.figureHeight,
  );

  // Compute stroke weights
  strokeData = [];
  strokeWeights = [];
  const bh = data.figureHeight * 0.044;
  const emptyRegions = new Map<string, [number, number]>();
  for (const r of data.bodyRegions) {
    emptyRegions.set(r.name, [r.dyStart, r.dyEnd]);
  }
  // Arm threshold from width profile or landmark
  let armThreshold = (data.landmarks["waist_valley"]?.[0] ?? 0.55) * 1.05;
  if (data.widthProfile.length > 0) {
    const wDy = data.landmarks["waist_valley"]?.[1] ?? 2.8;
    for (const s of data.widthProfile) {
      if (Math.abs(s.dy - wDy) <= 0.2 && s.dx * 0.95 > armThreshold) {
        armThreshold = s.dx * 0.95;
      }
    }
  }
  for (const s of data.strokes) {
    const wts = s.points.map((p: Vec2) =>
      getWeights(p[0], p[1], data.landmarks, boneIndex, armThreshold, bh, emptyRegions),
    );
    strokeData.push(s);
    strokeWeights.push(wts);

    if (data.mirrored) {
      const mirPts: Vec2[] = s.points.map((p: Vec2) => [-p[0], p[1]] as const);
      const mirWts = mirPts.map((mp: Vec2) =>
        getWeights(mp[0], mp[1], data.landmarks, boneIndex, armThreshold, bh, emptyRegions),
      );
      strokeData.push({ points: mirPts });
      strokeWeights.push(mirWts);
    }
  }

  // CoM weights — use biomechanics whole_body_com dy if available
  const comDy = data.figureHeight * 0.465;
  comWeights = getWeights(0, comDy, data.landmarks, boneIndex, armThreshold, bh, emptyRegions);

  // Reset animation
  manualOverrides = {};
  animTime = 0;

  // Rebuild UI
  buildBoneSliders();
  updateLoadStatus(`${mesh.vertices.length} verts, ${mesh.triangles.length} tris, ${bones.length} bones`);
}

// ── Default data ──

// Compact embedded data for initial display (same as silhouette.html)
function loadDefaultData(): void {
  // Use fetch to load the generated_v4.json if available, otherwise
  // show a message asking to load a file
  updateLoadStatus("Load a v4 JSON file to begin");
}

// ── Animation ──

function applyPreset(t: number): void {
  const fn = PRESETS[activePreset];
  if (!fn) return;
  const angles = fn(t);
  for (const b of bones) {
    if (manualOverrides[b.name] !== undefined) {
      b.angle = manualOverrides[b.name]!;
    } else {
      b.angle = angles[b.name] ?? 0;
    }
  }
}

function render(ts: number): void {
  if (!lastTs) lastTs = ts;
  const dt = (ts - lastTs) / 1000;
  lastTs = ts;

  if (playing) animTime += dt * speed;

  if (!mesh || !bones) {
    ctx.clearRect(0, 0, W, H);
    requestAnimationFrame(render);
    return;
  }

  // Animate
  applyPreset(animTime);
  updateBones(bones);

  // Deform mesh
  const deformed = deformMesh(mesh.vertices, vertexWeights, bones);

  // Clear
  ctx.clearRect(0, 0, W, H);

  // Render layers
  if (display.grid) drawGrid(ctx, W);
  if (display.fill) drawMeshFill(ctx, deformed, mesh.triangles);
  if (display.mesh) drawMeshWireframe(ctx, deformed, mesh.triangles);
  if (display.outline) drawOutline(ctx, deformed, mesh.boundaryLoop);
  if (display.strokes && strokeData.length > 0) {
    drawStrokes(ctx, strokeData, strokeWeights, bones, mirrored);
  }
  if (display.skeleton) drawSkeleton(ctx, bones);
  if (display.joints) drawJoints(ctx, bones, display.labels);
  if (display.com) drawCoM(ctx, bones, comWeights);

  // Stats
  updateStats();

  requestAnimationFrame(render);
}

// ── UI ──

function updateLoadStatus(msg: string): void {
  const el = document.getElementById("load-status");
  if (el) {
    el.textContent = msg;
    el.style.color = "rgba(100,255,150,0.6)";
  }
}

function updateStats(): void {
  const el = document.getElementById("stats");
  if (!el || !bones) return;
  const PI = Math.PI;
  const angleStrs = bones.map((b) =>
    `<div class="stat"><span>${b.name}</span><span class="stat-v">${(b.angle * 180 / PI).toFixed(1)}°</span></div>`,
  ).join("");
  el.innerHTML = `
    <div class="stat"><span>vertices</span><span class="stat-v">${mesh?.vertices.length ?? 0}</span></div>
    <div class="stat"><span>triangles</span><span class="stat-v">${mesh?.triangles.length ?? 0}</span></div>
    <div class="stat"><span>bones</span><span class="stat-v">${bones.length}</span></div>
    <div class="stat"><span>preset</span><span class="stat-v">${activePreset}</span></div>
    <div class="stat"><span>time</span><span class="stat-v">${animTime.toFixed(1)}s</span></div>
    <div style="margin-top:6px;border-top:1px solid rgba(100,120,180,0.08);padding-top:6px">
    ${angleStrs}</div>
  `;
}

function buildPresetButtons(): void {
  const el = document.getElementById("presets");
  if (!el) return;
  el.innerHTML = "";
  for (const name of Object.keys(PRESETS)) {
    const btn = document.createElement("button");
    btn.className = "btn" + (name === activePreset ? " active" : "");
    btn.textContent = name;
    btn.onclick = () => {
      activePreset = name;
      manualOverrides = {};
      el.querySelectorAll(".btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll<HTMLInputElement>(".bone-slider").forEach((sl) => {
        sl.value = "0";
      });
    };
    el.appendChild(btn);
  }
}

function buildBoneSliders(): void {
  const el = document.getElementById("bone-sliders");
  if (!el || !bones) return;
  el.innerHTML = "";
  const PI = Math.PI;
  for (const b of bones) {
    const row = document.createElement("div");
    row.className = "slider-row";
    const lbl = document.createElement("span");
    lbl.className = "slider-label";
    lbl.textContent = b.name;
    const sl = document.createElement("input");
    sl.type = "range";
    sl.className = "bone-slider";
    sl.min = "-90"; sl.max = "90"; sl.value = "0"; sl.step = "0.5";
    const val = document.createElement("span");
    val.className = "slider-val";
    val.textContent = "0°";
    sl.oninput = () => {
      const deg = parseFloat(sl.value);
      val.textContent = deg.toFixed(1) + "°";
      if (Math.abs(deg) < 0.3) {
        delete manualOverrides[b.name];
      } else {
        manualOverrides[b.name] = deg * PI / 180;
      }
    };
    row.appendChild(lbl);
    row.appendChild(sl);
    row.appendChild(val);
    el.appendChild(row);
  }
}

function buildToggles(): void {
  const el = document.getElementById("toggles");
  if (!el) return;
  for (const key of Object.keys(display) as Array<keyof DisplayToggles>) {
    const row = document.createElement("div");
    row.className = "toggle-row";
    const dot = document.createElement("div");
    dot.className = "toggle-dot" + (display[key] ? " on" : "");
    const lbl = document.createElement("span");
    lbl.className = "toggle-label";
    lbl.textContent = key;
    row.onclick = () => {
      display[key] = !display[key];
      dot.classList.toggle("on");
    };
    row.appendChild(dot);
    row.appendChild(lbl);
    el.appendChild(row);
  }
}

function setupFileLoader(): void {
  const fileInput = document.getElementById("file-input") as HTMLInputElement;
  const loadBtn = document.getElementById("load-btn");
  const loadStatus = document.getElementById("load-status");

  loadBtn?.addEventListener("click", () => fileInput?.click());

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    if (loadStatus) {
      loadStatus.style.color = "#404860";
      loadStatus.textContent = "Loading…";
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const json = JSON.parse(ev.target?.result as string) as Record<string, unknown>;
        const data = loadV4Json(json);
        initFromData(data);
      } catch (err) {
        if (loadStatus) {
          loadStatus.style.color = "#ef4444";
          loadStatus.textContent = (err as Error).message;
        }
      }
    };
    reader.onerror = () => {
      if (loadStatus) {
        loadStatus.style.color = "#ef4444";
        loadStatus.textContent = "Failed to read file.";
      }
    };
    reader.readAsText(file);
    fileInput.value = "";
  });
}

function setupSpeedSlider(): void {
  const slider = document.getElementById("speed") as HTMLInputElement;
  const val = document.getElementById("speed-val");
  slider?.addEventListener("input", () => {
    speed = parseFloat(slider.value) / 100;
    if (val) val.textContent = speed.toFixed(1) + "×";
  });
}

// ── Init ──

export function init(): void {
  window.addEventListener("resize", resize);
  resize();
  buildPresetButtons();
  buildToggles();
  setupFileLoader();
  setupSpeedSlider();
  loadDefaultData();
  requestAnimationFrame(render);
}


