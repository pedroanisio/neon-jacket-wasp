  for (const bone of body.skeleton) {
    if (bone.parentBoneId) {
      const list = childrenOf.get(bone.parentBoneId) || [];
      list.push(bone.id);
      childrenOf.set(bone.parentBoneId, list);
    }
  }

  // Map bone IDs to their pose rotation (first matching pattern wins)
  const rotationMap = new Map<string, THREE.Quaternion>();
  for (const bone of body.skeleton) {
    for (const rot of pose.rotations) {
      if (rot.boneNamePattern.test(bone.name)) {
        rotationMap.set(
          bone.id,
          new THREE.Quaternion().setFromEuler(new THREE.Euler(rot.euler[0], rot.euler[1], rot.euler[2])),
        );
        break;
      }
    }
  }

  // FK traversal: compute new world positions
  const newPositions = new Map<string, Vec3>();

  function processNode(boneId: string, parentNewPos: Vec3, parentRestPos: Vec3, parentAccumQ: THREE.Quaternion): void {
    const bone = boneById.get(boneId)!;

    // This bone's local rotation (at its proximal joint)
    const localQ = rotationMap.get(boneId) ?? new THREE.Quaternion();
    const accumQ = parentAccumQ.clone().multiply(localQ);

    let newPos: Vec3;
    if (!bone.parentBoneId) {
      // Root bone: stays in place
      newPos = { ...bone.transform.position };
    } else {
      // Rotate rest-pose offset by accumulated rotation
      const offset = new THREE.Vector3(
        bone.transform.position.x - parentRestPos.x,
        bone.transform.position.y - parentRestPos.y,
        bone.transform.position.z - parentRestPos.z,
      );
      offset.applyQuaternion(accumQ);
      newPos = {
        x: parentNewPos.x + offset.x,
        y: parentNewPos.y + offset.y,
        z: parentNewPos.z + offset.z,
      };
    }

    newPositions.set(boneId, newPos);

    // Recurse to children
    for (const childId of childrenOf.get(boneId) || []) {
      processNode(childId, newPos, bone.transform.position, accumQ);
    }
  }

  // Start FK from root bones
  for (const bone of body.skeleton) {
    if (!bone.parentBoneId) {
      const rootQ = rotationMap.get(bone.id) ?? new THREE.Quaternion();
      newPositions.set(bone.id, { ...bone.transform.position });
      for (const childId of childrenOf.get(bone.id) || []) {
        processNode(childId, bone.transform.position, bone.transform.position, rootQ);
      }
    }
  }

  // Build modified skeleton with posed positions
  const newSkeleton = body.skeleton.map((bone) => {
    const p = newPositions.get(bone.id);
    if (!p) return bone;
    return { ...bone, transform: { ...bone.transform, position: p } };
  });

  // Update joint positions: average of connected bone positions
  const newJoints = body.joints.map((joint) => {
    if (joint.connectedBoneIds.length === 0) return joint;
    let sx = 0, sy = 0, sz = 0, n = 0;
    for (const bId of joint.connectedBoneIds) {
      const p = newPositions.get(bId);
      if (p) { sx += p.x; sy += p.y; sz += p.z; n++; }
    }
    if (n === 0) return joint;
    return { ...joint, transform: { ...joint.transform, position: { x: sx / n, y: sy / n, z: sz / n } } };
  });

  return { ...body, skeleton: newSkeleton, joints: newJoints };
}

// ═══════════════════════════════════════════════════════════════════════
// 5. SCENE LAYER GROUPS — toggleable visibility
// ═══════════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════════
// 6. SCENE ASSEMBLY — builds Three.js scene from HumanBody JSON
// ═══════════════════════════════════════════════════════════════════════

export type ThemeMode = "dark" | "light";

interface ThemeConfig {
  sceneBg: number;
  fogColor: number;
  fogDensity: number;
  groundColor: number;
  gridA: number;
  gridB: number;
  hemiSky: number;
  hemiGround: number;
  hemiIntensity: number;
  ambientColor: number;
  ambientIntensity: number;
  keyIntensity: number;
  fillIntensity: number;
  rimIntensity: number;
  exposure: number;
  bloomStrength: number;
}

