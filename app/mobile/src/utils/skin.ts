// 2D skinning (plan 14): bends a placed garment onto a pose. Pure functions.
//
// Each garment gets its own "garment pose": the neutral skeleton, but with
// the arms along its sleeves and the legs along its trouser legs (worker
// anchors). Grid vertices are bound to those bones by capsule distance, and
// every bone moves rigidly to the target pose's bone. Target = neutral is
// the same path, so the sleeves land on the arms in every pose.
import { BodyPose } from "../types/body";
import { GarmentAnchors } from "../types/outfit";
import { Placement } from "./fit";

type V = [number, number];
type BoneName =
  | "torso" | "head" | "feet"
  | "upper_l" | "fore_l" | "upper_r" | "fore_r"
  | "thigh_l" | "shin_l" | "thigh_r" | "shin_r";
type Skeleton = Record<BoneName, [V, V]>;

// positions normalized to the pose image (0..1), textures normalized to the
// garment image; triangles drawn in index order (limbs last, over the torso)
export type Mesh = { positions: V[]; textures: V[]; indices: number[]; bbox: [number, number, number, number] };

const LIMB_BIAS = 0.5;

const sub = (a: V, b: V): V => [a[0] - b[0], a[1] - b[1]];
const add = (a: V, b: V): V => [a[0] + b[0], a[1] + b[1]];
const mul = (a: V, k: number): V => [a[0] * k, a[1] * k];
const len = (a: V) => Math.hypot(a[0], a[1]);
const rotate = (a: V, t: number): V => [a[0] * Math.cos(t) - a[1] * Math.sin(t), a[0] * Math.sin(t) + a[1] * Math.cos(t)];
const angle = (a: V) => Math.atan2(a[1], a[0]);

function segmentDistance(p: V, a: V, b: V) {
  const ab = sub(b, a);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / (ab[0] ** 2 + ab[1] ** 2 || 1)));
  return len(sub(p, add(a, mul(ab, t))));
}

function skeleton(pose: BodyPose): Skeleton {
  const [W, H] = pose.size;
  const k = (name: string, fallback?: string): V => {
    const p = pose.keypoints[name] ?? pose.keypoints[fallback ?? ""] ?? [0.5, 0.5];
    return [p[0] * W, p[1] * H];
  };
  const hipL = k("hip_joint_l", "hip_l");
  const hipR = k("hip_joint_r", "hip_r");
  return {
    torso: [k("neck"), mul(add(hipL, hipR), 0.5)],
    head: [k("neck"), k("head_top")],
    feet: [k("ankle_r"), k("ankle_l")],
    upper_l: [k("shoulder_l"), k("elbow_l")], fore_l: [k("elbow_l"), k("wrist_l")],
    upper_r: [k("shoulder_r"), k("elbow_r")], fore_r: [k("elbow_r"), k("wrist_r")],
    thigh_l: [hipL, k("knee_l")], shin_l: [k("knee_l"), k("ankle_l")],
    thigh_r: [hipR, k("knee_r")], shin_r: [k("knee_r"), k("ankle_r")],
  };
}

function bonesFor(slot: string | undefined, subcategory: string | null | undefined,
                  index: number, count: number): BoneName[] {
  switch (slot) {
    case "torso":
    case "full":
      return ["torso", "upper_l", "fore_l", "upper_r", "fore_r"];
    case "legs":
      // a skirt hangs from the waist; it shouldn't split with the legs
      return subcategory === "skirt" ? ["torso"] : ["torso", "thigh_l", "shin_l", "thigh_r", "shin_r"];
    case "head":
    case "eyes":
      return ["head"];
    case "wrist":
      return ["fore_l"];
    case "hands":
    case "bag":
      return ["fore_r"];
    case "feet":
      // a single shoe is drawn twice (left foot first); a pair spans both
      return count === 2 ? [index === 0 ? "shin_l" : "shin_r"] : ["feet"];
    default:
      return ["torso"];
  }
}

