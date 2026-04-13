export function applyPoseToBody(body: HumanBodyData, pose: PoseDefinition): HumanBodyData {
  if (pose.rotations.length === 0) return body;

  const boneById = new Map(body.skeleton.map((b) => [b.id, b]));

  // Build parent→children map
  const childrenOf = new Map<string, string[]>();
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
