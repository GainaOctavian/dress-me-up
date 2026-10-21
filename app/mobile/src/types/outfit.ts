import { ItemCategory } from "./item";

export interface Transform {
  // normalized to the canvas: item center in 0..1, scale vs 40% canvas width
  translate: { x: number; y: number };
  scale: { x: number; y: number };
  rotation: number; // degrees
  flip_horizontal: boolean;
  flip_vertical: boolean;
  crop?: null;
}

export interface OutfitItem {
  item_id: string;
  z_index: number; // free-canvas outfits only; dressed ones use layering
  transform: Transform;
  visible: boolean;
  opacity: number;
  // layering switches (plan 11); null = the type's default
  tucked?: boolean | null;
  into_shoes?: boolean | null;
  open?: boolean | null;
  layer_offset?: number;
  fit_adjust?: FitAdjust | null; // dressed outfits: the user's tweak on the auto-fit
}

// Offsets in body heights, so a tweak carries over to another body
export interface FitAdjust {
  dx: number;
  dy: number;
  scale: number;
  rotation: number; // degrees
}

// Worker anchors on the processed image (plan 13), normalized 0..1;
// _l/_r = the garment's own sides (_l on the image's right)
export interface GarmentAnchors {
  format: number;
  collar: [number, number];
  top_l: [number, number];
  top_r: [number, number];
  hem_l: [number, number];
  hem_r: [number, number];
  parts: number;
  // tops, when the worker found the sleeves (format 2, plan 14)
  shoulder_l?: [number, number];
  shoulder_r?: [number, number];
  sleeve_l?: [number, number];
  sleeve_r?: [number, number];
}

export interface OutfitItemRef {
  name: string;
  categories: ItemCategory[];
  image_url?: string | null;
  subcategory?: string | null;
  image_size?: [number, number] | null;
  fit?: GarmentAnchors | null;
  plain_url?: string | null; // cutout without glow, drawn on the mannequin
}

export interface Outfit {
  _id: string;
  owner_id: string;
  wardrobe_id?: string | null;
  name: string;
  items: OutfitItem[];
  shared: boolean;
  created_at: string;
  preview_url?: string | null;
  // item_id -> summary; deleted items are missing
  item_refs: Record<string, OutfitItemRef>;
  body_id?: string | null; // dressed on a mannequin (plan 13); null = free canvas
  pose_id?: string | null;
  render?: OutfitRender | null; // server 3D render (plan 19)
  render_url?: string | null; // presigned, the latest finished render
}

// queued: a newer version is rendering (render_url may still show the old one)
export interface OutfitRender {
  status: "queued" | "done" | "failed";
  version: number;
  image_key?: string | null;
  error?: string | null;
}

export interface OutfitPayload {
  name: string;
  wardrobe_id?: string | null;
  items: OutfitItem[];
  body_id?: string | null;
  pose_id?: string | null;
}

export interface OutfitResponse {
  outfit: Outfit;
}

export interface OutfitListResponse {
  outfits: Outfit[];
}
