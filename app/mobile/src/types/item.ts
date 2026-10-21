import { GarmentAnchors } from "./outfit";
export const ITEM_CATEGORIES = [
  "top",
  "bottom",
  "dress",
  "outerwear",
  "shoes",
  "accessory",
] as const;

export type ItemCategory = (typeof ITEM_CATEGORIES)[number];

export interface Item {
  _id: string;
  owner_id: string;
  name: string;
  wardrobe_ids: string[];
  categories: ItemCategory[];
  subcategory?: string | null; // precise type (t_shirt, blazer, ...), see types/layering
  tags: string[];
  colors: string[];
  image_asset_id?: string | null;
  // presigned, valid ~24h; refetch the list if it stops loading
  image_url?: string | null;
  // background removal state; "processed" = transparent cutout
  image_status?: "pending_upload" | "ready" | "processing" | "processed" | "failed" | null;
  image_size?: [number, number] | null; // [w, h] of image_url
  fit?: GarmentAnchors | null; // worker anchors (plan 13)
  plain_url?: string | null; // cutout without glow, for the mannequin
  created_at: string;
}

export interface ItemPayload {
  name: string;
  categories: ItemCategory[];
  subcategory?: string | null;
  tags: string[];
  colors: string[];
  image_asset_id?: string; // a freshly uploaded image (api/images.ts)
}

export interface ItemResponse {
  item: Item;
}

export interface ItemListResponse {
  items: Item[];
}
