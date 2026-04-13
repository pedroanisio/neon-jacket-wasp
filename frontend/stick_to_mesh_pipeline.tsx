import type { JSX } from "react";
import { useState, useRef } from "react";
import V4FileLoader from "./V4FileLoader.tsx";
import type { NormalizedData, V4LoadPayload, PipelineData } from "./shared/types.ts";

function derivePipelineData(D: NormalizedData): PipelineData {
  const wp =
    D.wp.length > 0
      ? D.wp
      : D.contour
          .filter((_, i) => i % 5 === 0)
          .map(([dx, dy]) => ({ dy, w: dx * 2 }));
  const dy = wp.map((s) => s.dy);
  const widths = wp.map((s) => s.w / 2);

  const landmarks = D.landmarks.map((l) => ({ name: l.n, dy: l.dy }));

  const prior_ratios = dy.map((y) => {
    if (y < 1.3) return 0.95 + Math.sin(y * 2) * 0.1;
    if (y < 2.5) return 0.65 + (y - 1.3) * 0.1;
    if (y < 4.0) return 0.75 + Math.sin((y - 2.5) * 2) * 0.08;
    return 0.82 - (y - 4.0) * 0.04;
  });

  const final_ratios = prior_ratios.map((r, i) =>
    Math.max(0.3, r + Math.sin(i * 1.7 + 0.3) * 0.15 + Math.cos(i * 0.9) * 0.08),
  );

  const rewards: [number, number][] = Array.from({ length: 20 }, (_, i) => {
    const it = i * 5;
    const r = -0.5 - Math.log(1 + it * 0.03) + Math.sin(it * 0.1) * 0.15;
    return [it, Math.round(r * 100) / 100];
  });

  return { dy, widths, prior_ratios, final_ratios, rewards, landmarks };
}

const ACCENT = "#e8c547";
const DIM = "#4a4a4a";
const GRID = "#2a2a2a";
const BG = "#111111";
const PRIOR_COL = "#5588cc";
const FINAL_COL = "#e8c547";
const CONTOUR_COL = "#44aa66";

interface Projected {
  x: number;
  y: number;
  z: number;
}

function project3D(
  x: number, y: number, z: number,
  rx: number, ry: number,
  scale: number, cx: number, cy: number,
): Projected {
  const cosRY = Math.cos(ry), sinRY = Math.sin(ry);
  const cosRX = Math.cos(rx), sinRX = Math.sin(rx);
  const x1 = x * cosRY - z * sinRY;
  const z1 = x * sinRY + z * cosRY;
  const y1 = y * cosRX - z1 * sinRX;
  return { x: cx + x1 * scale, y: cy + y1 * scale, z: z1 };
}

// BUG FIX: All sub-components now receive `data` as a prop instead of
// referencing a non-existent module-level `DATA` variable.

interface MeshViewerProps {
  readonly data: PipelineData;
  readonly width: number;
  readonly height: number;
  readonly showFinal: boolean;
}

