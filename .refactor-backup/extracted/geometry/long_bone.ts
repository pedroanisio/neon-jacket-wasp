function longBoneGeometry(length: number, width: number, depth: number): THREE.BufferGeometry {
  const r = (width + depth) / 4;
  const epiphR = r * 1.35;
  const diaphR = r * 0.7;
  const h = Math.max(0.5, length);

  const nPts = 7;
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i < nPts; i++) {
    pts.push(new THREE.Vector3(0, -h / 2 + (h * i) / (nPts - 1), 0));
  }

  return variableRadiusTube(pts, 16, (t) => {
    const endProx = Math.exp(-((t * 5) ** 2));
    const endDist = Math.exp(-(((1 - t) * 5) ** 2));
    const endInfluence = Math.max(endProx, endDist);
    return diaphR + (epiphR - diaphR) * endInfluence;
  }, 10);
}
