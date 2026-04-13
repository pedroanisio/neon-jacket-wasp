function indexedMeshToGeometry(mesh: IndexedMeshGeometryData): THREE.BufferGeometry {
  const lod = [...mesh.lods].sort((a, b) => a.level - b.level)[0];
  if (!lod) {
    return new THREE.BufferGeometry();
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(lod.vertices.positions, 3));
  geo.setIndex(lod.indices);
  if (lod.vertices.normals && lod.vertices.normals.length === lod.vertices.positions.length) {
    geo.setAttribute("normal", new THREE.Float32BufferAttribute(lod.vertices.normals, 3));
  } else {
    geo.computeVertexNormals();
  }
  if (lod.vertices.uvs && lod.vertices.uvs.length === (lod.vertexCount * 2)) {
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(lod.vertices.uvs, 2));
  }
  return geo;
}
