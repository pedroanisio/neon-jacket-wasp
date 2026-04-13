import type { JSX } from "react";
import { useState, useMemo, useCallback } from "react";
import V4FileLoader from "./V4FileLoader.tsx";
import type { NormalizedData, V4LoadPayload } from "./shared/types.ts";
import { REGION_COLORS, BODY_REGION_COLORS } from "./shared/colors.ts";
import { SCALE, CENTER_X, PAD_TOP, huToSvg, buildContourPath } from "./shared/coord.ts";
import { Btn, Stat, Bar } from "./shared/ui.tsx";

const S = SCALE;
const CX = CENTER_X;
const PT = PAD_TOP;

interface LayerState {
  contour: boolean;
  strokes: boolean;
  landmarks: boolean;
  regions: boolean;
  medial: boolean;
  widthViz: boolean;
}

type TabId = "proportions" | "area" | "style" | "shape" | "bio" | "hull";

function Renderer({ data: D }: { readonly data: NormalizedData }): JSX.Element {
  const [layers, setLayers] = useState<LayerState>({
    contour: true,
    strokes: true,
    landmarks: true,
    regions: false,
    medial: false,
    widthViz: false,
  });
  const [tab, setTab] = useState<TabId>("proportions");
  const [hovLm, setHovLm] = useState<string | null>(null);
  const toggle = useCallback(
    (k: keyof LayerState) => setLayers((p) => ({ ...p, [k]: !p[k] })),
    [],
  );

  const contourPath = useMemo(
    () => buildContourPath(D.contour, D.mirrored, D.holes),
    [D.contour, D.mirrored, D.holes],
  );

  const lmData = useMemo(
    () =>
      D.landmarks.map((lm) => {
        const [xR, y] = huToSvg(lm.dx, lm.dy);
        return { ...lm, xR, y };
      }),
    [D.landmarks],
  );

  const neckLm = D.landmarks.find((l) => l.n === "neck_valley");
  const neckDy = neckLm ? neckLm.dy : 1.26;

  const comDy = D.bio?.com_dy;
  const availLayers: [keyof LayerState, string][] = [
    ["contour", "Contour"],
    ["strokes", "Strokes"],
    ["landmarks", "Landmarks"],
  ];
  if (D.br.length) availLayers.push(["regions", "Regions"]);
  if (D.med.length) availLayers.push(["medial", "Medial"]);
  if (D.wp.length) availLayers.push(["widthViz", "Width"]);

  const tabs: [TabId, string][] = [["proportions", "Proportions"]];
  if (D.ar.length) tabs.push(["area", "Area"]);
  if (D.sd) tabs.push(["style", "Style Dev"]);
  if (D.sc || D.gl) tabs.push(["shape", "Shape"]);
  if (D.bio) tabs.push(["bio", "Biomech"]);
  if (D.hull || D.vol) tabs.push(["hull", "Hull/Vol"]);

  return (
    <>
      {/* Header */}
      <div
        style={{
          width: "100%",
          maxWidth: 720,
          borderBottom: "1px solid #0f1d2d",
          paddingBottom: 8,
          marginBottom: 8,
        }}
      >
        <div
          style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}
        >
          <span
            style={{
              color: "#e0f2fe",
              fontSize: 14,
              fontWeight: 700,
              letterSpacing: 2,
            }}
          >
            SILHOUETTE ANALYSIS
          </span>
          <span style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 0.6 }}>
            {D.version} · {D.view.toUpperCase()} · {D.surface.toUpperCase()} ·{" "}
            {D.gender.toUpperCase()} · {D.pr.hc.toFixed(1)} HU
          </span>
        </div>
        <div style={{ fontSize: 9, color: "#172030", marginTop: 2 }}>
          {D.contour.length} contour pts · {D.strokes.length} strokes ·{" "}
          {D.landmarks.length} landmarks
          {D.br.length ? ` · ${D.br.length} regions` : ""}
          {D.hull ? ` · solidity ${D.hull.sol}` : ""}
        </div>
      </div>

      {/* Layers */}
      <div
        style={{
          display: "flex",
          gap: 4,
          flexWrap: "wrap",
          marginBottom: 8,
          maxWidth: 720,
          width: "100%",
        }}
      >
        {availLayers.map(([k, lb]) => (
          <Btn key={k} on={layers[k]} onClick={() => toggle(k)}>
            {lb}
          </Btn>
        ))}
      </div>

      {/* SVG */}
      <svg viewBox="0 0 270 560" style={{ width: "100%", maxWidth: 420, height: "auto" }}>
        <defs>
          <linearGradient id="cf" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5eead4" stopOpacity=".04" />
            <stop offset="50%" stopColor="#818cf8" stopOpacity=".03" />
            <stop offset="100%" stopColor="#f472b6" stopOpacity=".04" />
          </linearGradient>
          <filter id="gl">
            <feGaussianBlur stdDeviation="1.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {Array.from({ length: 9 }, (_, i) => {
          const y = PT + i * S;
          return (
            <g key={i}>
              <line
                x1={0} y1={y} x2={270} y2={y}
                stroke="#0d1520" strokeWidth={0.3} strokeDasharray="2,4"
              />
              <text x={2} y={y - 1} fill="#0d1520" fontSize={5} fontFamily="inherit">
                {i}.0
              </text>
            </g>
          );
        })}
        <line
          x1={CX} y1={0} x2={CX} y2={560}
          stroke="#172030" strokeWidth={0.3} strokeDasharray="1,3"
        />

        {layers.regions &&
          D.br.map((r, i) => (
            <rect
              key={i}
              x={CX - 1.4 * S} y={PT + r.s * S}
              width={2.8 * S} height={(r.e - r.s) * S}
              fill={BODY_REGION_COLORS[i % BODY_REGION_COLORS.length]}
              fillOpacity={0.06}
              stroke={BODY_REGION_COLORS[i % BODY_REGION_COLORS.length]}
              strokeWidth={0.3} strokeOpacity={0.2}
            />
          ))}
        {layers.regions &&
          D.br.map((r, i) => (
            <text
              key={`t${i}`}
              x={4} y={PT + ((r.s + r.e) / 2) * S + 2}
              fill={BODY_REGION_COLORS[i % BODY_REGION_COLORS.length]}
              fontSize={5} fontFamily="inherit" opacity={0.5}
            >
              {r.n}
            </text>
          ))}

        {layers.widthViz &&
          D.wp
            .filter((w) => w.w > 0 && w.w < 3)
            .map((w, i) => {
              const y = PT + w.dy * S;
              const hw = (w.w / 2) * S;
              return (
                <line
                  key={i}
                  x1={CX - hw} y1={y} x2={CX + hw} y2={y}
                  stroke="#0ea5e9" strokeWidth={0.4} opacity={0.25}
                />
              );
            })}

        {layers.medial &&
          D.med
            .filter((m) => m.r > 0)
            .map((m, i) => (
              <circle
                key={i}
                cx={CX} cy={PT + m.dy * S}
                r={Math.max(0.5, m.r * S * 0.08)}
                fill="#f59e0b" fillOpacity={0.3}
              />
            ))}

        {layers.contour && (
          <g>
            <path d={contourPath} fill="url(#cf)" fillRule="evenodd" />
            <path
              d={contourPath} fill="none" stroke="#334155"
              strokeWidth={0.7} strokeLinejoin="round"
            />
          </g>
        )}

        {layers.strokes &&
          D.strokes.map((sp, i) => {
            const d =
              "M " +
              sp.p
                .map(([dx, dy]) => {
                  const [x, y] = huToSvg(dx, dy);
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(" L ");
            return (
              <path
                key={i} d={d} fill="none"
                stroke={REGION_COLORS[sp.r] ?? "#64748b"}
                strokeWidth={0.5} opacity={0.55}
                strokeLinecap="round" strokeLinejoin="round"
              />
            );
          })}

        {layers.landmarks &&
          lmData.map((lm, i) => {
            const hov = hovLm === lm.n;
            return (
              <g
                key={i}
                onMouseEnter={() => setHovLm(lm.n)}
                onMouseLeave={() => setHovLm(null)}
                style={{ cursor: "pointer" }}
              >
                <line
                  x1={CX - 2} y1={lm.y} x2={CX + 2} y2={lm.y}
                  stroke={hov ? "#e0f2fe" : "#3b5068"}
                  strokeWidth={hov ? 1 : 0.5}
                />
                <circle
                  cx={lm.xR} cy={lm.y} r={hov ? 2 : 1.2}
                  fill={hov ? "#7dd3fc" : "#3b5068"}
                  filter={hov ? "url(#gl)" : undefined}
                />
                <text
                  x={260} y={lm.y + 2}
                  fill={hov ? "#bae6fd" : "#1e3a5f"}
                  fontSize={hov ? 6 : 5} fontFamily="inherit"
                  textAnchor="end" fontWeight={hov ? 700 : 400}
                >
                  {lm.n.replace(/_/g, " ").slice(0, 14)}
                </text>
                {hov && (
                  <g>
                    <rect
                      x={90} y={lm.y - 16} width={160} height={12}
                      rx={2} fill="#0f1d2d" stroke="#1e3a5f" strokeWidth={0.4}
                    />
                    <text
                      x={94} y={lm.y - 8}
                      fill="#7dd3fc" fontSize={4.5} fontFamily="inherit"
                    >
                      {lm.d.slice(0, 50)} — dy:{lm.dy.toFixed(3)} dx:
                      {lm.dx.toFixed(3)}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

        {comDy != null && (
          <g>
            <line
              x1={CX - 4} y1={PT + comDy * S} x2={CX + 4} y2={PT + comDy * S}
              stroke="#ef4444" strokeWidth={0.8} strokeDasharray="1,1"
            />
            <text
              x={CX + 6} y={PT + comDy * S + 2}
              fill="#ef4444" fontSize={4.5} fontFamily="inherit"
            >
              CoM
            </text>
          </g>
        )}

        {Array.from(
          { length: Math.min(8, Math.ceil(D.pr.hc)) },
          (_, i) => {
            const y1 = PT + 0.005 * S + i * neckDy * S;
            const y2 = y1 + neckDy * S;
            if (i >= Math.ceil(D.pr.hc)) return null;
            return (
              <g key={i}>
                <rect
                  x={4} y={y1} width={8} height={neckDy * S}
                  fill={
                    i % 2 === 0
                      ? "rgba(94,234,212,.06)"
                      : "rgba(129,140,248,.06)"
                  }
                  stroke="#172030" strokeWidth={0.2}
                />
                <text
                  x={8} y={(y1 + y2) / 2 + 2}
                  fill="#1e3a5f" fontSize={4.5} fontFamily="inherit" textAnchor="middle"
                >
                  {i + 1}
                </text>
              </g>
            );
          },
        )}
      </svg>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 2,
          marginTop: 12,
          maxWidth: 720,
          width: "100%",
          borderBottom: "1px solid #0f1d2d",
          flexWrap: "wrap",
        }}
      >
        {tabs.map(([k, lb]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            style={{
              background: tab === k ? "#0f1d2d" : "transparent",
              border: "none",
              borderBottom:
                tab === k ? "2px solid #0ea5e9" : "2px solid transparent",
              color: tab === k ? "#7dd3fc" : "#1e3a5f",
              padding: "5px 10px",
              fontSize: 10,
              cursor: "pointer",
              fontFamily: "inherit",
              fontWeight: tab === k ? 600 : 400,
            }}
          >
            {lb}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ maxWidth: 720, width: "100%", padding: "12px 0" }}>
        {tab === "proportions" && (
          <div>
            <div
              style={{
                fontSize: 10,
                color: "#3b5068",
                fontWeight: 600,
                marginBottom: 8,
                letterSpacing: 1,
              }}
            >
              SEGMENT RATIOS — {D.pr.hc.toFixed(1)} HEAD UNITS
            </div>
            {Object.entries(D.pr.sr).map(([k, v]) => (
              <Bar
                key={k}
                label={k
                  .split("\u2192")
                  .map((s) => s.slice(0, 4))
                  .join("\u2192")}
                value={v}
                max={0.3}
                color="#0ea5e9"
              />
            ))}
            {Object.keys(D.pr.comp).length > 0 && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  COMPOSITE RATIOS
                </div>
                {Object.entries(D.pr.comp).map(([k, v]) => (
                  <Stat
                    key={k}
                    label={k.replace(/_/g, " ")}
                    value={typeof v === "number" ? v.toFixed(3) : String(v)}
                  />
                ))}
              </>
            )}
            {D.pr.canons.length > 0 && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 6,
                    letterSpacing: 1,
                  }}
                >
                  CANONICAL SYSTEMS
                </div>
                {D.pr.canons.map((c, i) => (
                  <Stat
                    key={i}
                    label={c.sys}
                    value={`${c.heads} heads`}
                    accent="#f59e0b"
                  />
                ))}
              </>
            )}
          </div>
        )}

        {tab === "area" && (
          <div>
            <div
              style={{
                fontSize: 10,
                color: "#3b5068",
                fontWeight: 600,
                marginBottom: 8,
                letterSpacing: 1,
              }}
            >
              AREA PER BODY REGION (HU²)
            </div>
            {D.ar.map((r, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 3,
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 2,
                    background:
                      BODY_REGION_COLORS[i % BODY_REGION_COLORS.length],
                    opacity: 0.7,
                  }}
                />
                <span style={{ fontSize: 9, color: "#3b5068", width: 80 }}>
                  {r.n}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: 6,
                    background: "#0a1018",
                    borderRadius: 2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${r.f * 100 * 4.5}%`,
                      height: "100%",
                      background:
                        BODY_REGION_COLORS[i % BODY_REGION_COLORS.length],
                      opacity: 0.7,
                      borderRadius: 2,
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: 8,
                    color: "#64748b",
                    width: 55,
                    textAlign: "right",
                  }}
                >
                  {r.a.toFixed(2)} ({(r.f * 100).toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === "style" && D.sd && (
          <div>
            <div
              style={{
                fontSize: 10,
                color: "#3b5068",
                fontWeight: 600,
                marginBottom: 4,
                letterSpacing: 1,
              }}
            >
              STYLE DEVIATION vs {(D.sd.canon || "").replace(/_/g, " ").toUpperCase()}
            </div>
            <div style={{ fontSize: 8, color: "#1e3a5f", marginBottom: 10 }}>
              Figure: {D.sd.fh} heads · Canon: {D.sd.ch} heads · L²: {D.sd.l2}
            </div>
            <div
              style={{ fontSize: 9, color: "#3b5068", fontWeight: 600, marginBottom: 6 }}
            >
              POSITION DEVIATIONS
            </div>
            {D.sd.pos.map((p, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 3,
                }}
              >
                <span style={{ fontSize: 8, color: "#3b5068", width: 80 }}>
                  {p.n.replace(/_/g, " ")}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: 8,
                    background: "#0a1018",
                    borderRadius: 3,
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      top: 0,
                      bottom: 0,
                      width: 1,
                      background: "#1e3a5f",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      left: `${50 + p.d * 500}%`,
                      top: 1,
                      width: 6,
                      height: 6,
                      borderRadius: 3,
                      background: p.d > 0 ? "#f59e0b" : "#0ea5e9",
                      transform: "translateX(-3px)",
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: 8,
                    color: p.d > 0 ? "#f59e0b" : "#0ea5e9",
                    width: 40,
                    textAlign: "right",
                  }}
                >
                  {p.d > 0 ? "+" : ""}
                  {(p.d * 100).toFixed(1)}%
                </span>
              </div>
            ))}
            <div
              style={{
                fontSize: 9,
                color: "#3b5068",
                fontWeight: 600,
                marginTop: 12,
                marginBottom: 6,
              }}
            >
              WIDTH DEVIATIONS
            </div>
            {D.sd.wid.map((w, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 3,
                }}
              >
                <span style={{ fontSize: 8, color: "#3b5068", width: 80 }}>
                  {w.n.replace(/_/g, " ")}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: 8,
                    background: "#0a1018",
                    borderRadius: 3,
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      top: 0,
                      bottom: 0,
                      width: 1,
                      background: "#1e3a5f",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      left: `${50 + w.d * 300}%`,
                      top: 1,
                      width: 6,
                      height: 6,
                      borderRadius: 3,
                      background: w.d > 0 ? "#f59e0b" : "#0ea5e9",
                      transform: "translateX(-3px)",
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: 8,
                    color: w.d > 0 ? "#f59e0b" : "#0ea5e9",
                    width: 40,
                    textAlign: "right",
                  }}
                >
                  {w.d > 0 ? "+" : ""}
                  {(w.d * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === "shape" && (
          <div>
            {D.sc && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  SHAPE COMPLEXITY
                </div>
                {Object.entries(D.sc).map(([k, v]) => (
                  <Stat
                    key={k}
                    label={k.replace(/_/g, " ")}
                    value={
                      typeof v === "object" && v !== null
                        ? (v as { value: number }).value
                        : (v as number)
                    }
                    unit={
                      typeof v === "object" && v !== null
                        ? (v as { units?: string; method?: string }).units ??
                          (v as { method?: string }).method ??
                          ""
                        : ""
                    }
                  />
                ))}
              </>
            )}
            {D.gl && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  GESTURE LINE
                </div>
                <Stat
                  label="Lean Angle"
                  value={`${D.gl.lean}\u00B0`}
                  unit={(D.gl.li || "").replace(/_/g, " ")}
                />
                <Stat
                  label="Contrapposto"
                  value={D.gl.cp}
                  unit={D.gl.ci}
                  accent="#a78bfa"
                />
                <Stat label="Gesture Energy" value={D.gl.en} />
                <Stat
                  label="Centroid"
                  value={`(${D.gl.ctr_dx}, ${D.gl.ctr_dy})`}
                  unit="HU"
                />
              </>
            )}
          </div>
        )}

        {tab === "bio" && D.bio && (
          <div>
            <div
              style={{
                fontSize: 10,
                color: "#3b5068",
                fontWeight: 600,
                marginBottom: 8,
                letterSpacing: 1,
              }}
            >
              BIOMECHANICS
            </div>
            <Stat label="Canonical Height" value={D.bio.hcm} unit="cm" />
            <Stat label="Scale Factor" value={D.bio.sc} unit="cm/HU" />
            {D.bio.com_dy != null && (
              <Stat
                label="Center of Mass"
                value={D.bio.com_dy.toFixed(3)}
                unit="HU"
              />
            )}
            {D.bio.com_frac != null && (
              <Stat
                label="CoM Fraction"
                value={(D.bio.com_frac * 100).toFixed(1)}
                unit="% from crown"
              />
            )}
            {D.wp.length > 0 && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  WIDTH PROFILE
                </div>
                <svg
                  viewBox="0 0 300 100"
                  style={{
                    width: "100%",
                    height: 80,
                    background: "#0a1018",
                    borderRadius: 4,
                  }}
                >
                  {D.wp
                    .filter((w) => w.w > 0 && w.w < 3)
                    .map((w, i) => {
                      const x = (w.dy / 8) * 290 + 5;
                      const h = (w.w / 2.5) * 90;
                      return (
                        <rect
                          key={i}
                          x={x} y={95 - h} width={3} height={h}
                          fill="#0ea5e9" opacity={0.5} rx={1}
                        />
                      );
                    })}
                  <text
                    x={5} y={10}
                    fill="#1e3a5f" fontSize={6} fontFamily="inherit"
                  >
                    Full Width (HU)
                  </text>
                </svg>
              </>
            )}
            {D.med.length > 0 && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  MEDIAL AXIS INSCRIBED RADIUS
                </div>
                <svg
                  viewBox="0 0 300 60"
                  style={{
                    width: "100%",
                    height: 50,
                    background: "#0a1018",
                    borderRadius: 4,
                  }}
                >
                  <polyline
                    fill="none" stroke="#f59e0b" strokeWidth={1} opacity={0.6}
                    points={D.med
                      .filter((m) => m.r > 0)
                      .map(
                        (m) =>
                          `${(m.dy / 8) * 290 + 5},${55 - (m.r / 1.3) * 45}`,
                      )
                      .join(" ")}
                  />
                  <text
                    x={5} y={10}
                    fill="#1e3a5f" fontSize={6} fontFamily="inherit"
                  >
                    Inscribed Radius (HU)
                  </text>
                </svg>
              </>
            )}
          </div>
        )}

        {tab === "hull" && (
          <div>
            {D.hull && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  CONVEX HULL
                </div>
                <Stat label="Solidity" value={D.hull.sol} unit="A/A_hull" />
                <Stat label="Hull Area" value={D.hull.ha} unit="HU²" />
                <Stat label="Silhouette Area" value={D.hull.sa} unit="HU²" />
                <Stat
                  label="Negative Space"
                  value={D.hull.na}
                  unit="HU²"
                  accent="#ef4444"
                />
              </>
            )}
            {D.vol && (
              <>
                <div
                  style={{
                    fontSize: 10,
                    color: "#3b5068",
                    fontWeight: 600,
                    marginTop: 14,
                    marginBottom: 8,
                    letterSpacing: 1,
                  }}
                >
                  VOLUMETRIC ESTIMATES (HU³)
                </div>
                {D.vol.cyl != null && (
                  <Stat
                    label="Cylindrical (\u03C0\u222Bdx\u00B2dy)"
                    value={D.vol.cyl}
                    accent="#0ea5e9"
                  />
                )}
                {D.vol.ell != null && (
                  <Stat
                    label="Ellipsoidal (\u03C0/4\u222Bdx\u00B2dy)"
                    value={D.vol.ell}
                    accent="#818cf8"
                  />
                )}
                {D.vol.pap != null && (
                  <Stat
                    label="Pappus (2\u03C0\u222Bx\u00B7w\u00B7dy)"
                    value={D.vol.pap}
                    accent="#f59e0b"
                  />
                )}
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export default function App(): JSX.Element {
  const [data, setData] = useState<NormalizedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");

  const handleLoad = useCallback((payload: V4LoadPayload) => {
    setData(payload.data);
    setFileName(payload.fileName);
    setError(null);
  }, []);

  return (
    <div
      style={{
        background: "#060b12",
        minHeight: "100vh",
        fontFamily: "'IBM Plex Mono','Fira Code',monospace",
        color: "#64748b",
        padding: "12px 8px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&display=swap');`}</style>

      {!data ? (
        <V4FileLoader
          title="SILHOUETTE ANALYSIS"
          description="Drop a contour JSON (v2 or v4) here, or click to browse"
          onLoad={handleLoad}
        />
      ) : (
        <>
          <div
            style={{
              width: "100%",
              maxWidth: 720,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 4,
            }}
          >
            <span style={{ fontSize: 9, color: "#1e3a5f" }}>{fileName}</span>
            <button
              onClick={() => {
                setData(null);
                setFileName("");
                setError(null);
              }}
              style={{
                background: "transparent",
                border: "1px solid #172030",
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
          <Renderer data={data} />
          <div
            style={{
              fontSize: 7,
              color: "#0d1520",
              marginTop: 16,
              textAlign: "center",
            }}
          >
            schema {data.version} · {data.contour.length} pts ·{" "}
            {data.strokes.length} strokes · {data.landmarks.length} landmarks
          </div>
          {error && (
            <div style={{ color: "#ef4444", fontSize: 10, marginTop: 8 }}>
              {error}
            </div>
          )}
        </>
      )}
    </div>
  );
}
