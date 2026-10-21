// Dressing items on a body (plan 13). Pure functions: the canvas, the
// editor and (later) a server-side preview all place garments the same way.
//
// Coordinates: body keypoints and garment anchors are normalized 0..1 in
// their own images; everything here works in body-image pixels and returns
// a rect normalized to the body image. _l/_r = the wearer's sides.
import { BodyPose } from "../types/body";
import { FitAdjust, GarmentAnchors, OutfitItem, OutfitItemRef } from "../types/outfit";
import { LayeringMeta } from "../types/layering";

export type Rect = { left: number; top: number; width: number; height: number };
export type Placement = Rect & { flip?: boolean; rotation?: number };
type P = [number, number];

// ---------------------------------------------------------------- draw order
// Port of common/layering.py z_of/draw_order; the bands come from the meta.

export function zOf(item: OutfitItem, sub: string | null | undefined, meta: LayeringMeta): number {
  const info = sub ? meta.subcategories[sub] : undefined;
  if (!info || info.band == null) return 50; // unknown type: middle of the stack
  if (info.slot === "torso" && ["base", "mid", "insulation"].includes(info.role)) {
    const tucked = item.tucked ?? info.tucked_default;
    if (tucked && info.role !== "base") return meta.tucked_band;
  }
  if (info.slot === "legs" && info.role === "mid" && item.into_shoes) return meta.into_shoes_band;
  return info.band;
}

export function drawOrder(
  items: OutfitItem[],
  refs: Record<string, OutfitItemRef>,
  meta: LayeringMeta
): OutfitItem[] {
  const key = (oi: OutfitItem) => zOf(oi, refs[oi.item_id]?.subcategory, meta);
  return items
    .map((oi, i) => ({ oi, i }))
    .sort((a, b) => key(a.oi) - key(b.oi) || (a.oi.layer_offset ?? 0) - (b.oi.layer_offset ?? 0) || a.i - b.i)
    .map(({ oi }) => oi);
}

// ---------------------------------------------------------------- fit

// A flat garment is about half its circumference wide; worn and seen from the
// front it's ~1/1.38 of that (measured on the mannequins' chest and waist).
const FLAT_TO_WORN = 1.38;
// a worn top is a bit wider than the chest it covers
const EASE = 1.1;
// Width padding per layer role, so stacked layers read as layers.
const ROLE_PAD: Record<string, number> = {
  base: 1.0, mid: 1.03, insulation: 1.07, outer: 1.12, over: 1.18,
};
// Where the hem lands: 0 waist, 1 hip, 2 crotch, 3 knee, 4 ankle (piecewise).
const LENGTH: Record<string, number> = {
  tank_top: 1.2, undershirt: 1.2, t_shirt: 1.5, polo: 1.5, blouse: 1.5,
  shirt: 1.8, sweater: 1.4, sweatshirt: 1.4, hoodie: 1.5, cardigan: 1.5,
  blazer: 1.8, jacket: 1.6, denim_jacket: 1.4, leather_jacket: 1.4, bomber: 1.2,
  gilet: 1.4, puffer: 1.6, coat: 3.2, parka: 2.6, trench: 3.3,
  dress: 2.9, jumpsuit: 4.0,
};
const FULL_LENGTH = new Set(["jeans", "trousers", "chinos", "sweatpants", "leggings", "tights"]);

// photos without anchors (no processed image yet): treat the bbox as the garment
const BBOX_ANCHORS: GarmentAnchors = {
  format: 1, collar: [0.5, 0], top_l: [1, 0], top_r: [0, 0], hem_l: [0.75, 1], hem_r: [0.25, 1], parts: 1,
};

const mid = (a: P, b: P): P => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// Usually one rect; a single shoe is drawn on both feet (mirrored on the right).
export function fitRects(
  ref: OutfitItemRef,
  sub: { slot: string; role: string } | undefined,
  pose: BodyPose
): Placement[] {
  const one = fitRect(ref, sub, pose);
  if (sub?.slot !== "feet" || (ref.fit?.parts ?? 1) > 1) return [one];
  const [W, H] = pose.size;
  const height = (pose.keypoints.heel_l[1] - pose.keypoints.head_top[1]) * H;
  // a side-view shoe is ~16% of body height long
  const w = (height * 0.16) / W;
  const [gw, gh] = ref.image_size ?? [1000, 1000];
  const h = ((w * W) * (gh / gw)) / H;
  const floor = pose.keypoints.heel_l[1] + 0.006;
  return [
    { left: pose.keypoints.heel_l[0] - w * 0.3, top: floor - h, width: w, height: h },
    { left: pose.keypoints.heel_r[0] - w * 0.7, top: floor - h, width: w, height: h, flip: true },
  ];
}

