/** Shared presentational UI components for silhouette dashboards. */

import type { JSX, ReactNode } from "react";

interface BtnProps {
  readonly on: boolean;
  readonly onClick: () => void;
  readonly children: ReactNode;
}

export function Btn({ on, onClick, children }: BtnProps): JSX.Element {
  return (
    <button
      onClick={onClick}
      style={{
        background: on ? "#1a2332" : "transparent",
        border: `1px solid ${on ? "#2d3f54" : "#172030"}`,
        color: on ? "#e0f2fe" : "#3b5068",
        padding: "3px 8px",
        borderRadius: 3,
        fontSize: 10,
        cursor: "pointer",
        fontFamily: "inherit",
        transition: "all .12s",
      }}
    >
      {children}
    </button>
  );
}

interface StatProps {
  readonly label: string;
  readonly value: string | number;
  readonly unit?: string;
  readonly accent?: string;
}

export function Stat({ label, value, unit, accent }: StatProps): JSX.Element {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "3px 0",
        borderBottom: "1px solid #0d1520",
      }}
    >
      <span style={{ fontSize: 9, color: "#3b5068" }}>{label}</span>
      <span style={{ fontSize: 9, color: accent ?? "#7dd3fc", fontWeight: 600 }}>
        {value}
        {unit && (
          <span style={{ color: "#3b5068", fontWeight: 400 }}> {unit}</span>
        )}
      </span>
    </div>
  );
}

interface BarProps {
  readonly label: string;
  readonly value: number;
  readonly max: number;
  readonly color?: string;
}

export function Bar({ label, value, max, color }: BarProps): JSX.Element {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
      <span
        style={{ fontSize: 8, color: "#3b5068", width: 70, flexShrink: 0, textAlign: "right" }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: 5,
          background: "#0a1018",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(100, (value / max) * 100)}%`,
            height: "100%",
            background: color ?? "#0ea5e9",
            borderRadius: 2,
          }}
        />
      </div>
      <span style={{ fontSize: 8, color: "#475569", width: 32, textAlign: "right" }}>
        {(value * 100).toFixed(1)}%
      </span>
    </div>
  );
}
