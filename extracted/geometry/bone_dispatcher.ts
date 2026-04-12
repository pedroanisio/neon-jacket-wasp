function boneGeometry(bone: BoneData): THREE.BufferGeometry {
  const cls = bone.classification;
  const l = bone.length;
  const w = bone.width;
  const d = bone.depth;

  switch (cls) {
    case "long": {
      return longBoneGeometry(l, w, d);
    }
    case "flat": {
      // Flattened box — cranial/rib bones, with slight curvature
      const geo = new THREE.BoxGeometry(w, l * 0.15, d, 4, 1, 4);
      // Bend flat bones slightly for anatomical curvature
      const pos = geo.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i);
        const z = pos.getZ(i);
        const dist = Math.sqrt(x * x + z * z);
        pos.setY(i, pos.getY(i) + dist * 0.05);
      }
      geo.computeVertexNormals();
      return geo;
    }
    case "irregular": {
      // Organic-looking shape: smooth icosahedron with subtle perturbation
      const ico = new THREE.IcosahedronGeometry(1, 2);
      const pos = ico.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        const len = Math.sqrt(x * x + y * y + z * z) || 1;
        const nx = x / len, ny = y / len, nz = z / len;
        // Subtle organic noise — just enough to break perfect symmetry
        const noise = 1.0
          + 0.04 * Math.sin(nx * 5.3 + ny * 3.1)
          + 0.03 * Math.cos(nz * 4.7 + nx * 2.2);
        pos.setXYZ(i, nx * (w / 2) * noise, ny * (l / 2) * noise, nz * (d / 2) * noise);
      }
      ico.computeVertexNormals();
      return ico;
    }
    case "short": {
      // Rounded cube — carpals, tarsals
      const geo = new THREE.IcosahedronGeometry(1, 1);
      geo.scale(w / 2, l / 2, d / 2);
      return geo;
    }
    case "sesamoid": {
      // Smooth sphere — patella, sesamoids
      const r = Math.max(w, d, l) / 2;
      return new THREE.SphereGeometry(r, 12, 10);
    }
    default:
      return new THREE.SphereGeometry(l / 2, 8, 6);
  }
}
