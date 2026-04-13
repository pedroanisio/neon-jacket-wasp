  for (const muscle of body.muscles) {
    const renderOverride = muscleOverrideById.get(muscle.id);
    if (renderOverride?.visible === false) continue;
    const originTendon = tendonById.get(muscle.origin.tendonId);
    const insertionTendon = tendonById.get(muscle.insertion.tendonId);
    if (!originTendon || !insertionTendon) continue;

    const originBone = boneDataById.get(originTendon.attachedBoneId);
    const insertionBone = boneDataById.get(insertionTendon.attachedBoneId);
    if (!originBone || !insertionBone) continue;

    // World positions = bone position + tendon local offset
    const oPos = new THREE.Vector3(
      originBone.transform.position.x + originTendon.localPosition.x,
      originBone.transform.position.y + originTendon.localPosition.y,
      originBone.transform.position.z + originTendon.localPosition.z,
    );
    const iPos = new THREE.Vector3(
      insertionBone.transform.position.x + insertionTendon.localPosition.x,
      insertionBone.transform.position.y + insertionTendon.localPosition.y,
      insertionBone.transform.position.z + insertionTendon.localPosition.z,
    );

    // Muscle belly: curved spindle tube between origin and insertion
    // Multiple control points for anatomical curvature
    const mid = oPos.clone().add(iPos).multiplyScalar(0.5);
    const span = oPos.distanceTo(iPos);
    const bulge = span * 0.15;

    // Compute a bulge direction perpendicular to the muscle span.
    // fiberDirection points along the fiber axis (roughly parallel to span),
    // so using it directly as the bulge offset creates loops/twists.
    // Instead: cross(spanDir, fiberDir) gives a perpendicular direction,
    // and we bias it outward from the body centerline (x=0, z≈10).
    const spanDir = iPos.clone().sub(oPos);
    if (spanDir.lengthSq() > 0) spanDir.normalize();
    const fiberDir = toV3(muscle.fiberDirection).normalize();
    const bulgeDir = new THREE.Vector3().crossVectors(spanDir, fiberDir);
    if (bulgeDir.lengthSq() < 1e-6) {
      // fiberDir is parallel to span — pick an arbitrary perpendicular
      const ref = Math.abs(spanDir.y) < 0.9
        ? new THREE.Vector3(0, 1, 0)
        : new THREE.Vector3(1, 0, 0);
      bulgeDir.crossVectors(spanDir, ref);
    }
    bulgeDir.normalize();

    // Ensure bulge pushes outward from body center (x=0, z≈10)
    const outward = new THREE.Vector3(mid.x, 0, mid.z - 10);
    if (outward.lengthSq() > 0.01 && bulgeDir.dot(outward) < 0) {
      bulgeDir.negate();
    }

    // 5 control points for smoother curvature
    const q1 = oPos.clone().lerp(mid, 0.25).add(bulgeDir.clone().multiplyScalar(bulge * 0.6));
    const q2 = oPos.clone().lerp(mid, 0.5).add(bulgeDir.clone().multiplyScalar(bulge));
    const q3 = mid.clone().lerp(iPos, 0.5).add(bulgeDir.clone().multiplyScalar(bulge * 0.8));
    const q4 = mid.clone().lerp(iPos, 0.75).add(bulgeDir.clone().multiplyScalar(bulge * 0.4));

    // Belly radius from volume: V ≈ π r² L → r = sqrt(V / (π L))
    const bellyR = Math.max(0.2, Math.min(3.0, Math.sqrt(muscle.volume / (Math.PI * Math.max(1, muscle.restingLength)))));
    const tR = bellyR * 0.2; // Tendon is much thinner than belly

    // Spindle-shaped tube: thin at tendons, thick at belly center
    const muscleGeo = variableRadiusTube(
      [oPos, q1, q2, q3, q4, iPos],
      24, // more segments for smooth spindle
      (t) => {
        // Smooth spindle profile: sin^0.7 creates a natural muscle belly shape
        const s = Math.pow(Math.sin(t * Math.PI), 0.7);
        return tR + (bellyR - tR) * s;
      },
      8,
    );

    const muscleMesh = new THREE.Mesh(
      muscleGeo,
      applyRenderOverride(muscleMaterial(muscle.region), renderOverride, globalOpacity),
    );
    muscleMesh.castShadow = true;
    muscleMesh.userData = { type: "muscle", id: muscle.id, name: muscle.name, region: muscle.region };
    layers.muscles.add(muscleMesh);
