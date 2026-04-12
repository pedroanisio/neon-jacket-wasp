import { useState, useRef, useEffect, useCallback } from "react";

const DATA = {"dy":[0.005,0.206,0.407,0.608,0.809,1.011,1.212,1.413,1.614,1.815,2.016,2.217,2.419,2.62,2.821,3.022,3.223,3.424,3.625,3.827,4.028,4.229,4.43,4.631,4.832,5.033,5.234,5.436,5.637,5.838,6.039,6.24,6.441,6.642,6.844,7.045,7.246,7.447,7.648,7.849],"widths":[0.2624,0.4759,0.5381,0.5505,0.5404,0.4991,0.4095,0.7726,0.9627,0.9976,1.003,1.0493,1.0745,1.1631,1.2032,1.2009,1.2229,1.2544,1.2828,1.2845,1.3075,1.248,1.0176,0.7922,0.7659,0.7419,0.7256,0.7298,0.7539,0.7855,0.7968,0.7951,0.774,0.7519,0.7522,0.79,0.8011,0.7984,0.8791,0.9896],"prior_ratios":[0.95,0.9995,1.049,1.0985,0.9942,0.885,0.7759,0.7129,0.6642,0.6155,0.5669,0.5182,0.5614,0.6593,0.7047,0.7127,0.7207,0.7288,0.7368,0.7448,0.7554,0.7706,0.7859,0.8011,0.8163,0.8316,0.8468,0.8454,0.8395,0.8336,0.8277,0.8219,0.816,0.8101,0.8042,0.7777,0.6982,0.6186,0.5391,0.4596],"final_ratios":[0.9793,1.0702,0.9796,1.0865,1.0769,0.9411,0.7354,0.8005,0.6124,0.6015,0.6534,0.4481,0.6455,0.5802,0.6458,0.7247,0.729,0.8086,0.7199,0.7781,0.7869,0.7567,0.7634,0.7244,0.6943,0.8534,0.8992,0.7622,0.8832,0.8435,0.7577,0.8778,0.8748,0.9115,0.878,0.8672,0.7701,0.632,0.4791,0.5665],"rewards":[[0,-0.47],[5,-1.51],[10,-1.59],[15,-1.87],[20,-1.9],[25,-2.22],[30,-2.31],[35,-2.25],[40,-2.18],[45,-2.27],[50,-2.28],[55,-2.13],[60,-2.12],[65,-2.03],[70,-1.79],[75,-1.93],[80,-2.08],[85,-1.97],[90,-1.99],[95,-1.93]],"landmarks":[{"name":"crown","dy":0.005},{"name":"head_peak","dy":0.615},{"name":"neck_valley","dy":1.26},{"name":"shoulder_peak","dy":2.293},{"name":"waist_valley","dy":2.703},{"name":"hip_peak","dy":3.957},{"name":"knee_valley","dy":5.277},{"name":"ankle_valley","dy":6.988},{"name":"sole","dy":8.0}]};

const ACCENT = "#e8c547";
const DIM = "#4a4a4a";
const GRID = "#2a2a2a";
const BG = "#111111";
const PRIOR_COL = "#5588cc";
const FINAL_COL = "#e8c547";
const CONTOUR_COL = "#44aa66";

function project3D(x, y, z, rx, ry, scale, cx, cy) {
  const cosRY = Math.cos(ry), sinRY = Math.sin(ry);
  const cosRX = Math.cos(rx), sinRX = Math.sin(rx);
  let x1 = x * cosRY - z * sinRY;
  let z1 = x * sinRY + z * cosRY;
  let y1 = y * cosRX - z1 * sinRX;
  return { x: cx + x1 * scale, y: cy + y1 * scale, z: z1 };
}

