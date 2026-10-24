import { Outfit } from "./outfit";

// What we may see of another user (plan 08): email only for friends and
// wardrobe co-members; a stranger's private profile has no name either.
export interface PublicUser {
  _id: string;
  name?: string | null;
  email?: string | null;
}

export interface FriendRequest {
  _id: string;
  status: "pending" | "accepted" | "declined";
  created_at: string;
  user: PublicUser; // the other side
}

export interface FriendRequests {
  incoming: FriendRequest[];
  outgoing: FriendRequest[];
}

export interface Feed {
  outfits: Outfit[];
  owners: Record<string, PublicUser>;
}

export const displayName = (u?: PublicUser | null) => u?.name || u?.email || "Someone";
