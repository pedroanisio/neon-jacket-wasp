import type { ComponentType, JSX } from "react";
import { useState, lazy, Suspense } from "react";

interface TabDef {
  readonly id: string;
  readonly label: string;
  readonly component: React.LazyExoticComponent<ComponentType>;
}

const TABS: ReadonlyArray<TabDef> = [
  { id: "loader", label: "V4 Loader", component: lazy(() => import("@frontend/silhouette_loader.tsx")) },
  { id: "analysis", label: "V4 Analysis", component: lazy(() => import("@frontend/v4_silhouette_analysis.tsx")) },
  { id: "render", label: "V2 Render", component: lazy(() => import("@frontend/silhouette_render.tsx")) },
  { id: "pipeline", label: "Mesh Pipeline", component: lazy(() => import("@frontend/stick_to_mesh_pipeline.tsx")) },
];

const ACCENT = "#e8c547";

export default function Shell(): JSX.Element {
  const [active, setActive] = useState(TABS[0]!.id);
  const tab = TABS.find((t) => t.id === active)!;
  const Component = tab.component;

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {/* Tab bar */}
      <nav
        style={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          padding: "8px 12px",
          background: "#0d0e14",
          borderBottom: "1px solid #1a1c28",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 11,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: "rgba(100,140,255,0.5)",
            fontWeight: 400,
            marginRight: 16,
          }}
        >
          NJW
        </span>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            style={{
              padding: "5px 14px",
              fontSize: 10,
              fontFamily: "inherit",
              background:
                active === t.id ? "rgba(70,110,220,0.2)" : "transparent",
              border: `1px solid ${active === t.id ? "rgba(100,140,255,0.4)" : "#1a1c28"}`,
              borderRadius: 3,
              cursor: "pointer",
              transition: "all .15s",
              color: active === t.id ? ACCENT : "#5868a8",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <Suspense
          fallback={
            <div
              style={{
                padding: 40,
                textAlign: "center",
                color: "#3b5068",
                fontSize: 12,
              }}
            >
              Loading...
            </div>
          }
        >
          <Component />
        </Suspense>
      </div>
    </div>
  );
}
