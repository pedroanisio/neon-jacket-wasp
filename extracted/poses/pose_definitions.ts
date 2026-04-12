interface PoseJointRotation {
  /** Regex matched against bone.name (case-insensitive) */
  boneNamePattern: RegExp;
  /** Euler rotation [x, y, z] in radians applied at this bone's proximal joint */
  euler: [number, number, number];
}
export interface PoseDefinition {
  id: string;
  label: string;
  rotations: PoseJointRotation[];
}
export const AVAILABLE_POSES: PoseDefinition[] = [
  {
    id: "rest",
    label: "T-Pose",
    rotations: [],
  },
  {
    id: "a-pose",
    label: "A-Pose",
    rotations: [
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0, 0, 0.75] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [0, 0, -0.75] },
    ],
  },
  {
    id: "anatomical",
    label: "Anatomical",
    rotations: [
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0, 0, 1.4] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [0, 0, -1.4] },
    ],
  },
  {
    id: "relaxed",
    label: "Relaxed",
    rotations: [
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0.15, 0, 1.35] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [0.15, 0, -1.35] },
      { boneNamePattern: /^radius\s*\(r\)/i, euler: [0.3, 0, 0] },
      { boneNamePattern: /^ulna\s*\(r\)/i, euler: [0.3, 0, 0] },
      { boneNamePattern: /^radius\s*\(l\)/i, euler: [0.3, 0, 0] },
      { boneNamePattern: /^ulna\s*\(l\)/i, euler: [0.3, 0, 0] },
    ],
  },
  {
    id: "walking",
    label: "Walking",
    rotations: [
      // Arms swing (opposite to legs)
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0.3, 0, 1.3] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [-0.3, 0, -1.3] },
      { boneNamePattern: /^radius\s*\(r\)/i, euler: [0.35, 0, 0] },
      { boneNamePattern: /^ulna\s*\(r\)/i, euler: [0.35, 0, 0] },
      // Right leg forward, knee bent
      { boneNamePattern: /^femur\s*\(r\)/i, euler: [-0.4, 0, 0] },
      { boneNamePattern: /^tibia\s*\(r\)/i, euler: [0.5, 0, 0] },
      { boneNamePattern: /^fibula\s*\(r\)/i, euler: [0.5, 0, 0] },
      // Left leg back
      { boneNamePattern: /^femur\s*\(l\)/i, euler: [0.2, 0, 0] },
    ],
  },
  {
    id: "arms-raised",
    label: "Arms Raised",
    rotations: [
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0, 0, -1.2] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [0, 0, 1.2] },
    ],
  },
  {
    id: "fighting",
    label: "Fighter",
    rotations: [
      // Guard stance: arms up, fists near face
      { boneNamePattern: /^humerus\s*\(r\)/i, euler: [0.8, 0.3, 0.5] },
      { boneNamePattern: /^humerus\s*\(l\)/i, euler: [0.8, -0.3, -0.5] },
      { boneNamePattern: /^radius\s*\(r\)/i, euler: [1.2, 0, 0] },
      { boneNamePattern: /^ulna\s*\(r\)/i, euler: [1.2, 0, 0] },
      { boneNamePattern: /^radius\s*\(l\)/i, euler: [1.4, 0, 0] },
      { boneNamePattern: /^ulna\s*\(l\)/i, euler: [1.4, 0, 0] },
      // Staggered stance
      { boneNamePattern: /^femur\s*\(r\)/i, euler: [-0.15, 0, 0.08] },
      { boneNamePattern: /^femur\s*\(l\)/i, euler: [-0.1, 0, -0.08] },
      { boneNamePattern: /^tibia\s*\(r\)/i, euler: [0.2, 0, 0] },
      { boneNamePattern: /^tibia\s*\(l\)/i, euler: [0.15, 0, 0] },
      { boneNamePattern: /^fibula\s*\(r\)/i, euler: [0.2, 0, 0] },
      { boneNamePattern: /^fibula\s*\(l\)/i, euler: [0.15, 0, 0] },
    ],
  },
];
