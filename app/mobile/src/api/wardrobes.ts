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
  const { wardrobes } = await apiClient.getWithAuth<WardrobeListResponse>(
    path,
    token
  );
  // warm the per-wardrobe cache so opening a detail screen needs no GET
  wardrobes.forEach((w) => writeCache(wardrobeKey(w._id), w));
  return wardrobes;
}

// Keep every cached copy of a wardrobe in sync after a mutation,
// so the list screen shows the edit without a refetch.
async function storeWardrobe(w: Wardrobe): Promise<Wardrobe> {
  writeCache(wardrobeKey(w._id), w);
  for (const key of [ALL_KEY, OWNED_KEY]) {
    const list = await readCache<Wardrobe[]>(key);
    if (list) writeCache(key, list.map((x) => (x._id === w._id ? w : x)));
  }
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