export function skinPlacement(
  p: Placement,
  fit: GarmentAnchors | null | undefined,
  slot: string | undefined,
  subcategory: string | null | undefined,
  neutral: BodyPose,
  target: BodyPose,
  index = 0,
  count = 1
): Mesh {
  const [W, H] = neutral.size;
  const center: V = [(p.left + p.width / 2) * W, (p.top + p.height / 2) * H];
  const theta = ((p.rotation ?? 0) * Math.PI) / 180;
  // garment image (u, v in 0..1) -> neutral pose px
  const toPx = (u: number, v: number): V =>
    add(center, rotate([(u - 0.5) * p.width * W, (v - 0.5) * p.height * H], theta));

  const names = bonesFor(slot, subcategory, index, count);
  const N = skeleton(neutral);
  const T = skeleton(target);
  const G: Skeleton = { ...N };

  // virtual limbs: the garment's own arms/legs, with the body's lengths
  const limb = (upper: BoneName, lower: BoneName, from: V, toward: V) => {
    const d = sub(toward, from);
    if (len(d) < 1) return;
    const dir = mul(d, 1 / len(d));
    const elbow = add(from, mul(dir, len(sub(N[upper][1], N[upper][0]))));
    G[upper] = [from, elbow];
    G[lower] = [elbow, add(elbow, mul(dir, len(sub(N[lower][1], N[lower][0]))))];
  };
  if (fit && names.includes("upper_l")) {
    for (const s of ["l", "r"] as const) {
      const sh = fit[`shoulder_${s}`];
      const sl = fit[`sleeve_${s}`];
      if (sh && sl) {
        // the sleeve leaves the garment at its shoulder; the body's shoulder
        // is where that sleeve attaches
        limb(`upper_${s}`, `fore_${s}`, N[`upper_${s}`][0],
             add(N[`upper_${s}`][0], sub(toPx(...sl), toPx(...sh))));
      }
    }
  }
  if (fit && names.includes("thigh_l")) {
    limb("thigh_l", "shin_l", N.thigh_l[0], toPx(...fit.hem_l));
    limb("thigh_r", "shin_r", N.thigh_r[0], toPx(...fit.hem_r));
  }

  const bh = len(sub(N.torso[1], N.torso[0])) * 2.6; // ~ body height in px
  const chest = (neutral.keypoints.chest_l?.[0] ?? 0.6) - (neutral.keypoints.chest_r?.[0] ?? 0.4);
  const hips = (neutral.keypoints.hip_l?.[0] ?? 0.6) - (neutral.keypoints.hip_r?.[0] ?? 0.4);
  const radius = (b: BoneName) =>
    b === "torso" ? ((slot === "legs" ? hips : chest) * W) / 2
    : b.startsWith("upper") || b.startsWith("fore") ? bh * 0.035
    : b.startsWith("thigh") || b.startsWith("shin") ? bh * 0.06
    : bh * 0.05;
  const eps = bh * 0.015;

  const moves = names.map((b) => {
    const [ga, gb] = G[b];
    const [ta, tb] = T[b];
    const t = angle(sub(tb, ta)) - angle(sub(gb, ga));
    return (v: V) => add(rotate(sub(v, ga), t), ta);
  });

  const column = names.includes("upper_l") && fit?.shoulder_l && fit?.shoulder_r
    ? [fit.shoulder_r[0], fit.shoulder_l[0]] : null;
  // garment u -> which sleeve side it's on, and how far out (0..1)
  const sleeveSide = (u: number): { side: "_l" | "_r"; t: number } => {
    if (!column) return { side: "_l", t: 1 };
    const ramp = (column[1] - column[0]) * 0.12;
    return u > column[1]
      ? { side: "_l", t: Math.min(1, (u - column[1]) / ramp) }
      : { side: "_r", t: u < column[0] ? Math.min(1, (column[0] - u) / ramp) : 0 };
  };

  const n = names.length > 1 ? 16 : 1;
  const positions: V[] = [];
  const textures: V[] = [];
  const limbWeight: number[] = [];
  for (let j = 0; j <= n; j++) {
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      const v = j / n;
      const p0 = toPx(u, v);
      // the torso wins where it's ambiguous (shoulder tops stay covered);
      // tops with a known torso column: inside it only the torso moves the
      // cloth, outside it the sleeve of that side (ramped, so nothing tears)
      const side = sleeveSide(u);
      const w = names.map((b, bi) => {
        let k = bi > 0 && names[0] === "torso" ? LIMB_BIAS : 1;
        if (column && bi > 0) k *= b.endsWith(side.side) ? side.t : 0;
        return k / (Math.max(0, segmentDistance(p0, ...G[b]) - radius(b)) + eps) ** 2;
      });
      const total = w.reduce((s, x) => s + x, 0);
      let out: V = [0, 0];
      names.forEach((_, bi) => (out = add(out, mul(moves[bi](p0), w[bi] / total))));
      positions.push([out[0] / W, out[1] / H]);
      textures.push([p.flip ? 1 - u : u, v]);
      limbWeight.push(names[0] === "torso" ? 1 - w[0] / total : 0);
    }
  }

  const cells: { tris: number[]; key: number }[] = [];
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const a = j * (n + 1) + i;
      const quad = [a, a + 1, a + n + 1, a + n + 2];
      cells.push({
        tris: [a, a + 1, a + n + 1, a + 1, a + n + 2, a + n + 1],
        key: quad.reduce((s, q) => s + limbWeight[q], 0),
      });
    }
  }
  cells.sort((x, y) => x.key - y.key);

  const xs = positions.map((q) => q[0]);
  const ys = positions.map((q) => q[1]);
  return {
    positions,
    textures,
    indices: cells.flatMap((c) => c.tris),
    bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
  };
}
