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
  tags: string[];
  colors: string[];
  image_asset_id?: string | null;
  created_at: string;
}

export interface ItemPayload {
  name: string;
  categories: ItemCategory[];
  tags: string[];
  colors: string[];
}

export interface ItemResponse {
  item: Item;
}

export interface ItemListResponse {
  items: Item[];
}
