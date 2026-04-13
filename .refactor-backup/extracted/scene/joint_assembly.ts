  for (const joint of body.joints) {
    const dof = joint.degreesOfFreedom;
    const r = dof >= 3 ? 1.2 : dof === 2 ? 0.9 : 0.65;
    const geo = new THREE.SphereGeometry(r, 12, 8);
    const mesh = new THREE.Mesh(geo, jointMaterial());
    mesh.position.set(
      joint.transform.position.x,
      joint.transform.position.y,
      joint.transform.position.z,
    );
    mesh.userData = { type: "joint", id: joint.id, name: joint.name, dof };
    layers.joints.add(mesh);
    jointMap.set(joint.id, mesh);
