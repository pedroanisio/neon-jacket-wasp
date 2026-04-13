export type LayerName =
  | "skeleton"
  | "joints"
  | "muscles"
  | "tendons"
  | "organs"
  | "arteries"
  | "veins"
  | "nerves"
  | "ligaments"
  | "cartilage";
export const ALL_LAYERS: LayerName[] = [
  "skeleton", "joints", "muscles", "tendons",
  "organs", "arteries", "veins", "nerves",
  "ligaments", "cartilage",
];
export const DEFAULT_VISIBLE: Set<LayerName> = new Set(["skeleton", "joints", "muscles"]);