const THEMES: Record<ThemeMode, ThemeConfig> = {
  dark: {
    sceneBg: 0x0c0c14, fogColor: 0x0c0c14, fogDensity: 0.0008,
    groundColor: 0x111118, gridA: 0x222244, gridB: 0x181828,
    hemiSky: 0xddeeff, hemiGround: 0x886644, hemiIntensity: 1.5,
    ambientColor: 0xffffff, ambientIntensity: 0.8,
    keyIntensity: 2.5, fillIntensity: 1.2, rimIntensity: 0.8,
    exposure: 1.6, bloomStrength: 0.1,
  },
  light: {
    sceneBg: 0xeef2f7, fogColor: 0xeef2f7, fogDensity: 0.0004,
    groundColor: 0xd8dce4, gridA: 0xbbc0cc, gridB: 0xd0d4dc,
    hemiSky: 0xffffff, hemiGround: 0xccbbaa, hemiIntensity: 2.0,
    ambientColor: 0xffffff, ambientIntensity: 1.0,
    keyIntensity: 2.0, fillIntensity: 1.5, rimIntensity: 0.6,
    exposure: 1.8, bloomStrength: 0.03,
  },
};

export interface UITheme {
  bg: string;
  bgOverlay: string;
  border: string;
  text: string;
  textMuted: string;
  textDim: string;
  panelBg: string;
  panelBorder: string;
  btnBg: string;
  btnBorder: string;
  btnText: string;
  btnActiveText: string;
  inactiveText: string;
}

const UI_THEMES: Record<ThemeMode, UITheme> = {
  dark: {
    bg: "#0c0c14", bgOverlay: "rgba(12,12,20,.92)", border: "rgba(100,120,180,.15)",
    text: "#e8e8f0", textMuted: "#556688", textDim: "#334455",
    panelBg: "rgba(12,12,20,.92)", panelBorder: "rgba(100,120,180,.15)",
    btnBg: "rgba(60,80,120,.12)", btnBorder: "rgba(80,100,140,.2)",
    btnText: "#8899bb", btnActiveText: "#c8ccd4", inactiveText: "#556677",
  },
  light: {
    bg: "#eef2f7", bgOverlay: "rgba(255,255,255,.94)", border: "rgba(100,120,160,.2)",
    text: "#1a1e2a", textMuted: "#667889", textDim: "#8899aa",
    panelBg: "rgba(255,255,255,.94)", panelBorder: "rgba(100,120,160,.18)",
    btnBg: "rgba(100,120,160,.08)", btnBorder: "rgba(100,120,160,.2)",
    btnText: "#4a5568", btnActiveText: "#1a1e2a", inactiveText: "#8899aa",
  },
};

export interface SceneHandle {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  composer: EffectComposer;
  controls: OrbitControls;
  layers: Record<LayerName, THREE.Group>;
  boneMap: Map<string, THREE.Mesh>;
  jointMap: Map<string, THREE.Mesh>;
  themeRefs: {
    hemi: THREE.HemisphereLight;
    ambient: THREE.AmbientLight;
    keyLight: THREE.DirectionalLight;
    fillLight: THREE.DirectionalLight;
    rimLight: THREE.DirectionalLight;
    ground: THREE.Mesh;
    grid: THREE.GridHelper;
    bloom: UnrealBloomPass;
  };
  dispose: () => void;
}

export function applyTheme(handle: SceneHandle, mode: ThemeMode): void {
  const t = THEMES[mode];
  const { scene, renderer, themeRefs } = handle;

  scene.background = new THREE.Color(t.sceneBg);
  (scene.fog as THREE.FogExp2).color.set(t.fogColor);
  (scene.fog as THREE.FogExp2).density = t.fogDensity;

  renderer.toneMappingExposure = t.exposure;

  themeRefs.hemi.color.set(t.hemiSky);
  themeRefs.hemi.groundColor.set(t.hemiGround);
  themeRefs.hemi.intensity = t.hemiIntensity;

  themeRefs.ambient.color.set(t.ambientColor);
  themeRefs.ambient.intensity = t.ambientIntensity;

  themeRefs.keyLight.intensity = t.keyIntensity;
  themeRefs.fillLight.intensity = t.fillIntensity;
  themeRefs.rimLight.intensity = t.rimIntensity;

  ((themeRefs.ground as THREE.Mesh).material as THREE.MeshStandardMaterial).color.set(t.groundColor);

  themeRefs.grid.geometry.dispose();
  (themeRefs.grid.material as THREE.Material).dispose();
  scene.remove(themeRefs.grid);
  const newGrid = new THREE.GridHelper(200, 40, t.gridA, t.gridB);
  newGrid.position.y = 0.05;
  scene.add(newGrid);
  themeRefs.grid = newGrid;

  themeRefs.bloom.strength = t.bloomStrength;
}

function toV3(v: Vec3): THREE.Vector3 {
  return new THREE.Vector3(v.x, v.y, v.z);
}

