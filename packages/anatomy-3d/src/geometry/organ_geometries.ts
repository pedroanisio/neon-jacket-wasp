function organGeometry(organ: OrganData): THREE.BufferGeometry {
  const name = organ.name.toLowerCase();
  const vol = organ.volume;
  const k = Math.cbrt(vol / ((4 / 3) * Math.PI));

  if (name.includes("heart")) {
    return heartGeometry(k);
  }
  if (name.includes("lung")) {
    return lungGeometry(k, name.includes("(l)") || name.includes("left") ? -1 : 1);
  }
  if (name.includes("brain") || name.includes("cerebr")) {
    return brainGeometry(k);
  }
  if (name.includes("kidney")) {
    return kidneyGeometry(k);
  }
  if (name.includes("liver")) {
    return liverGeometry(k);
  }
  if (name.includes("stomach")) {
    return stomachGeometry(k);
  }
  if (name.includes("intestin")) {
    return intestineGeometry(k, name.includes("large") || name.includes("colon"));
  }
  if (name.includes("bladder")) {
    return bladderGeometry(k);
  }

  // Default: organic ellipsoid with perturbation
  return defaultOrganGeometry(vol);
}
function heartGeometry(k: number): THREE.BufferGeometry {
  // Heart-like shape: rounded top with tapered bottom (apex)
  const pts: THREE.Vector2[] = [];
  for (let i = 0; i <= 20; i++) {
    const t = i / 20;
    const angle = t * Math.PI;
    // Heart profile: wide at top 1/3, tapering to apex at bottom
    let r: number;
    if (t < 0.15) {
      // Flat top (base of heart, where vessels attach)
      r = 0.6 + t * 1.5;
    } else if (t < 0.55) {
      // Wide rounded body
      r = Math.sin(angle) * 1.1;
    } else {
      // Taper to apex
      const taper = (1 - t) / 0.45;
      r = Math.sin(angle) * 0.9 * taper;
    }
    pts.push(new THREE.Vector2(Math.max(0.01, r * k * 1.0), (t - 0.5) * k * 2.8));
  }
  const geo = new THREE.LatheGeometry(pts, 16);
  geo.computeVertexNormals();
  return geo;
}
function lungGeometry(k: number, side: number): THREE.BufferGeometry {
  // Elongated ellipsoid with medial flat surface and rounded lateral
  const geo = new THREE.SphereGeometry(1, 16, 12);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    // Flatten medial side (towards center of body)
    if (x * side < 0) {
      x *= 0.6;
    }
    // Taper top (apex)
    const yNorm = (y + 1) / 2; // 0=bottom, 1=top
    const taperTop = yNorm > 0.7 ? 1 - (yNorm - 0.7) / 0.3 * 0.4 : 1;
    // Widen bottom
    const widenBot = yNorm < 0.3 ? 1 + (0.3 - yNorm) / 0.3 * 0.15 : 1;
    pos.setXYZ(i,
      x * k * 1.2 * taperTop * widenBot,
      y * k * 1.8,
      z * k * 1.0 * taperTop * widenBot,
    );
  }
  geo.computeVertexNormals();
  return geo;
}
function brainGeometry(k: number): THREE.BufferGeometry {
  // Sphere with sulci/gyri wrinkles via vertex displacement
  const geo = new THREE.IcosahedronGeometry(k * 1.3, 4);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const len = Math.sqrt(x * x + y * y + z * z) || 1;
    const nx = x / len, ny = y / len, nz = z / len;
    // Multi-frequency noise for wrinkled surface
    const wrinkle =
      0.06 * Math.sin(nx * 18 + nz * 12) * Math.cos(ny * 15 + nx * 8) +
      0.04 * Math.sin(ny * 22 + nz * 16) * Math.cos(nx * 20) +
      0.03 * Math.cos(nz * 28 + nx * 14 + ny * 10);
    const r = len * (1 + wrinkle);
    // Slightly flatten top, elongate front-back
    pos.setXYZ(i, nx * r * 1.05, ny * r * 0.85, nz * r * 1.15);
  }
  geo.computeVertexNormals();
  return geo;
}
function kidneyGeometry(k: number): THREE.BufferGeometry {
  // Bean shape using a torus section
  const geo = new THREE.TorusGeometry(k * 0.8, k * 0.5, 12, 16, Math.PI * 1.3);
  geo.rotateX(Math.PI / 2);
  geo.rotateZ(Math.PI * 0.15);
  geo.computeVertexNormals();
  return geo;
}
function liverGeometry(k: number): THREE.BufferGeometry {
  // Wide, flat, wedge-shaped organ
  const geo = new THREE.SphereGeometry(1, 14, 10);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    // Flatten vertically, widen horizontally
    // Right lobe larger than left
    const xBias = x > 0 ? 1.3 : 0.8;
    pos.setXYZ(i, x * k * 2.0 * xBias, y * k * 0.6, z * k * 1.4);
  }
  geo.computeVertexNormals();
  return geo;
}
function stomachGeometry(k: number): THREE.BufferGeometry {
  // J-shaped curved tube with variable radius
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i <= 12; i++) {
    const t = i / 12;
    const angle = t * Math.PI * 0.8;
    pts.push(new THREE.Vector3(
      Math.sin(angle) * k * 1.5,
      -t * k * 2.5,
      Math.cos(angle) * k * 0.3,
    ));
  }
  return variableRadiusTube(pts, 16, (t) => {
    // Wide at fundus (top), narrow at pylorus (bottom)
    const fundus = Math.exp(-((t * 3) ** 2)) * 0.4;
    const body = Math.sin(t * Math.PI) * 0.6;
    return k * (0.3 + fundus + body);
  }, 10);
}
function intestineGeometry(k: number, isLarge: boolean): THREE.BufferGeometry {
  // Coiled tube
  const r = isLarge ? k * 0.5 : k * 0.2;
  const coilR = isLarge ? k * 2.0 : k * 1.5;
  const turns = isLarge ? 1.5 : 4;
  const pts: THREE.Vector3[] = [];
  const nPts = Math.ceil(turns * 12);
  for (let i = 0; i <= nPts; i++) {
    const t = i / nPts;
    const angle = t * turns * Math.PI * 2;
    pts.push(new THREE.Vector3(
      Math.cos(angle) * coilR * (0.5 + t * 0.5),
      -t * k * 3,
      Math.sin(angle) * coilR * (0.5 + t * 0.5),
    ));
  }
  return variableRadiusTube(pts, Math.max(12, nPts * 2), () => r, 8);
}
function bladderGeometry(k: number): THREE.BufferGeometry {
  // Pear-shaped: wider at top, narrow at base
  const pts: THREE.Vector2[] = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16;
    const r = Math.sin(t * Math.PI) * (1 - t * 0.3);
    pts.push(new THREE.Vector2(Math.max(0.01, r * k * 1.0), (t - 0.5) * k * 1.6));
  }
  return new THREE.LatheGeometry(pts, 12);
}
function defaultOrganGeometry(vol: number): THREE.BufferGeometry {
  // Organic ellipsoid with slight perturbation
  const k = Math.cbrt(vol / ((4 / 3) * Math.PI * 1.0 * 1.5 * 0.8));
  const a = k * 1.0;
  const b = k * 1.5;
  const c = k * 0.8;

  const geo = new THREE.SphereGeometry(1, 14, 10);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const len = Math.sqrt(x * x + y * y + z * z) || 1;
    const nx = x / len, ny = y / len, nz = z / len;
    // Subtle organic noise
    const noise = 1.0 + 0.05 * Math.sin(nx * 10 + ny * 8) * Math.cos(nz * 12);
    pos.setXYZ(i, nx * a * noise, ny * b * noise, nz * c * noise);
  }
  geo.computeVertexNormals();
  return geo;
}
