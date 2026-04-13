import type { JSX } from "react";
import { useState, useMemo, useCallback } from "react";
import V4FileLoader from "./V4FileLoader.tsx";
import type { NormalizedData, V4LoadPayload } from "./shared/types.ts";
import { REGION_COLORS } from "./shared/colors.ts";

const LANDMARK_SHORT: Readonly<Record<string, string>> = {
  crown: "CRN",
  head_peak: "HP",
  neck_valley: "NV",
  shoulder_peak: "SP",
  waist_valley: "WV",
  hip_peak: "HiP",
  knee_valley: "KV",
  ankle_valley: "AV",
  sole: "SOL",
};

const S = 75;
const CX = 120;
const PAD_TOP = 8;
const VB_W = 320;
const VB_H = 640;

function huToSvg(dx: number, dy: number): [number, number] {
  return [CX + dx * S, PAD_TOP + dy * S];
}

interface LayerState {
  contour: boolean;
  strokes: boolean;
  landmarks: boolean;
  ruler: boolean;
  widths: boolean;
}

export default function SilhouetteRenderer(): JSX.Element {
  const [loaded, setLoaded] = useState<V4LoadPayload | null>(null);

  if (!loaded) {
    return (
      <div
        style={{
          background: "#0a0e17",
          minHeight: "100vh",
          padding: "16px 8px",
          fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
        }}
      >
        <V4FileLoader
          title="CONTOUR ANALYSIS"
          description="Drop a silhouette v4 JSON to render contour, strokes, landmarks, and proportions"
          onLoad={setLoaded}
        />
      </div>
    );
  }

  return (
    <SilhouetteRendererInner
      D={loaded.data}
      fileName={loaded.fileName}
      onReset={() => setLoaded(null)}
    />
  );
}

interface RendererInnerProps {
  readonly D: NormalizedData;
  readonly fileName: string;
  readonly onReset: () => void;
}

