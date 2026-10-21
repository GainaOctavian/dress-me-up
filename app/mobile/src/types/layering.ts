import { ItemCategory } from "./item";

// Served by GET /meta/layering (backend common/layering.py is the source).
export interface SubcategoryInfo {
  category: ItemCategory;
  slot: string;
  role: string;
  label: string;
  tucked_default: boolean;
  band: number | null;
}

export interface LayeringMeta {
  format: number;
  subcategories: Record<string, SubcategoryInfo>;
  bands: Record<string, number>;
  tucked_band: number;
  into_shoes_band: number;
}
