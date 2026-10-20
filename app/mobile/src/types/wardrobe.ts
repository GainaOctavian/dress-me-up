export type WardrobeRole = "owner" | "editor" | "viewer";

export interface Wardrobe {
  _id: string;
  user_id: string;
  name: string;
  description?: string | null;
  roles: Record<string, WardrobeRole>;
  created_at: string;
  // client-side only: filled from the list response's item_counts
  item_count?: number;
}

export interface WardrobeListResponse {
  wardrobes: Wardrobe[];
  item_counts?: Record<string, number>;
}

export interface WardrobeResponse {
  wardrobe: Wardrobe;
}
