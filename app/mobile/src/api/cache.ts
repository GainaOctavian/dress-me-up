import AsyncStorage from "@react-native-async-storage/async-storage";

// All API cache keys share this prefix so logout can wipe them in one go.
const PREFIX = "cache:";
// Bump when cached API data changes shape or gets backfilled server-side
// (v2: items gained `subcategory`). Old entries are ignored, then cleared.
const VERSION = "v3";

export const cacheKey = (key: string) => `${PREFIX}${VERSION}:${key}`;

// Read-through AsyncStorage cache. No TTL on purpose: screens pass
// forceRefresh (pull-to-refresh) when they want fresh data.
export async function cached<T>(
  key: string,
  fetcher: () => Promise<T>,
  forceRefresh = false
): Promise<T> {
  if (!forceRefresh) {
    try {
      const hit = await AsyncStorage.getItem(key);
      if (hit) return JSON.parse(hit) as T;
    } catch (e) {
      console.log("Cache read failed", key, e);
    }
  }
  const value = await fetcher();
  void AsyncStorage.setItem(key, JSON.stringify(value));
  return value;
}

export async function readCache<T>(key: string): Promise<T | null> {
  try {
    const hit = await AsyncStorage.getItem(key);
    return hit ? (JSON.parse(hit) as T) : null;
  } catch {
    return null;
  }
}

export function writeCache(key: string, value: unknown) {
  void AsyncStorage.setItem(key, JSON.stringify(value));
}

export function dropCache(key: string) {
  void AsyncStorage.removeItem(key);
}

// Drop entries written by older cache versions (called once on startup).
export async function purgeOldCache() {
  const keys = await AsyncStorage.getAllKeys();
  const current = `${PREFIX}${VERSION}:`;
  await AsyncStorage.multiRemove(
    keys.filter((k) => k.startsWith(PREFIX) && !k.startsWith(current))
  );
}

export async function clearCache() {
  const keys = await AsyncStorage.getAllKeys();
  await AsyncStorage.multiRemove(keys.filter((k) => k.startsWith(PREFIX)));
}
