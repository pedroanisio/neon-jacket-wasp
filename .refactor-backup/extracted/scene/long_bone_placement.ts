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