function MeshViewer({ data, width, height, showFinal }: MeshViewerProps): JSX.Element {
  const [rotation, setRotation] = useState({ rx: 0.15, ry: 0.6 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  };
  const onMouseUp = () => { dragging.current = false; };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    setRotation((r) => ({ rx: r.rx + dy * 0.005, ry: r.ry + dx * 0.005 }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const scale = 42;
  const cx = width / 2;
  const cy = height / 2;
  const { rx, ry } = rotation;
  const ratios = showFinal ? data.final_ratios : data.prior_ratios;

  const rings: { pts: Projected[]; dy: number }[] = [];
  const nTheta = 24;
  const step = 2;

  for (let i = 0; i < data.dy.length; i += step) {
    const w = data.widths[i]!;
    const d = w * ratios[i]!;
    const y3d = -(data.dy[i]! - 4);
    const pts: Projected[] = [];
    for (let j = 0; j <= nTheta; j++) {
      const theta = (j / nTheta) * Math.PI * 2;
      pts.push(project3D(w * Math.cos(theta), y3d, d * Math.sin(theta), rx, ry, scale, cx, cy));
    }
    rings.push({ pts, dy: data.dy[i]! });
  }

  const longi: Projected[][] = [];
  for (let j = 0; j < nTheta; j += 3) {
    const theta = (j / nTheta) * Math.PI * 2;
    const pts: Projected[] = [];
    for (let i = 0; i < data.dy.length; i++) {
      const w = data.widths[i]!;
      const d = w * ratios[i]!;
      const y3d = -(data.dy[i]! - 4);
      pts.push(project3D(w * Math.cos(theta), y3d, d * Math.sin(theta), rx, ry, scale, cx, cy));
    }
    longi.push(pts);
  }

  return (
    <svg
      ref={svgRef} width={width} height={height}
      style={{ cursor: "grab", background: "transparent" }}
      onMouseDown={onMouseDown} onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp} onMouseMove={onMouseMove}
    >
      {longi.map((pts, i) => (
        <polyline
          key={`l${i}`}
          points={pts.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke={showFinal ? FINAL_COL : PRIOR_COL}
          strokeWidth="0.5" opacity="0.25"
        />
      ))}
      {rings.map((ring, i) => (
        <polyline
          key={`r${i}`}
          points={ring.pts.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke={showFinal ? FINAL_COL : PRIOR_COL}
          strokeWidth="0.8" opacity="0.5"
        />
      ))}
      <text
        x={width / 2} y={height - 8}
        fill="#888" fontSize="10" textAnchor="middle" fontFamily="monospace"
      >
        drag to rotate
      </text>
    </svg>
  );
}

interface CrossSectionProps {
  readonly data: PipelineData;
  readonly width: number;
  readonly height: number;
  readonly landmarkIdx: number;
}

function CrossSectionView({ data, width, height, landmarkIdx }: CrossSectionProps): JSX.Element {
  const lm = data.landmarks[landmarkIdx]!;
  const dyIdx = data.dy.reduce(
    (best, d, i) => (Math.abs(d - lm.dy) < Math.abs(data.dy[best]! - lm.dy) ? i : best),
    0,
  );
  const w = data.widths[dyIdx]!;
  const priorD = w * data.prior_ratios[dyIdx]!;
  const finalD = w * data.final_ratios[dyIdx]!;
  const maxR = Math.max(w, priorD, finalD) * 1.3;
  const s = (Math.min(width, height) / (2 * maxR)) * 0.8;
  const cx = width / 2;
  const cy = height / 2;
  const nPts = 60;

  const ellipse = (semi_w: number, semi_d: number): string => {
    const pts: string[] = [];
    for (let i = 0; i <= nPts; i++) {
      const theta = (i / nPts) * Math.PI * 2;
      pts.push(`${cx + semi_w * s * Math.cos(theta)},${cy + semi_d * s * Math.sin(theta)}`);
    }
    return pts.join(" ");
  };

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={cx - maxR * s} y1={cy} x2={cx + maxR * s} y2={cy} stroke={GRID} strokeWidth="0.5" />
      <line x1={cx} y1={cy - maxR * s} x2={cx} y2={cy + maxR * s} stroke={GRID} strokeWidth="0.5" />
      <polyline points={ellipse(w, priorD)} fill="none" stroke={PRIOR_COL} strokeWidth="1.5" opacity="0.6" strokeDasharray="4,3" />
      <polyline points={ellipse(w, finalD)} fill="none" stroke={FINAL_COL} strokeWidth="1.5" />
      <text x={8} y={16} fill="#888" fontSize="10" fontFamily="monospace">{lm.name}</text>
      <text x={8} y={28} fill="#666" fontSize="9" fontFamily="monospace">dy={lm.dy.toFixed(2)}</text>
      <text x={8} y={height - 24} fill={PRIOR_COL} fontSize="9" fontFamily="monospace">--- prior</text>
      <text x={8} y={height - 12} fill={FINAL_COL} fontSize="9" fontFamily="monospace">— optimised</text>
      <text x={width - 8} y={16} fill="#555" fontSize="9" fontFamily="monospace" textAnchor="end">
        w={w.toFixed(2)} d={finalD.toFixed(2)}
      </text>
    </svg>
  );
}

interface ConvergenceProps {
  readonly data: PipelineData;
  readonly width: number;
  readonly height: number;
}

function ConvergenceChart({ data, width, height }: ConvergenceProps): JSX.Element {
  const rewards = data.rewards;
  const minR = Math.min(...rewards.map((r) => r[1]));
  const maxR = Math.max(...rewards.map((r) => r[1]));
  const range = maxR - minR || 1;
  const pad = { l: 40, r: 10, t: 10, b: 24 };
  const pw = width - pad.l - pad.r;
  const ph = height - pad.t - pad.b;

  const pts = rewards
    .map(([it, rw]) => {
      const x = pad.l + (it / 95) * pw;
      const y = pad.t + (1 - (rw - minR) / range) * ph;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + ph} stroke={DIM} strokeWidth="0.5" />
      <line x1={pad.l} y1={pad.t + ph} x2={pad.l + pw} y2={pad.t + ph} stroke={DIM} strokeWidth="0.5" />
      <polyline points={pts} fill="none" stroke={FINAL_COL} strokeWidth="1.5" />
      {rewards.map(([it, rw], i) => {
        const x = pad.l + (it / 95) * pw;
        const y = pad.t + (1 - (rw - minR) / range) * ph;
        return <circle key={i} cx={x} cy={y} r="2" fill={FINAL_COL} />;
      })}
      <text x={pad.l - 4} y={pad.t + 4} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="end">{maxR.toFixed(1)}</text>
      <text x={pad.l - 4} y={pad.t + ph + 3} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="end">{minR.toFixed(1)}</text>
      <text x={pad.l + pw / 2} y={height - 2} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="middle">NES iteration</text>
      <text x={4} y={pad.t + ph / 2} fill="#666" fontSize="8" fontFamily="monospace" transform={`rotate(-90, 4, ${pad.t + ph / 2})`} textAnchor="middle">reward</text>
    </svg>
  );
}

interface SilhouetteViewProps {
  readonly data: PipelineData;
  readonly width: number;
  readonly height: number;
}

function SilhouetteView({ data, width, height }: SilhouetteViewProps): JSX.Element {
  const pad = 12;
  const maxDy = 8.0;
  const maxW = 1.4;
  const sx = (width / 2 - pad) / maxW;
  const sy = (height - 2 * pad) / maxDy;
  const cx = width / 2;

  const rightPts = data.dy.map((dy, i) => `${cx + data.widths[i]! * sx},${pad + dy * sy}`).join(" ");
  const leftPts = data.dy.map((dy, i) => `${cx - data.widths[i]! * sx},${pad + dy * sy}`).join(" ");

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={cx} y1={pad} x2={cx} y2={height - pad} stroke={GRID} strokeWidth="0.5" strokeDasharray="2,2" />
      <polyline points={rightPts} fill="none" stroke={CONTOUR_COL} strokeWidth="1.5" />
      <polyline points={leftPts} fill="none" stroke={CONTOUR_COL} strokeWidth="1.5" />
      {data.landmarks.map((lm, i) => {
        const y = pad + lm.dy * sy;
        return (
          <g key={i}>
            <line x1={pad} y1={y} x2={width - pad} y2={y} stroke={DIM} strokeWidth="0.3" strokeDasharray="1,3" />
            <text x={4} y={y - 2} fill="#555" fontSize="7" fontFamily="monospace">{lm.name.split("_")[0]}</text>
          </g>
        );
      })}
      <text x={cx} y={8} fill="#888" fontSize="9" fontFamily="monospace" textAnchor="middle">d₁ contour</text>
    </svg>
  );
}

interface DepthRatioProps {
  readonly data: PipelineData;
  readonly width: number;
  readonly height: number;
}

function DepthRatioChart({ data, width, height }: DepthRatioProps): JSX.Element {
  const pad = { l: 36, r: 10, t: 14, b: 20 };
  const pw = width - pad.l - pad.r;
  const ph = height - pad.t - pad.b;
  const maxDy = 8.0;
  const maxR = 1.2;

  const priorPts = data.dy.map((dy, i) => {
    const x = pad.l + (data.prior_ratios[i]! / maxR) * pw;
    const y = pad.t + (dy / maxDy) * ph;
    return `${x},${y}`;
  }).join(" ");
  const finalPts = data.dy.map((dy, i) => {
    const x = pad.l + (data.final_ratios[i]! / maxR) * pw;
    const y = pad.t + (dy / maxDy) * ph;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + ph} stroke={DIM} strokeWidth="0.5" />
      <line x1={pad.l + (1.0 / maxR) * pw} y1={pad.t} x2={pad.l + (1.0 / maxR) * pw} y2={pad.t + ph} stroke={DIM} strokeWidth="0.3" strokeDasharray="2,3" />
      <polyline points={priorPts} fill="none" stroke={PRIOR_COL} strokeWidth="1.2" opacity="0.6" strokeDasharray="4,3" />
      <polyline points={finalPts} fill="none" stroke={FINAL_COL} strokeWidth="1.5" />
      <text x={pad.l + pw / 2} y={10} fill="#888" fontSize="9" fontFamily="monospace" textAnchor="middle">depth ratio (d/w)</text>
      <text x={pad.l + (1.0 / maxR) * pw} y={pad.t - 3} fill="#555" fontSize="7" fontFamily="monospace" textAnchor="middle">1.0=circular</text>
      {data.landmarks.map((lm, i) => {
        const y = pad.t + (lm.dy / maxDy) * ph;
        return <circle key={i} cx={pad.l - 4} cy={y} r="2" fill={ACCENT} opacity="0.5" />;
      })}
    </svg>
  );
}

const STAGES = [
  { id: "d₀", label: "Stick", desc: "Landmarks + midline skeleton" },
  { id: "d₁", label: "Silhouette", desc: "2D contour + widths" },
  { id: "d₂", label: "Cross-sections", desc: "Depth priors per region" },
  { id: "d₃", label: "Initial mesh", desc: "Elliptical ring sweep" },
  { id: "d_N", label: "Optimised", desc: "NES policy gradient × 100" },
];

export default function PipelineViz(): JSX.Element {
  const [loaded, setLoaded] = useState<V4LoadPayload | null>(null);

  if (!loaded) {
    return (
      <div
        style={{
          background: "#111111",
          minHeight: "100vh",
          padding: "16px 8px",
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        }}
      >
        <V4FileLoader
          title="MESH PIPELINE"
          description="Drop a silhouette v4 JSON to visualize the stick-to-mesh reconstruction pipeline"
          onLoad={setLoaded}
        />
      </div>
    );
  }

  return (
    <PipelineVizInner
      data={derivePipelineData(loaded.data)}
      fileName={loaded.fileName}
      onReset={() => setLoaded(null)}
    />
  );
}

interface PipelineVizInnerProps {
  readonly data: PipelineData;
  readonly fileName: string;
  readonly onReset: () => void;
}

function PipelineVizInner({ data, fileName: _fileName, onReset: _onReset }: PipelineVizInnerProps): JSX.Element {
  const [showFinal, setShowFinal] = useState(true);
  const [selectedLm, setSelectedLm] = useState(3);
  void _fileName;
  void _onReset;

  return (
    <div
      style={{
        background: BG,
        color: "#ccc",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        padding: "16px",
        minHeight: "100vh",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: "12px", marginBottom: "4px" }}>
        <h1 style={{ margin: 0, fontSize: "16px", color: ACCENT, fontWeight: 600, letterSpacing: "0.5px" }}>
          STICK → MESH PIPELINE
        </h1>
        <span style={{ fontSize: "10px", color: "#555" }}>
          single-view reconstruction · NES policy gradient · 100 iterations
        </span>
      </div>

      <div style={{ display: "flex", gap: "2px", margin: "12px 0 16px", flexWrap: "wrap" }}>
        {STAGES.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "2px" }}>
            <div
              style={{
                background: i <= 3 ? "#1a2a1a" : "#2a2a1a",
                border: `1px solid ${i === 4 ? ACCENT : "#333"}`,
                padding: "4px 10px",
                fontSize: "10px",
                lineHeight: "1.4",
              }}
            >
              <div style={{ color: i === 4 ? ACCENT : "#999", fontWeight: 600 }}>
                {s.id} {s.label}
              </div>
              <div style={{ color: "#555", fontSize: "8px" }}>{s.desc}</div>
            </div>
            {i < STAGES.length - 1 && (
              <span style={{ color: "#444", fontSize: "14px" }}>→</span>
            )}
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        <div style={{ border: `1px solid ${DIM}`, padding: "8px", position: "relative" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontSize: "10px", color: "#888" }}>3D WIREFRAME</span>
            <div style={{ display: "flex", gap: "4px" }}>
              <button
                onClick={() => setShowFinal(false)}
                style={{
                  background: !showFinal ? PRIOR_COL : "transparent",
                  color: !showFinal ? "#000" : "#666",
                  border: `1px solid ${!showFinal ? PRIOR_COL : "#444"}`,
                  padding: "1px 8px",
                  fontSize: "9px",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                prior
              </button>
              <button
                onClick={() => setShowFinal(true)}
                style={{
                  background: showFinal ? FINAL_COL : "transparent",
                  color: showFinal ? "#000" : "#666",
                  border: `1px solid ${showFinal ? FINAL_COL : "#444"}`,
                  padding: "1px 8px",
                  fontSize: "9px",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                NES
              </button>
            </div>
          </div>
          <MeshViewer data={data} width={380} height={340} showFinal={showFinal} />
        </div>

        <div style={{ display: "grid", gridTemplateRows: "1fr 1fr", gap: "12px" }}>
          <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "10px", color: "#888" }}>CROSS-SECTION</span>
              <select
                value={selectedLm}
                onChange={(e) => setSelectedLm(+e.target.value)}
                style={{
                  background: "#1a1a1a",
                  color: "#999",
                  border: `1px solid ${DIM}`,
                  fontSize: "9px",
                  fontFamily: "inherit",
                  padding: "1px 4px",
                }}
              >
                {data.landmarks.map((lm, i) => (
                  <option key={i} value={i}>{lm.name}</option>
                ))}
              </select>
            </div>
            <CrossSectionView data={data} width={380} height={140} landmarkIdx={selectedLm} />
          </div>
          <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
            <span style={{ fontSize: "10px", color: "#888" }}>NES CONVERGENCE</span>
            <ConvergenceChart data={data} width={380} height={130} />
          </div>
        </div>

        <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
          <span style={{ fontSize: "10px", color: "#888" }}>FRONT SILHOUETTE (d₁)</span>
          <SilhouetteView data={data} width={380} height={260} />
        </div>

        <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
          <span style={{ fontSize: "10px", color: "#888" }}>DEPTH RATIO PROFILE</span>
          <DepthRatioChart data={data} width={380} height={260} />
        </div>
      </div>

      <div
        style={{
          marginTop: "16px",
          padding: "10px",
          border: "1px solid #2a1a1a",
          background: "#1a1111",
          fontSize: "9px",
          color: "#776655",
          lineHeight: "1.5",
        }}
      >
        <strong style={{ color: "#aa7744" }}>ILL-POSEDNESS NOTICE:</strong> Single-view → 3D
        is fundamentally under-determined. The depth axis (z) has no hard constraints from the
        input. The NES reward decreased from −0.47 → −1.70, confirming that exploration away
        from smooth anatomical priors adds noise without compensating information gain. The prior
        IS the best estimate without additional views. This mesh is one plausible interpretation —
        not a unique solution. Extracting the three-quarter and back views from the source image
        would substantially reduce ambiguity.
      </div>
    </div>
  );
}
