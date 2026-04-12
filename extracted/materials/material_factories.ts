function boneMaterial(region: string): THREE.MeshPhysicalMaterial {
  const key = `bone_${region}`;
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: BONE_COLORS[region] ?? 0xe8dbb8,
    roughness: 0.45,
    metalness: 0.02,
    clearcoat: 0.2,
    clearcoatRoughness: 0.35,
    sheen: 0.15,
    sheenRoughness: 0.5,
    sheenColor: new THREE.Color(0xfffff0),
  });
  _materialCache.set(key, mat);
  return mat;
}
function muscleMaterial(region: string): THREE.MeshPhysicalMaterial {
  const key = `muscle_${region}`;
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: MUSCLE_COLORS[region] ?? 0xaa3333,
    roughness: 0.55,
    metalness: 0.0,
    clearcoat: 0.15,
    clearcoatRoughness: 0.4,
    transmission: 0.03,
    thickness: 0.8,
    sheen: 0.25,
    sheenRoughness: 0.4,
    sheenColor: new THREE.Color(0xff8888),
    side: THREE.DoubleSide,
  });
  _materialCache.set(key, mat);
  return mat;
}
function tendonMaterial(): THREE.MeshPhysicalMaterial {
  const key = "tendon";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xf0f0e8,
    roughness: 0.5,
    metalness: 0.0,
    clearcoat: 0.25,
    clearcoatRoughness: 0.25,
    sheen: 0.4,
    sheenRoughness: 0.35,
    sheenColor: new THREE.Color(0xeeeedd),
  });
  _materialCache.set(key, mat);
  return mat;
}
function arteryMaterial(): THREE.MeshPhysicalMaterial {
  const key = "artery";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xdd3322,
    roughness: 0.4,
    metalness: 0.0,
    clearcoat: 0.35,
    clearcoatRoughness: 0.15,
    transmission: 0.12,
    thickness: 0.4,
  });
  _materialCache.set(key, mat);
  return mat;
}
function veinMaterial(): THREE.MeshPhysicalMaterial {
  const key = "vein";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0x3344aa,
    roughness: 0.4,
    metalness: 0.0,
    clearcoat: 0.35,
    clearcoatRoughness: 0.15,
    transmission: 0.12,
    thickness: 0.4,
  });
  _materialCache.set(key, mat);
  return mat;
}
function nerveMaterial(): THREE.MeshPhysicalMaterial {
  const key = "nerve";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xeedd44,
    roughness: 0.5,
    metalness: 0.0,
    emissive: 0x332200,
    emissiveIntensity: 0.15,
    clearcoat: 0.15,
    clearcoatRoughness: 0.4,
  });
  _materialCache.set(key, mat);
  return mat;
}
function organMaterial(system: string): THREE.MeshPhysicalMaterial {
  const key = `organ_${system}`;
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: ORGAN_COLORS[system] ?? 0xddaa88,
    roughness: 0.5,
    metalness: 0.0,
    clearcoat: 0.3,
    clearcoatRoughness: 0.25,
    transmission: 0.1,
    thickness: 1.5,
    sheen: 0.15,
    sheenRoughness: 0.5,
    sheenColor: new THREE.Color(0xffcccc),
    side: THREE.DoubleSide,
  });
  _materialCache.set(key, mat);
  return mat;
}
function ligamentMaterial(): THREE.MeshPhysicalMaterial {
  const key = "ligament";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xd0d8c0,
    roughness: 0.55,
    metalness: 0.0,
    clearcoat: 0.2,
    clearcoatRoughness: 0.35,
    sheen: 0.25,
    sheenRoughness: 0.45,
    sheenColor: new THREE.Color(0xeeeedd),
  });
  _materialCache.set(key, mat);
  return mat;
}
function cartilageMaterial(type: string): THREE.MeshPhysicalMaterial {
  const key = `cartilage_${type}`;
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const color = type === "hyaline" ? 0xc8dde8 : 0xb0c8d0;
  const mat = new THREE.MeshPhysicalMaterial({
    color,
    roughness: 0.3,
    metalness: 0.0,
    clearcoat: 0.5,
    clearcoatRoughness: 0.15,
    transmission: 0.2,
    thickness: 0.6,
  });
  _materialCache.set(key, mat);
  return mat;
}
function jointMaterial(): THREE.MeshPhysicalMaterial {
  const key = "joint";
  if (_materialCache.has(key)) return _materialCache.get(key) as THREE.MeshPhysicalMaterial;
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0x66aadd,
    roughness: 0.25,
    metalness: 0.1,
    clearcoat: 0.5,
    clearcoatRoughness: 0.1,
    emissive: 0x112244,
    emissiveIntensity: 0.2,
  });
  _materialCache.set(key, mat);
  return mat;
}
