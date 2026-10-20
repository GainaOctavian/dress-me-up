import { apiClient } from "./client";
import { cached, cacheKey, readCache, writeCache } from "./cache";
import {
  Wardrobe,
  WardrobeListResponse,
  WardrobeResponse,
  WardrobeRole,
} from "../types/wardrobe";

type CacheOptions = { forceRefresh?: boolean };

const ALL_KEY = cacheKey("wardrobes:all");
const OWNED_KEY = cacheKey("wardrobes:owned");
const wardrobeKey = (id: string) => cacheKey(`wardrobe:${id}`);

async function fetchList(path: string, token: string): Promise<Wardrobe[]> {
  const { wardrobes: raw, item_counts = {} } =
    await apiClient.getWithAuth<WardrobeListResponse>(path, token);
  const wardrobes = raw.map((w) => ({ ...w, item_count: item_counts[w._id] }));
  // warm the per-wardrobe cache so opening a detail screen needs no GET
  wardrobes.forEach((w) => writeCache(wardrobeKey(w._id), w));
  return wardrobes;
}

// Apply a change to both cached lists (no-op for a list not cached yet).
async function patchLists(patch: (list: Wardrobe[]) => Wardrobe[]) {
  for (const key of [ALL_KEY, OWNED_KEY]) {
    const list = await readCache<Wardrobe[]>(key);
    if (list) writeCache(key, patch(list));
  }
}

// Keep every cached copy of a wardrobe in sync after a mutation,
// so the list screen shows the edit without a refetch. Merging keeps
// client-only fields (item_count) that API responses don't carry.
export async function storeWardrobe(w: Wardrobe): Promise<Wardrobe> {
  writeCache(wardrobeKey(w._id), w);
  await patchLists((list) =>
    list.map((x) => (x._id === w._id ? { ...x, ...w } : x))
  );
  return w;
}

export const getAllRelatedWardrobes = (token: string, options?: CacheOptions) =>
  cached(
    ALL_KEY,
    () => fetchList("/wardrobes/user/me/roles/", token),
    options?.forceRefresh
  );

export const getOwnedWardrobes = (token: string, options?: CacheOptions) =>
  cached(
    OWNED_KEY,
    () => fetchList("/wardrobes/user/me", token),
    options?.forceRefresh
  );

export const getWardrobeById = (
  token: string,
  wardrobeId: string,
  options?: CacheOptions
) =>
  cached(
    wardrobeKey(wardrobeId),
    async () =>
      (
        await apiClient.getWithAuth<WardrobeResponse>(
          `/wardrobes/${wardrobeId}`,
          token
        )
      ).wardrobe,
    options?.forceRefresh
  );

export interface UpdateWardrobePayload {
  name?: string;
  description?: string | null;
}

export async function updateWardrobe(
  token: string,
  wardrobeId: string,
  payload: UpdateWardrobePayload
): Promise<Wardrobe> {
  const { wardrobe } = await apiClient.putWithAuth<WardrobeResponse>(
    `/wardrobes/${wardrobeId}`,
    token,
    payload
  );
  return storeWardrobe(wardrobe);
}

export async function addUserByEmailToWardrobe(
  token: string,
  wardrobeId: string,
  email: string,
  role: WardrobeRole
): Promise<Wardrobe> {
  const { wardrobe } = await apiClient.putWithAuth<WardrobeResponse>(
    `/wardrobes/${wardrobeId}/roles/by-email/`,
    token,
    { email, role }
  );
  return storeWardrobe(wardrobe);
}

export async function removeUserFromWardrobe(
  token: string,
  wardrobeId: string,
  userId: string
): Promise<Wardrobe> {
  const { wardrobe } = await apiClient.deleteWithAuth<WardrobeResponse>(
    `/wardrobes/${wardrobeId}/roles/${userId}`,
    token
  );
  return storeWardrobe(wardrobe);
}

// The creator becomes OWNER, so the new wardrobe belongs in both lists.
export async function createWardrobe(
  token: string,
  payload: { name: string; description?: string | null }
): Promise<Wardrobe> {
  const { wardrobe } = await apiClient.postJsonWithAuth<WardrobeResponse>(
    "/wardrobes/",
    token,
    payload
  );
  writeCache(wardrobeKey(wardrobe._id), wardrobe);
  await patchLists((list) => [{ ...wardrobe, item_count: 0 }, ...list]);
  return wardrobe;
}

export async function deleteWardrobe(
  token: string,
  wardrobeId: string
): Promise<void> {
  await apiClient.deleteWithAuth<void>(`/wardrobes/${wardrobeId}`, token);
  await patchLists((list) => list.filter((w) => w._id !== wardrobeId));
}

// Add a member by id or change an existing member's role (owner only).
export async function setMemberRole(
  token: string,
  wardrobeId: string,
  userId: string,
  role: WardrobeRole
): Promise<Wardrobe> {
  const { wardrobe } = await apiClient.putWithAuth<WardrobeResponse>(
    `/wardrobes/${wardrobeId}/roles/`,
    token,
    { user_id: userId, role }
  );
  return storeWardrobe(wardrobe);
}

export async function leaveWardrobe(
  token: string,
  wardrobeId: string
): Promise<void> {
  await apiClient.postJsonWithAuth<void>(`/wardrobes/${wardrobeId}/leave`, token);
  await patchLists((list) => list.filter((w) => w._id !== wardrobeId));
}
