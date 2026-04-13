export function pick(
  handle: SceneHandle,
  ndc: THREE.Vector2,
  visibleLayers: Set<LayerName>,
): PickResult | null {
  _raycaster.setFromCamera(ndc, handle.camera);

  const targets: THREE.Object3D[] = [];
  for (const ln of ALL_LAYERS) {
    if (visibleLayers.has(ln)) targets.push(handle.layers[ln]);
  }

  const hits = _raycaster.intersectObjects(targets, true);
  if (hits.length === 0) return null;

  const hit = hits[0];
  if (!hit) return null;
  const ud = hit.object.userData as Record<string, unknown>;
  if (!ud?.name) return null;
  return { name: ud.name as string, type: ud.type as string, extra: ud };
}