function fitRect(
  ref: OutfitItemRef,
  sub: { slot: string; role: string } | undefined,
  pose: BodyPose
): Rect {
  const [W, H] = pose.size;
  const k = (name: string): P => {
    const p = pose.keypoints[name] ?? [0.5, 0.5];
    return [p[0] * W, p[1] * H];
  };
  const [gw, gh] = ref.image_size ?? [1000, 1000];
  const a = ref.fit ?? BBOX_ANCHORS;
  const g = (p: P): P => [p[0] * gw, p[1] * gh];

  const neck = k("neck");
  const eyes = mid(k("eye_l"), k("eye_r"));
  const eyeGap = k("eye_l")[0] - k("eye_r")[0];
  const levelY = (t: number) => {
    const ys = [k("waist")[1], mid(k("hip_l"), k("hip_r"))[1], k("crotch")[1],
                mid(k("knee_l"), k("knee_r"))[1], mid(k("ankle_l"), k("ankle_r"))[1]];
    const i = Math.min(Math.floor(t), 3);
    return lerp(ys[i], ys[i + 1], t - i);
  };
  const width = (l: string, r: string) => k(l)[0] - k(r)[0];
  const pad = ROLE_PAD[sub?.role ?? "mid"] ?? 1.03;
  const name = ref.subcategory ?? "";

  // garment scaled by (sx, sy) with garment point `from` landing on body point `to`
  const place = (sx: number, sy: number, from: P, to: P): Rect => ({
    left: (to[0] - from[0] * sx) / W,
    top: (to[1] - from[1] * sy) / H,
    width: (gw * sx) / W,
    height: (gh * sy) / H,
  });
  // box of given body-px size, image contained inside (accessories, shoes)
  const box = (cx: number, top: number, w: number, h: number): Rect => ({
    left: (cx - w / 2) / W, top: top / H, width: w / W, height: h / H,
  });

  switch (sub?.slot) {
    case "torso":
    case "full": {
      // length decides the scale: sleeves make widths unreliable on photos
      const collar = g(a.collar);
      const hemY = Math.max(g(a.hem_l)[1], g(a.hem_r)[1]);
      const top = neck[1] - 0.45 * (neck[1] - eyes[1]); // back of the collar sits above the neck base
      const sy = (levelY(LENGTH[name] ?? 1.6) - top) / Math.max(1, hemY - collar[1]);
      // width: the torso column between the sleeves (worker, plan 14) onto the
      // chest with a little ease; without sleeves found, from the length
      const torso = a.shoulder_l && a.shoulder_r ? (a.shoulder_l[0] - a.shoulder_r[0]) * gw : 0;
      const sx = torso > 0
        ? (width("chest_l", "chest_r") * pad * EASE) / torso
        : (sy / FLAT_TO_WORN) * pad;
      return place(sx, sy, collar, [neck[0], top]);
    }
    case "legs": {
      // waistband between natural waist and hips, width from the body outline
      const t = 0.35;
      const y = lerp(k("waist")[1], mid(k("hip_l"), k("hip_r"))[1], t);
      const target = lerp(width("waist_l", "waist_r"), width("hip_l", "hip_r"), t);
      const band = Math.max(1, g(a.top_l)[0] - g(a.top_r)[0]);
      const sx = (target / band) * pad;
      const topY = g(a.top_l)[1];
      const hemY = Math.max(g(a.hem_l)[1], g(a.hem_r)[1]);
      const ankle = mid(k("ankle_l"), k("ankle_r"))[1];
      const floor = k("heel_l")[1];
      const sy = FULL_LENGTH.has(name)
        ? (lerp(ankle, floor, 0.5) - y) / Math.max(1, hemY - topY)
        : (sx / pad) * FLAT_TO_WORN;
      return place(sx, sy, [(g(a.top_l)[0] + g(a.top_r)[0]) / 2, topY], [k("crotch")[0], y]);
    }
    case "feet": {
      const span = width("heel_l", "heel_r");
      const floor = k("heel_l")[1];
      const h = span * 0.45;
      return box(k("crotch")[0], floor - h * 0.9, span * 1.6, h);
    }
    case "head": {
      const w = eyeGap * (name === "cap" ? 4.4 : 3.8);
      const top = k("head_top")[1] - eyeGap * 0.5;
      return box(k("head_top")[0], top, w, (eyes[1] - top) * 0.95);
    }
    case "eyes":
      return box(eyes[0], eyes[1] - eyeGap * 0.6, eyeGap * 2.6, eyeGap * 1.2);
    case "neck": {
      if (name === "tie") {
        const h = (k("waist")[1] - neck[1]) * 1.05;
        return box(neck[0], neck[1] - eyeGap * 0.2, h * 0.3, h);
      }
      const chest = width("chest_l", "chest_r");
      return box(neck[0], neck[1] - eyeGap * 0.3,
                 chest * (name === "scarf" ? 0.9 : name === "bow_tie" ? 0.3 : 0.5),
                 chest * (name === "scarf" ? 0.9 : 0.4));
    }
    case "waist": {
      // belt sits on the trousers' waistband (see legs)
      const y = lerp(k("waist")[1], mid(k("hip_l"), k("hip_r"))[1], 0.35);
      const w = lerp(width("waist_l", "waist_r"), width("hip_l", "hip_r"), 0.35) * 1.1;
      return box(k("crotch")[0], y - eyeGap * 0.25, w, eyeGap * 0.8);
    }
    case "wrist":
      return box(k("wrist_l")[0], k("wrist_l")[1] - eyeGap * 0.6, eyeGap * 1.3, eyeGap * 1.2);
    case "hands":
      return box(k("wrist_r")[0], k("wrist_r")[1], eyeGap * 2.4, eyeGap * 3);
    case "bag": {
      const chest = width("chest_l", "chest_r");
      return box(k("wrist_r")[0] - chest * 0.2, k("wrist_r")[1] - chest * 0.4, chest * 0.8, chest * 0.9);
    }
    default:
      // no type yet: a box on the torso, so it's visible and draggable later
      return box(neck[0], neck[1], width("chest_l", "chest_r"), levelY(1.5) - neck[1]);
  }
}

