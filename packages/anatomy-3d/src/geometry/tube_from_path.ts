function tubeFromPath(points: THREE.Vector3[], radius: number, segments?: number): THREE.BufferGeometry {
  if (points.length < 2) return new THREE.SphereGeometry(radius, 6, 4);
  const curve = new THREE.CatmullRomCurve3(points, false, "catmullrom", 0.5);
  const tubeSeg = segments ?? Math.max(4, Math.min(32, Math.ceil(curve.getLength() / 2)));
  return new THREE.TubeGeometry(curve, tubeSeg, radius, 6, false);
}