export function buildScene(container: HTMLElement, body: HumanBodyData): SceneHandle {
  const W = container.clientWidth;
  const H = container.clientHeight;

  // ── Renderer ──
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.6;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  // ── Scene ──
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0c0c14);
  scene.fog = new THREE.FogExp2(0x0c0c14, 0.0008);

  // Environment map disabled — direct lighting is sufficient for bone/muscle PBR.
  // PMREM generation can corrupt materials on some WebGL implementations.

  // ── Camera — framing full body (Y range 0–180 cm) ──
  const camera = new THREE.PerspectiveCamera(40, W / H, 0.5, 500);
  camera.position.set(60, 100, 120);
  camera.lookAt(0, 90, 0);

  // ── Controls ──
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 90, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 15;
  controls.maxDistance = 350;
  controls.maxPolarAngle = Math.PI * 0.95;
  controls.update();

  // ── Lighting — bright clinical/studio setup ──
  // Higher intensities to counteract ACES filmic tone mapping compression.
  // Target: bones should appear as warm ivory, not dark gray.
  const hemi = new THREE.HemisphereLight(0xddeeff, 0x886644, 1.5);
  scene.add(hemi);

  const ambient = new THREE.AmbientLight(0xffffff, 0.8);
  scene.add(ambient);

  const keyLight = new THREE.DirectionalLight(0xfff5e6, 2.5);
  keyLight.position.set(60, 150, 80);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(2048, 2048);
  keyLight.shadow.camera.near = 1;
  keyLight.shadow.camera.far = 400;
  keyLight.shadow.camera.left = -80;
  keyLight.shadow.camera.right = 80;
  keyLight.shadow.camera.top = 200;
  keyLight.shadow.camera.bottom = -20;
  keyLight.shadow.bias = -0.001;
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0xaaccff, 1.2);
  fillLight.position.set(-50, 100, -40);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xffcc88, 0.8);
  rimLight.position.set(0, 50, -100);
  scene.add(rimLight);

  const topLight = new THREE.PointLight(0xffffff, 1.0, 400);
  topLight.position.set(0, 200, 0);
  scene.add(topLight);

  // ── Ground plane ──
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(600, 600),
    new THREE.MeshStandardMaterial({ color: 0x111118, roughness: 0.9, metalness: 0.1 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  let grid = new THREE.GridHelper(200, 40, 0x222244, 0x181828);
  grid.position.y = 0.05;
  scene.add(grid);

  // ── Post-processing ──
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));

  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(W, H), 0.15, 0.4, 0.9,
  );
  composer.addPass(bloomPass);

  // SMAA omitted — rely on renderer MSAA (antialias: true in WebGLRenderer)

  // ── Layer groups ──
  const layers: Record<LayerName, THREE.Group> = {} as any;
  for (const ln of ALL_LAYERS) {
    const g = new THREE.Group();
    g.name = ln;
    g.visible = DEFAULT_VISIBLE.has(ln);
    scene.add(g);
    layers[ln] = g;
  }

  // ── Index maps ──
  const boneMap = new Map<string, THREE.Mesh>();
  const boneDataById = new Map<string, BoneData>();
  const tendonById = new Map<string, TendonData>();
  const jointMap = new Map<string, THREE.Mesh>();
  const jointDataById = new Map<string, JointData>();

  for (const b of body.skeleton) boneDataById.set(b.id, b);
  for (const t of body.tendons) tendonById.set(t.id, t);
  for (const j of body.joints) jointDataById.set(j.id, j);

  // ════════════════════════════════════════════════════════════════════
  // SKELETON — 206 bones
  //
  // Placement rules:
  //   - Each bone's transform.position = its proximal joint (origin).
  //   - LONG bones span from their OWN position toward their children's
  //     positions. The mesh is placed at the midpoint, Y axis aligned
  //     along self→children direction. Span length = bone.length.
  //   - ALL OTHER bones (flat, irregular, short, sesamoid): placed at
  //     their own anatomical position with rotation from transform.
  // ════════════════════════════════════════════════════════════════════

  const geometryByBoneId = new Map<string, BoneGeometryData>();
  if (body.boneGeometries) {
    for (const bg of body.boneGeometries) {
      geometryByBoneId.set(bg.boneId, bg);
    }
  }
  const globalOpacity = body.rendering?.globalOpacity ?? 1;
  const boneOverrideById = new Map((body.rendering?.boneOverrides ?? []).map((o) => [o.entityId, o]));
  const muscleOverrideById = new Map((body.rendering?.muscleOverrides ?? []).map((o) => [o.entityId, o]));
  const organOverrideById = new Map((body.rendering?.organOverrides ?? []).map((o) => [o.entityId, o]));
  const vesselOverrideById = new Map((body.rendering?.vesselOverrides ?? []).map((o) => [o.entityId, o]));

  // Build parent→children map for long bone span computation
  const childrenOfBone = new Map<string, BoneData[]>();
  for (const b of body.skeleton) {
    if (b.parentBoneId) {
      const list = childrenOfBone.get(b.parentBoneId) || [];
      list.push(b);
      childrenOfBone.set(b.parentBoneId, list);
    }
  }

  // Compute the distal end of a long bone: average position of its children,
  // or fall back to extending along parent→self direction by bone.length.
  function longBoneDistalEnd(bone: BoneData): THREE.Vector3 {
    const bonePos = toV3(bone.transform.position);
    const children = childrenOfBone.get(bone.id);
    if (children && children.length > 0) {
      const avg = new THREE.Vector3();
      for (const child of children) {
        avg.add(toV3(child.transform.position));
      }
      avg.divideScalar(children.length);
      return avg;
    }
    // No children: extend along parent→self direction by bone.length
    const parent = bone.parentBoneId ? boneDataById.get(bone.parentBoneId) : undefined;
    if (parent) {
      const dir = bonePos.clone().sub(toV3(parent.transform.position));
      if (dir.lengthSq() > 0.01) {
        dir.normalize();
        return bonePos.clone().add(dir.multiplyScalar(bone.length));
      }
    }
    // Last resort: extend downward
    return bonePos.clone().add(new THREE.Vector3(0, -bone.length, 0));
  }

  // Helper: build inline geometry from indexed_mesh or parametric_csg
  const buildInlineGeometry = (
    geometryEntry: BoneGeometryData | undefined,
    bone: BoneData,
    spanLen?: number,
  ): THREE.BufferGeometry => {
    if (geometryEntry?.geometryType === "indexed_mesh" && "lods" in geometryEntry) {
      return indexedMeshToGeometry(geometryEntry as IndexedMeshGeometryData);
    }
    if (geometryEntry?.geometryType === "parametric_csg" && "csgTree" in geometryEntry) {
      return csgTreeToGeometry((geometryEntry as { csgTree: CSGNode }).csgTree);
    }
    if (spanLen !== undefined) {
      return longBoneGeometry(spanLen, bone.width, bone.depth);
    }
    return boneGeometry(bone);
  };

  for (const bone of body.skeleton) {
    const renderOverride = boneOverrideById.get(bone.id);
    if (renderOverride?.visible === false) continue;
    const mat = applyRenderOverride(boneMaterial(bone.region), renderOverride, globalOpacity);
    const geometryEntry = geometryByBoneId.get(bone.id);
    const bonePos = toV3(bone.transform.position);

    const isLong = bone.classification === "long";
    let meshPos: THREE.Vector3;
    let meshQuat: THREE.Quaternion | undefined;
    let meshEuler: THREE.Euler | undefined;
    let spanLen: number | undefined;

    if (isLong) {
      // Long bones span from own position (proximal) to distal end (children avg)
      const distalEnd = longBoneDistalEnd(bone);
      const dir = distalEnd.clone().sub(bonePos);
      const dist = dir.length();
      spanLen = Math.max(1, dist);
      meshPos = bonePos.clone().add(distalEnd).multiplyScalar(0.5);
      if (dist > 0.1) {
        const d = dir.normalize();
        const up = new THREE.Vector3(0, 1, 0);
        if (Math.abs(d.dot(up)) < 0.9999) {
          meshQuat = new THREE.Quaternion().setFromUnitVectors(up, d);
        }
      }
    } else {
      meshPos = bonePos;
      const rot = bone.transform.rotation;
      if (rot.x !== 0 || rot.y !== 0 || rot.z !== 0) {
        const D2R = Math.PI / 180;
        meshEuler = new THREE.Euler(rot.x * D2R, rot.y * D2R, rot.z * D2R, "XYZ");
      }
    }

    // Build mesh — use inline geometry (indexed_mesh, parametric_csg, or procedural).
    // External GLB assets are skipped: the available GLBs are procedural placeholders
    // with inverted normals and coordinate-space mismatches. The inline procedural
    // generators produce correct geometry with proper normals and placement.
    const inlineEntry = geometryEntry?.geometryType === "external_asset" ? undefined : geometryEntry;
    const geo = buildInlineGeometry(inlineEntry, bone, spanLen);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(meshPos);
    if (meshQuat) mesh.quaternion.copy(meshQuat);
    if (meshEuler) mesh.rotation.copy(meshEuler);

    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = { type: "bone", id: bone.id, name: bone.name, region: bone.region };
    layers.skeleton.add(mesh);
    boneMap.set(bone.id, mesh);
