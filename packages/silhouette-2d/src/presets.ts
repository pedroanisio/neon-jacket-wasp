/**
 * Animation preset functions.
 *
 * Each preset returns bone angles (radians) as a function of time.
 */

import type { BoneAngles, PresetFn } from "./types.js";

const Z: BoneAngles = {
  root: 0, spine: 0, neck: 0, head: 0,
  r_arm: 0, r_forearm: 0, l_arm: 0, l_forearm: 0,
  r_thigh: 0, r_shin: 0, r_foot: 0,
  l_thigh: 0, l_shin: 0, l_foot: 0,
};

export const PRESETS: Readonly<Record<string, PresetFn>> = {
  idle: (t) => {
    const b = Math.sin(t * 1.8) * 0.008;
    return {
      ...Z,
      spine: b, neck: b * 0.7,
      head: Math.sin(t * 2.4) * 0.006,
      r_arm: Math.sin(t * 1.2) * 0.01,
      l_arm: Math.sin(t * 1.2 + 0.5) * 0.01,
    };
  },

  breathe: (t) => {
    const p = Math.sin(t);
    return {
      ...Z,
      root: p * 0.005, spine: p * 0.018,
      neck: p * 0.012, head: Math.sin(t * 1.5) * 0.008,
      r_arm: p * 0.015, l_arm: p * 0.015,
      r_forearm: p * 0.008, l_forearm: p * 0.008,
    };
  },

  sway: (t) => {
    const s = Math.sin(t * 0.8);
    return {
      ...Z,
      root: s * 0.03, spine: s * -0.025,
      neck: s * -0.015, head: s * 0.01,
      r_arm: s * 0.04, l_arm: s * -0.04,
      r_forearm: s * 0.02, l_forearm: s * -0.02,
    };
  },

  contrapposto: (t) => {
    const s = Math.sin(t * 0.5);
    const a = Math.abs(s);
    const d = s > 0 ? 1 : -1;
    return {
      ...Z,
      root: d * a * 0.04, spine: d * a * -0.035,
      neck: d * a * -0.02, head: d * a * 0.015,
      r_arm: d * a * 0.05, l_arm: d * a * -0.05,
      r_forearm: d * a * 0.03, l_forearm: d * a * -0.03,
      r_thigh: d * a * -0.025, l_thigh: d * a * 0.025,
      r_shin: d * a * 0.01, l_shin: d * a * -0.01,
    };
  },

  squat: (t) => {
    const p = (Math.sin(t * 0.6) + 1) / 2;
    const e = p * p * (3 - 2 * p);
    return {
      ...Z,
      root: e * 0.04, spine: e * -0.03, neck: e * -0.02,
      r_arm: e * 0.15, l_arm: e * 0.15,
      r_forearm: e * 0.2, l_forearm: e * 0.2,
      r_thigh: e * 0.25, r_shin: e * -0.45, r_foot: e * 0.2,
      l_thigh: e * 0.25, l_shin: e * -0.45, l_foot: e * 0.2,
    };
  },

  march: (t) => {
    const s = Math.sin(t * 2.5);
    const pos = Math.max(0, s);
    const neg = Math.max(0, -s);
    return {
      ...Z,
      root: Math.sin(t * 5) * 0.01, spine: Math.cos(t * 2.5) * 0.015,
      neck: Math.cos(t * 2.5) * 0.01, head: s * 0.005,
      r_arm: s * 0.25, r_forearm: pos * 0.2,
      l_arm: -s * 0.25, l_forearm: neg * 0.2,
      r_thigh: -s * 0.35, r_shin: neg * 0.3,
      l_thigh: s * 0.35, l_shin: pos * 0.3,
    };
  },
};

export const DEFAULT_PRESET = "idle";
