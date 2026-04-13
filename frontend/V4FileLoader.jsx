/**
 * Shared v4 JSON file loader with drag-and-drop.
 *
 * Usage:
 *   <V4FileLoader title="MY VIZ" onLoad={setData} />
 *
 * Calls onLoad(normalizedData) when a valid v4 JSON is loaded.
 */

import { useState, useCallback, useRef } from "react";
import normalize from "./normalize_v4.js";

export default function V4FileLoader({ title, description, onLoad }) {
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);

  const loadFile = useCallback((file) => {
    setError(null);
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const raw = JSON.parse(e.target.result);
        if (!raw.contour || !Array.isArray(raw.contour)) {
          setError("Invalid JSON: missing 'contour' array. Needs a v4 silhouette document.");
          return;
        }
        onLoad({ data: normalize(raw), fileName: file.name, raw });
      } catch (err) {
        setError(`Parse error: ${err.message}`);
      }
    };
    reader.onerror = () => setError("Failed to read file.");
    reader.readAsText(file);
  }, [onLoad]);

  const onDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) loadFile(file);
  }, [loadFile]);

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onClick={() => fileRef.current?.click()}
      style={{
        width: "100%", maxWidth: 500, marginTop: "12vh",
        border: `2px dashed ${dragging ? "#0ea5e9" : "#1e3a5f"}`,
        borderRadius: 12, padding: "60px 30px", textAlign: "center",
        cursor: "pointer", transition: "all .2s",
        background: dragging ? "rgba(14,165,233,.04)" : "transparent",
        marginLeft: "auto", marginRight: "auto",
      }}
    >
      <input
        ref={fileRef} type="file" accept=".json"
        style={{ display: "none" }}
        onChange={(e) => loadFile(e.target.files?.[0])}
      />
      <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.3 }}>&#x2B06;</div>
      <div style={{ color: "#e0f2fe", fontSize: 14, fontWeight: 700, letterSpacing: 2, marginBottom: 8 }}>
        {title || "LOAD V4 JSON"}
      </div>
      <div style={{ color: "#3b5068", fontSize: 11, marginBottom: 16 }}>
        {description || "Drop a silhouette v4 JSON here, or click to browse"}
      </div>
      <div style={{ color: "#172030", fontSize: 9 }}>
        Expects v4 schema with: contour, landmarks, proportion, strokes,
        body_regions, biomechanics, style_deviation, shape_complexity,
        volumetric_estimates, convex_hull, width_profile, medial_axis
      </div>
      {error && (
        <div style={{
          color: "#ef4444", fontSize: 10, marginTop: 16,
          padding: "8px 12px", background: "rgba(239,68,68,.08)", borderRadius: 6,
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
