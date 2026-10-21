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
  z_index: number;
  transform: Transform;
  visible: boolean;
  opacity: number;
}

export interface OutfitItemRef {
  name: string;
  categories: ItemCategory[];
  image_url?: string | null;
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
}

export interface OutfitPayload {
  name: string;
  wardrobe_id?: string | null;
  items: OutfitItem[];
}

export interface OutfitResponse {
  outfit: Outfit;
}

export interface OutfitListResponse {
  outfits: Outfit[];
}
