/** Single source of truth for region color palettes. */

/** Stroke colors keyed by body region. */
export const REGION_COLORS: Readonly<Record<string, string>> = {
  head: "#5eead4",
  neck_shoulder: "#818cf8",
  torso: "#f59e0b",
  legs: "#fb923c",
  feet: "#f472b6",
};

/** Body-region band colors (indexed). */
export const BODY_REGION_COLORS: ReadonlyArray<string> = [
  "#0d9488",
  "#0891b2",
  "#6366f1",
  "#7c3aed",
  "#a855f7",
  "#d946ef",
  "#ec4899",
  "#f43f5e",
  "#ef4444",
];
