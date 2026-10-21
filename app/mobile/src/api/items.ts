import { apiClient } from "./client";
import { cached, cacheKey, dropCache, readCache, writeCache } from "./cache";
import {
  Item,
  ItemListResponse,
  ItemPayload,
  ItemResponse,
} from "../types/item";

// The backend pulls removed/deleted items out of outfits, so cached
// outfits would still show them: drop that cache when items go away.
const OUTFITS_KEY = cacheKey("outfits:mine");

const wardrobeItemsKey = (wardrobeId: string) =>
  cacheKey(`wardrobe-items:${wardrobeId}`);

// Apply a change to a wardrobe's cached item list (no-op if not cached yet).
async function patchWardrobeItems(
  wardrobeId: string,
  patch: (items: Item[]) => Item[]
) {
  const key = wardrobeItemsKey(wardrobeId);
  const items = await readCache<Item[]>(key);
  if (items) writeCache(key, patch(items));
}

const upsert = (item: Item) => (items: Item[]) =>
  items.some((i) => i._id === item._id)
    ? items.map((i) => (i._id === item._id ? item : i))
    : [item, ...items];

const without = (itemId: string) => (items: Item[]) =>
  items.filter((i) => i._id !== itemId);

export const getWardrobeItems = (
  token: string,
  wardrobeId: string,
  options?: { forceRefresh?: boolean }
) =>
  cached(
    wardrobeItemsKey(wardrobeId),
    async () =>
      (
        await apiClient.getWithAuth<ItemListResponse>(
          `/wardrobes/${wardrobeId}/items`,
          token
        )
      ).items,
    options?.forceRefresh
  );

export async function createItem(
  token: string,
  wardrobeId: string,
  payload: ItemPayload
): Promise<Item> {
  const { item } = await apiClient.postJsonWithAuth<ItemResponse>(
    "/items/",
    token,
    { ...payload, wardrobe_ids: [wardrobeId] }
  );
  await patchWardrobeItems(wardrobeId, upsert(item));
  return item;
}

export async function updateItem(
  token: string,
  itemId: string,
  payload: Partial<ItemPayload>
): Promise<Item> {
  const { item } = await apiClient.putWithAuth<ItemResponse>(
    `/items/${itemId}`,
    token,
    payload
  );
  for (const wardrobeId of item.wardrobe_ids) {
    await patchWardrobeItems(wardrobeId, upsert(item));
  }
  return item;
}

export async function removeItemFromWardrobe(
  token: string,
  wardrobeId: string,
  itemId: string
): Promise<Item> {
  const { item } = await apiClient.deleteWithAuth<ItemResponse>(
    `/wardrobes/${wardrobeId}/items/${itemId}`,
    token
  );
  await patchWardrobeItems(wardrobeId, without(itemId));
  dropCache(OUTFITS_KEY);
  return item;
}

export async function deleteItem(token: string, item: Item): Promise<void> {
  await apiClient.deleteWithAuth<void>(`/items/${item._id}`, token);
  for (const wardrobeId of item.wardrobe_ids) {
    await patchWardrobeItems(wardrobeId, without(item._id));
  }
  dropCache(OUTFITS_KEY);
}

// Always fresh: only used by the "Add from my items" picker.
export async function getMyItems(token: string): Promise<Item[]> {
  return (await apiClient.getWithAuth<ItemListResponse>("/items/me", token))
    .items;
}

export async function addItemToWardrobe(
  token: string,
  wardrobeId: string,
  itemId: string
): Promise<Item> {
  const { item } = await apiClient.putWithAuth<ItemResponse>(
    `/wardrobes/${wardrobeId}/items/${itemId}`,
    token
  );
  await patchWardrobeItems(wardrobeId, upsert(item));
  return item;
}
