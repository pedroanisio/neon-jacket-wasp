export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface RGBAColor {
  r: number;
  g: number;
  b: number;
  a: number;
}

export interface Transform {
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
}

export interface BoneData {
  id: string;
  name: string;
  classification: "long" | "short" | "flat" | "irregular" | "sesamoid";
  region: string;
  transform: Transform;
  length: number;
  width: number;
  depth: number;
  mass: number;
  parentBoneId: string | null;
}

export interface TendonData {
  id: string;
  name: string;
  attachedBoneId: string;
  localPosition: Vec3;
  length: number;
  crossSectionalArea?: number;
}

export interface MuscleData {
  id: string;
  name: string;
  region: string;
  type: string;
  origin: { tendonId: string; description: string };
  insertion: { tendonId: string; description: string };
  fiberDirection: Vec3;
  restingLength: number;
  volume: number;
  mass: number;
  fascicleArchitecture: string;
  pennationAngle?: number;
}

export interface JointData {
  id: string;
  name: string;
  type: string;
  transform: Transform;
  connectedBoneIds: string[];
  degreesOfFreedom: number;
}

export interface OrganData {
  id: string;
  name: string;
  system: string;
  transform: Transform;
  volume: number;
  mass: number;
  isVital: boolean;
  laterality: string;
}

export interface VesselData {
  id: string;
  name: string;
  vesselType: "artery" | "vein";
  path: Vec3[];
  averageLumenRadius: number;
  parentVesselId?: string | null;
}

export interface NerveData {
  id: string;
  name: string;
  type: string;
  path: Vec3[];
  parentNerveId?: string | null;
}

export interface LigamentData {
  id: string;
  name: string;
  originBoneId: string;
  originPosition: Vec3;
  insertionBoneId: string;
  insertionPosition: Vec3;
  restingLength: number;
}

export interface CartilageData {
  id: string;
  name: string;
  type: "hyaline" | "fibrocartilage";
  thickness: number;
  surfaceArea: number;
  boneId?: string;
  jointId: string;
}

export interface HumanBodyData {
  schemaVersion: string;
  id: string;
  name?: string;
  proportions: {
    biologicalSex?: string;
    totalHeight: number;
    weight: number;
  };
  skeleton: BoneData[];
  joints: JointData[];
  tendons: TendonData[];
  muscles: MuscleData[];
  organs: OrganData[];
  vascularSystem: VesselData[];
  nerves: NerveData[];
  ligaments: LigamentData[];
  cartilage: CartilageData[];
  boneGeometries?: BoneGeometryData[];
  rendering?: RenderingLayerData;
}

export interface PBRMaterialData {
  baseColor?: RGBAColor;
  metalness?: number;
  roughness?: number;
  clearcoat?: number;
  clearcoatRoughness?: number;
  transmission?: number;
  thickness?: number;
  sheen?: number;
  sheenRoughness?: number;
  sheenColor?: RGBAColor;
  emissive?: RGBAColor;
  emissiveIntensity?: number;
}

export interface EntityRenderOverrideData {
  entityId: string;
  color?: RGBAColor;
  opacity?: number;
  visible?: boolean;
  material?: PBRMaterialData;
}

export interface RenderingLayerData {
  muscleOverrides?: EntityRenderOverrideData[];
  boneOverrides?: EntityRenderOverrideData[];
  organOverrides?: EntityRenderOverrideData[];
  vesselOverrides?: EntityRenderOverrideData[];
  globalOpacity?: number;
}

export interface IndexedMeshLODData {
  level: number;
  vertexCount: number;
  triangleCount: number;
  vertices: {
    positions: number[];
    normals?: number[];
    uvs?: number[];
  };
  indices: number[];
}

export interface IndexedMeshGeometryData {
  geometryType: "indexed_mesh";
  id: string;
  boneId: string;
  lods: IndexedMeshLODData[];
  isClosed?: boolean;
  isManifold?: boolean;
}

export interface ExternalAssetGeometryData {
  geometryType: "external_asset";
  id: string;
  boneId: string;
  uri: string;
  format: string;
  contentHash?: string;
  byteSize?: number;
  coordinateSpace?: { upAxis: string; units: string; handedness: string };
  lodVariants?: { level: number; uri: string; format: string; approximateTriangleCount?: number }[];
}

export type BoneGeometryData =
  | { geometryType: "parametric_csg"; id: string; boneId: string; csgTree: CSGNode; collisionHull?: string }
  | { geometryType: "indexed_mesh"; id: string; boneId: string; lods: IndexedMeshLODData[]; isClosed?: boolean; isManifold?: boolean }
  | ExternalAssetGeometryData;