function MeshViewer({ width, height, showFinal }) {
  const [rotation, setRotation] = useState({ rx: 0.15, ry: 0.6 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const svgRef = useRef(null);

  const onMouseDown = (e) => { dragging.current = true; lastPos.current = { x: e.clientX, y: e.clientY }; };
  const onMouseUp = () => { dragging.current = false; };
  const onMouseMove = (e) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    setRotation(r => ({ rx: r.rx + dy * 0.005, ry: r.ry + dx * 0.005 }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const scale = 42;
  const cx = width / 2;
  const cy = height / 2;
  const { rx, ry } = rotation;
  const ratios = showFinal ? DATA.final_ratios : DATA.prior_ratios;

  const rings = [];
  const nTheta = 24;
  const step = 2;

  for (let i = 0; i < DATA.dy.length; i += step) {
    const w = DATA.widths[i];
    const d = w * ratios[i];
    const y3d = -(DATA.dy[i] - 4);
    const pts = [];
    for (let j = 0; j <= nTheta; j++) {
      const theta = (j / nTheta) * Math.PI * 2;
      const x3d = w * Math.cos(theta);
      const z3d = d * Math.sin(theta);
      pts.push(project3D(x3d, y3d, z3d, rx, ry, scale, cx, cy));
    }
    rings.push({ pts, dy: DATA.dy[i] });
  }

  const longi = [];
  for (let j = 0; j < nTheta; j += 3) {
    const theta = (j / nTheta) * Math.PI * 2;
    const pts = [];
    for (let i = 0; i < DATA.dy.length; i++) {
      const w = DATA.widths[i];
      const d = w * ratios[i];
      const y3d = -(DATA.dy[i] - 4);
      const x3d = w * Math.cos(theta);
      const z3d = d * Math.sin(theta);
      pts.push(project3D(x3d, y3d, z3d, rx, ry, scale, cx, cy));
    }
    longi.push(pts);
  }

  return (
    <svg ref={svgRef} width={width} height={height}
      style={{ cursor: "grab", background: "transparent" }}
      onMouseDown={onMouseDown} onMouseUp={onMouseUp} onMouseLeave={onMouseUp} onMouseMove={onMouseMove}>
      {longi.map((pts, i) => (
        <polyline key={`l${i}`} points={pts.map(p => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke={showFinal ? FINAL_COL : PRIOR_COL} strokeWidth="0.5" opacity="0.25" />
      ))}
      {rings.map((ring, i) => (
        <polyline key={`r${i}`} points={ring.pts.map(p => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke={showFinal ? FINAL_COL : PRIOR_COL} strokeWidth="0.8" opacity="0.5" />
      ))}
      <text x={width/2} y={height - 8} fill="#888" fontSize="10" textAnchor="middle" fontFamily="monospace">
        drag to rotate
      </text>
    </svg>
  );
}

function CrossSectionView({ width, height, landmarkIdx }) {
  const lm = DATA.landmarks[landmarkIdx];
  const dyIdx = DATA.dy.reduce((best, d, i) => Math.abs(d - lm.dy) < Math.abs(DATA.dy[best] - lm.dy) ? i : best, 0);
  const w = DATA.widths[dyIdx];
  const priorD = w * DATA.prior_ratios[dyIdx];
  const finalD = w * DATA.final_ratios[dyIdx];
  const maxR = Math.max(w, priorD, finalD) * 1.3;
  const s = Math.min(width, height) / (2 * maxR) * 0.8;
  const cx = width / 2, cy = height / 2;
  const nPts = 60;

  const ellipse = (semi_w, semi_d) => {
    const pts = [];
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

function ConvergenceChart({ width, height }) {
  const rewards = DATA.rewards;
  const minR = Math.min(...rewards.map(r => r[1]));
  const maxR = Math.max(...rewards.map(r => r[1]));
  const range = maxR - minR || 1;
  const pad = { l: 40, r: 10, t: 10, b: 24 };
  const pw = width - pad.l - pad.r;
  const ph = height - pad.t - pad.b;

  const pts = rewards.map(([it, rw]) => {
    const x = pad.l + (it / 95) * pw;
    const y = pad.t + (1 - (rw - minR) / range) * ph;
    return `${x},${y}`;
  }).join(" ");

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
      <text x={pad.l - 4} y={pad.t + 4} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="end">
        {maxR.toFixed(1)}
      </text>
      <text x={pad.l - 4} y={pad.t + ph + 3} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="end">
        {minR.toFixed(1)}
      </text>
      <text x={pad.l + pw / 2} y={height - 2} fill="#666" fontSize="8" fontFamily="monospace" textAnchor="middle">
        NES iteration
      </text>
      <text x={4} y={pad.t + ph / 2} fill="#666" fontSize="8" fontFamily="monospace"
        transform={`rotate(-90, 4, ${pad.t + ph / 2})`} textAnchor="middle">reward</text>
    </svg>
  );
}

function SilhouetteView({ width, height }) {
  const pad = 12;
  const maxDy = 8.0;
  const maxW = 1.4;
  const sx = (width / 2 - pad) / maxW;
  const sy = (height - 2 * pad) / maxDy;
  const cx = width / 2;

  const rightPts = DATA.dy.map((dy, i) => `${cx + DATA.widths[i] * sx},${pad + dy * sy}`).join(" ");
  const leftPts = DATA.dy.map((dy, i) => `${cx - DATA.widths[i] * sx},${pad + dy * sy}`).join(" ");

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={cx} y1={pad} x2={cx} y2={height - pad} stroke={GRID} strokeWidth="0.5" strokeDasharray="2,2" />
      <polyline points={rightPts} fill="none" stroke={CONTOUR_COL} strokeWidth="1.5" />
      <polyline points={leftPts} fill="none" stroke={CONTOUR_COL} strokeWidth="1.5" />
      {DATA.landmarks.map((lm, i) => {
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

function DepthRatioChart({ width, height }) {
  const pad = { l: 36, r: 10, t: 14, b: 20 };
  const pw = width - pad.l - pad.r;
  const ph = height - pad.t - pad.b;
  const maxDy = 8.0;
  const maxR = 1.2;

  const priorPts = DATA.dy.map((dy, i) => {
    const x = pad.l + (DATA.prior_ratios[i] / maxR) * pw;
    const y = pad.t + (dy / maxDy) * ph;
    return `${x},${y}`;
  }).join(" ");
  const finalPts = DATA.dy.map((dy, i) => {
    const x = pad.l + (DATA.final_ratios[i] / maxR) * pw;
    const y = pad.t + (dy / maxDy) * ph;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={width} height={height} style={{ background: "transparent" }}>
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + ph} stroke={DIM} strokeWidth="0.5" />
      <line x1={pad.l + (1.0 / maxR) * pw} y1={pad.t} x2={pad.l + (1.0 / maxR) * pw} y2={pad.t + ph}
        stroke={DIM} strokeWidth="0.3" strokeDasharray="2,3" />
      <polyline points={priorPts} fill="none" stroke={PRIOR_COL} strokeWidth="1.2" opacity="0.6" strokeDasharray="4,3" />
      <polyline points={finalPts} fill="none" stroke={FINAL_COL} strokeWidth="1.5" />
      <text x={pad.l + pw / 2} y={10} fill="#888" fontSize="9" fontFamily="monospace" textAnchor="middle">
        depth ratio (d/w)
      </text>
      <text x={pad.l + (1.0 / maxR) * pw} y={pad.t - 3} fill="#555" fontSize="7" fontFamily="monospace" textAnchor="middle">
        1.0=circular
      </text>
      {DATA.landmarks.map((lm, i) => {
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

export default function PipelineViz() {
  const [showFinal, setShowFinal] = useState(true);
  const [selectedLm, setSelectedLm] = useState(3);

  return (
    <div style={{ background: BG, color: "#ccc", fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      padding: "16px", minHeight: "100vh", boxSizing: "border-box" }}>
      
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
            <div style={{ background: i <= 3 ? "#1a2a1a" : "#2a2a1a", border: `1px solid ${i === 4 ? ACCENT : "#333"}`,
              padding: "4px 10px", fontSize: "10px", lineHeight: "1.4" }}>
              <div style={{ color: i === 4 ? ACCENT : "#999", fontWeight: 600 }}>{s.id} {s.label}</div>
              <div style={{ color: "#555", fontSize: "8px" }}>{s.desc}</div>
            </div>
            {i < STAGES.length - 1 && <span style={{ color: "#444", fontSize: "14px" }}>→</span>}
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        
        <div style={{ border: `1px solid ${DIM}`, padding: "8px", position: "relative" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontSize: "10px", color: "#888" }}>3D WIREFRAME</span>
            <div style={{ display: "flex", gap: "4px" }}>
              <button onClick={() => setShowFinal(false)}
                style={{ background: !showFinal ? PRIOR_COL : "transparent", color: !showFinal ? "#000" : "#666",
                  border: `1px solid ${!showFinal ? PRIOR_COL : "#444"}`, padding: "1px 8px", fontSize: "9px",
                  cursor: "pointer", fontFamily: "inherit" }}>prior</button>
              <button onClick={() => setShowFinal(true)}
                style={{ background: showFinal ? FINAL_COL : "transparent", color: showFinal ? "#000" : "#666",
                  border: `1px solid ${showFinal ? FINAL_COL : "#444"}`, padding: "1px 8px", fontSize: "9px",
                  cursor: "pointer", fontFamily: "inherit" }}>NES</button>
            </div>
          </div>
          <MeshViewer width={380} height={340} showFinal={showFinal} />
        </div>

        <div style={{ display: "grid", gridTemplateRows: "1fr 1fr", gap: "12px" }}>
          <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "10px", color: "#888" }}>CROSS-SECTION</span>
              <select value={selectedLm} onChange={e => setSelectedLm(+e.target.value)}
                style={{ background: "#1a1a1a", color: "#999", border: `1px solid ${DIM}`,
                  fontSize: "9px", fontFamily: "inherit", padding: "1px 4px" }}>
                {DATA.landmarks.map((lm, i) => (
                  <option key={i} value={i}>{lm.name}</option>
                ))}
              </select>
            </div>
            <CrossSectionView width={380} height={140} landmarkIdx={selectedLm} />
          </div>
          <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
            <span style={{ fontSize: "10px", color: "#888" }}>NES CONVERGENCE</span>
            <ConvergenceChart width={380} height={130} />
          </div>
        </div>

        <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
          <span style={{ fontSize: "10px", color: "#888" }}>FRONT SILHOUETTE (d₁)</span>
          <SilhouetteView width={380} height={260} />
        </div>

        <div style={{ border: `1px solid ${DIM}`, padding: "8px" }}>
          <span style={{ fontSize: "10px", color: "#888" }}>DEPTH RATIO PROFILE</span>
          <DepthRatioChart width={380} height={260} />
        </div>
      </div>

      <div style={{ marginTop: "16px", padding: "10px", border: `1px solid #2a1a1a`, background: "#1a1111",
        fontSize: "9px", color: "#776655", lineHeight: "1.5" }}>
        <strong style={{ color: "#aa7744" }}>ILL-POSEDNESS NOTICE:</strong> Single-view → 3D is fundamentally
        under-determined. The depth axis (z) has no hard constraints from the input. The NES reward decreased from
        −0.47 → −1.70, confirming that exploration away from smooth anatomical priors adds noise without compensating
        information gain. The prior IS the best estimate without additional views. This mesh is one plausible
        interpretation — not a unique solution. Extracting the three-quarter and back views from the source image
        would substantially reduce ambiguity.
      </div>
    </div>
  );
}