function SilhouetteRendererInner({ D, fileName, onReset }: RendererInnerProps): JSX.Element {
  const [layers, setLayers] = useState<LayerState>({
    contour: true,
    strokes: true,
    landmarks: true,
    ruler: true,
    widths: false,
  });
  const [hoveredLandmark, setHoveredLandmark] = useState<string | null>(null);
  const [mirrorStrokes, setMirrorStrokes] = useState(false);

  const toggle = useCallback((key: keyof LayerState) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const contourPath = useMemo(() => {
    const pts = D.contour;
    const right = pts.map(([dx, dy]) => huToSvg(dx, dy));
    const left = [...pts].reverse().map(([dx, dy]) => huToSvg(-dx, dy));
    const all = [...right, ...left];
    return (
      "M " + all.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ") + " Z"
    );
  }, [D.contour]);

  const strokePaths = useMemo(() => {
    return D.strokes.map((stroke) => {
      const d =
        "M " +
        stroke.p
          .map(([dx, dy]) => {
            const [x, y] = huToSvg(dx, dy);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(" L ");
      const dMirror =
        "M " +
        stroke.p
          .map(([dx, dy]) => {
            const [x, y] = huToSvg(-dx, dy);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(" L ");
      return { d, dMirror, region: stroke.r };
    });
  }, [D.strokes]);

  const landmarkData = useMemo(() => {
    return D.landmarks.map((lm) => {
      const [xR, y] = huToSvg(lm.dx, lm.dy);
      const [xL] = huToSvg(-lm.dx, lm.dy);
      return { ...lm, xR, xL, y };
    });
  }, [D.landmarks]);

  const headHU =
    (D.landmarks[1]?.dy ?? 0) -
    (D.landmarks[0]?.dy ?? 0) +
    ((D.landmarks[2]?.dy ?? 0) - (D.landmarks[1]?.dy ?? 0));
  void headHU; // used implicitly via neckDy
  const neckDy = D.landmarks[2]?.dy ?? 1.26;

  return (
    <div
      style={{
        background: "#0a0e17",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
        color: "#94a3b8",
        padding: "16px 8px",
      }}
    >
      {/* Header */}
      <div
        style={{
          width: "100%",
          maxWidth: 700,
          marginBottom: 12,
          borderBottom: "1px solid #1e293b",
          paddingBottom: 10,
        }}
      >
        <div
          style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}
        >
          <span
            style={{
              color: "#e2e8f0",
              fontSize: 15,
              fontWeight: 700,
              letterSpacing: 1.5,
            }}
          >
            CONTOUR ANALYSIS
          </span>
          <span style={{ fontSize: 10, color: "#475569", letterSpacing: 0.8 }}>
            {D.version} &middot; {D.view.toUpperCase()} &middot;{" "}
            {D.surface.toUpperCase()} &middot; {D.gender.toUpperCase()}
          </span>
        </div>
        <div style={{ fontSize: 10, color: "#334155", marginTop: 4 }}>
          {D.contour.length} contour pts &middot; {D.strokes.length} detail strokes
          &middot; {D.landmarks.length} landmarks &middot; {D.pr.hc.toFixed(1)}{" "}
          head-units tall
        </div>
      </div>

      {/* Controls */}
      <div
        style={{
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
          marginBottom: 12,
          maxWidth: 700,
          width: "100%",
        }}
      >
        {(
          [
            ["contour", "Contour"],
            ["strokes", "Strokes"],
            ["landmarks", "Landmarks"],
            ["ruler", "Ruler"],
            ["widths", "Widths"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            style={{
              background: layers[key] ? "#1e293b" : "transparent",
              border: `1px solid ${layers[key] ? "#334155" : "#1e293b"}`,
              color: layers[key] ? "#e2e8f0" : "#475569",
              padding: "4px 10px",
              borderRadius: 4,
              fontSize: 11,
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "all 0.15s",
            }}
          >
            {label}
          </button>
        ))}
        <button
          onClick={() => setMirrorStrokes((p) => !p)}
          style={{
            background: mirrorStrokes ? "#1e293b" : "transparent",
            border: `1px solid ${mirrorStrokes ? "#334155" : "#1e293b"}`,
            color: mirrorStrokes ? "#e2e8f0" : "#475569",
            padding: "4px 10px",
            borderRadius: 4,
            fontSize: 11,
            cursor: "pointer",
            fontFamily: "inherit",
            marginLeft: "auto",
          }}
        >
          Mirror Strokes
        </button>
      </div>

      {/* SVG Viewport */}
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        style={{ width: "100%", maxWidth: 500, height: "auto", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="contourFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.06" />
            <stop offset="50%" stopColor="#a78bfa" stopOpacity="0.04" />
            <stop offset="100%" stopColor="#f87171" stopOpacity="0.06" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Grid */}
        {Array.from({ length: 9 }, (_, i) => {
          const y = PAD_TOP + i * S;
          return (
            <g key={`grid-${i}`}>
              <line
                x1={0} y1={y} x2={VB_W} y2={y}
                stroke="#1e293b" strokeWidth={0.3} strokeDasharray="2,4"
              />
              <text x={2} y={y - 2} fill="#1e293b" fontSize={6} fontFamily="inherit">
                {i}.0
              </text>
            </g>
          );
        })}
        <line
          x1={CX} y1={0} x2={CX} y2={VB_H}
          stroke="#334155" strokeWidth={0.3} strokeDasharray="1,3"
        />

        {layers.contour && (
          <g>
            <path d={contourPath} fill="url(#contourFill)" />
            <path
              d={contourPath} fill="none" stroke="#475569"
              strokeWidth={0.8} strokeLinejoin="round"
            />
          </g>
        )}

        {layers.widths &&
          landmarkData.map((lm, i) => (
            <g key={`w-${i}`}>
              <line
                x1={lm.xL} y1={lm.y} x2={lm.xR} y2={lm.y}
                stroke="#334155" strokeWidth={0.5} strokeDasharray="2,2"
              />
              <text
                x={lm.xR + 4} y={lm.y + 2}
                fill="#475569" fontSize={5} fontFamily="inherit"
              >
                {(lm.dx * 2).toFixed(2)} HU
              </text>
            </g>
          ))}

        {layers.strokes &&
          strokePaths.map((sp, i) => (
            <g key={`s-${i}`}>
              <path
                d={sp.d} fill="none" stroke={REGION_COLORS[sp.region] ?? "#64748b"}
                strokeWidth={0.5} opacity={0.55}
                strokeLinecap="round" strokeLinejoin="round"
              />
              {mirrorStrokes && (
                <path
                  d={sp.dMirror} fill="none"
                  stroke={REGION_COLORS[sp.region] ?? "#64748b"}
                  strokeWidth={0.5} opacity={0.3}
                  strokeLinecap="round" strokeLinejoin="round"
                />
              )}
            </g>
          ))}

        {layers.landmarks &&
          landmarkData.map((lm, i) => {
            const isHovered = hoveredLandmark === lm.n;
            return (
              <g
                key={`lm-${i}`}
                onMouseEnter={() => setHoveredLandmark(lm.n)}
                onMouseLeave={() => setHoveredLandmark(null)}
                style={{ cursor: "pointer" }}
              >
                <line
                  x1={CX - 3} y1={lm.y} x2={CX + 3} y2={lm.y}
                  stroke={isHovered ? "#e2e8f0" : "#64748b"}
                  strokeWidth={isHovered ? 1.2 : 0.7}
                />
                <circle
                  cx={lm.xR} cy={lm.y} r={isHovered ? 2.5 : 1.5}
                  fill={isHovered ? "#e2e8f0" : "#64748b"}
                  filter={isHovered ? "url(#glow)" : undefined}
                />
                <text
                  x={VB_W - 8} y={lm.y + 2}
                  fill={isHovered ? "#e2e8f0" : "#475569"}
                  fontSize={isHovered ? 7 : 6} fontFamily="inherit"
                  textAnchor="end" fontWeight={isHovered ? 700 : 400}
                >
                  {LANDMARK_SHORT[lm.n]}
                </text>
                {isHovered && (
                  <g>
                    <rect
                      x={VB_W - 150} y={lm.y - 18} width={140} height={14}
                      rx={2} fill="#1e293b" stroke="#334155" strokeWidth={0.5}
                    />
                    <text
                      x={VB_W - 145} y={lm.y - 9}
                      fill="#cbd5e1" fontSize={5.5} fontFamily="inherit"
                    >
                      {lm.d} — dy:{lm.dy.toFixed(3)} dx:{lm.dx.toFixed(3)}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

        {layers.ruler && (
          <g>
            {Array.from({ length: Math.ceil(D.pr.hc) + 1 }, (_, i) => {
              const headH = neckDy;
              const yTop = PAD_TOP + (D.landmarks[0]?.dy ?? 0) * S;
              const y1 = yTop + i * headH * S;
              const y2 = yTop + (i + 1) * headH * S;
              if (i >= Math.ceil(D.pr.hc)) return null;
              const isPartial = i + 1 > D.pr.hc;
              return (
                <g key={`ru-${i}`}>
                  <rect
                    x={6} y={y1} width={10} height={y2 - y1}
                    fill={
                      i % 2 === 0
                        ? "rgba(96,165,250,0.08)"
                        : "rgba(167,139,250,0.08)"
                    }
                    stroke="#334155" strokeWidth={0.3}
                    opacity={isPartial ? 0.4 : 1}
                  />
                  <text
                    x={11} y={(y1 + y2) / 2 + 2}
                    fill="#475569" fontSize={5} fontFamily="inherit" textAnchor="middle"
                  >
                    {i + 1}
                  </text>
                </g>
              );
            })}
            <text
              x={11} y={PAD_TOP - 2}
              fill="#475569" fontSize={5} fontFamily="inherit" textAnchor="middle"
            >
              HU
            </text>
          </g>
        )}
      </svg>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginTop: 12,
          flexWrap: "wrap",
          justifyContent: "center",
        }}
      >
        {Object.entries(REGION_COLORS).map(([region, color]) => (
          <div key={region} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                background: color,
                opacity: 0.7,
              }}
            />
            <span style={{ fontSize: 10, color: "#64748b" }}>
              {region.replace("_", "/")}
            </span>
          </div>
        ))}
      </div>

      {/* Proportions panel */}
      <div
        style={{
          maxWidth: 500,
          width: "100%",
          marginTop: 16,
          borderTop: "1px solid #1e293b",
          paddingTop: 12,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            fontWeight: 700,
            marginBottom: 8,
            letterSpacing: 1,
          }}
        >
          SEGMENT RATIOS
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {Object.entries(D.pr.sr).map(([label, val]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{ fontSize: 9, color: "#475569", width: 170, flexShrink: 0 }}
              >
                {label}
              </span>
              <div
                style={{
                  flex: 1,
                  height: 6,
                  background: "#0f172a",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${val * 100 * 4}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #3b82f6, #8b5cf6)",
                    borderRadius: 3,
                  }}
                />
              </div>
              <span
                style={{ fontSize: 9, color: "#64748b", width: 40, textAlign: "right" }}
              >
                {(val * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>

        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            fontWeight: 700,
            marginTop: 14,
            marginBottom: 8,
            letterSpacing: 1,
          }}
        >
          WIDTH AT LANDMARKS (half-width / total height)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {Object.entries(D.pr.wr).map(([label, val]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{ fontSize: 9, color: "#475569", width: 100, flexShrink: 0 }}
              >
                {label}
              </span>
              <div
                style={{
                  flex: 1,
                  height: 6,
                  background: "#0f172a",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${val * 100 * 2.5}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #34d399, #60a5fa)",
                    borderRadius: 3,
                  }}
                />
              </div>
              <span
                style={{ fontSize: 9, color: "#64748b", width: 45, textAlign: "right" }}
              >
                {(val * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 12,
          marginTop: 20,
        }}
      >
        <div style={{ fontSize: 8, color: "#1e293b" }}>
          {fileName} &middot; schema {D.version} &middot; {D.contour.length} contour pts
          &middot; {D.strokes.length} strokes
        </div>
        <button
          onClick={onReset}
          style={{
            background: "transparent",
            border: "1px solid #1e293b",
            color: "#3b5068",
            padding: "2px 8px",
            borderRadius: 3,
            fontSize: 9,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Load Another
        </button>
      </div>
    </div>
  );
}
