import { apiClient } from "./client";
import { cached, cacheKey, readCache, writeCache } from "./cache";
import {
  Outfit,
  OutfitListResponse,
  OutfitPayload,
  OutfitResponse,
} from "../types/outfit";

const MINE_KEY = cacheKey("outfits:mine");

async function patchList(patch: (list: Outfit[]) => Outfit[]) {
  const list = await readCache<Outfit[]>(MINE_KEY);
  if (list) writeCache(MINE_KEY, patch(list));
}

// My outfits + every outfit of wardrobes I'm in, newest first.
export const getMyOutfits = (token: string, options?: { forceRefresh?: boolean }) =>
  cached(
    MINE_KEY,
    async () =>
      (await apiClient.getWithAuth<OutfitListResponse>("/outfits/me", token))
        .outfits,
    options?.forceRefresh
  );

export async function getOutfit(token: string, outfitId: string): Promise<Outfit> {
  const { outfit } = await apiClient.getWithAuth<OutfitResponse>(
    `/outfits/${outfitId}`,
    token
  );
  await patchList((list) => list.map((o) => (o._id === outfit._id ? outfit : o)));
  return outfit;
}

export async function createOutfit(
  token: string,
  payload: OutfitPayload
): Promise<Outfit> {
  const { outfit } = await apiClient.postJsonWithAuth<OutfitResponse>(
    "/outfits/",
    token,
    payload
  );
  await patchList((list) => [outfit, ...list]);
  return outfit;
}

export async function updateOutfit(
  token: string,
  outfitId: string,
  payload: Partial<Omit<OutfitPayload, "wardrobe_id">>
): Promise<Outfit> {
  const { outfit } = await apiClient.putWithAuth<OutfitResponse>(
    `/outfits/${outfitId}`,
    token,
    payload
  );
  await patchList((list) => list.map((o) => (o._id === outfit._id ? outfit : o)));
  return outfit;
}

export async function deleteOutfit(token: string, outfitId: string): Promise<void> {
  await apiClient.deleteWithAuth<void>(`/outfits/${outfitId}`, token);
  await patchList((list) => list.filter((o) => o._id !== outfitId));
}
