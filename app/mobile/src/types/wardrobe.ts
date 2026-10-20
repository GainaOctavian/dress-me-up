export type WardrobeRole = "owner" | "editor" | "viewer";

export interface Wardrobe {
  _id: string;
  user_id: string;
  name: string;
  description?: string | null;
  roles: Record<string, WardrobeRole>;
  created_at: string;
}

export interface WardrobeListResponse {
  wardrobes: Wardrobe[];
}

export interface WardrobeResponse {
  wardrobe: Wardrobe;
}