// ---------------------------------------------------------------- user tweaks

// head to soles, as a fraction of the pose image height
const bodyHeight = (pose: BodyPose) => pose.keypoints.heel_l[1] - pose.keypoints.head_top[1];

// auto-fit + the user's fit_adjust (move in body heights, scale around the center)
export function placeItem(
  oi: OutfitItem,
  ref: OutfitItemRef,
  sub: { slot: string; role: string } | undefined,
  pose: BodyPose
): Placement[] {
  const a = oi.fit_adjust;
  const placements = fitRects(ref, sub, pose);
  if (!a) return placements;
  const [W, H] = pose.size;
  const bh = bodyHeight(pose);
  return placements.map((p) => {
    const cx = p.left + p.width / 2 + (a.dx * bh * H) / W;
    const cy = p.top + p.height / 2 + a.dy * bh;
    const w = p.width * a.scale;
    const h = p.height * a.scale;
    return { ...p, left: cx - w / 2, top: cy - h / 2, width: w, height: h, rotation: a.rotation };
  });
}

// a drag of (px, py) screen pixels on a canvas `canvasWidth` px wide -> body heights
export function dragToAdjust(base: FitAdjust | null | undefined, px: number, py: number,
                             canvasWidth: number, pose: BodyPose): FitAdjust {
  const [W, H] = pose.size;
  const unit = W / (canvasWidth * H * bodyHeight(pose));
  const a = base ?? NO_ADJUST;
  return { ...a, dx: a.dx + px * unit, dy: a.dy + py * unit };
}

export const NO_ADJUST: FitAdjust = { dx: 0, dy: 0, scale: 1, rotation: 0 };

// ---------------------------------------------------------------- warnings
// Port of common/layering.py warnings(): soft checks, never blocking.

export function outfitWarnings(subs: (string | null | undefined)[], meta: LayeringMeta): string[] {
  const infos = subs.flatMap((s) => (s && meta.subcategories[s] ? [meta.subcategories[s]] : []));
  const count = (slot: string, role?: string) =>
    infos.filter((i) => i.slot === slot && (!role || i.role === role)).length;
  const out: string[] = [];
  if (count("full") && count("legs", "mid")) out.push("A dress with trousers or a skirt");
  if (count("torso", "over") > 1) out.push("More than one coat");
  if (count("feet", "mid") > 1) out.push("More than one pair of shoes");
  if (count("legs", "mid") > 1) out.push("More than one pair of trousers/shorts/skirt");
  if (count("head") > 1) out.push("More than one hat");
  return out;
}
