import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiClient } from "./client";
import { cached, cacheKey } from "./cache";
import { Body } from "../types/body";

// Pose images are immutable; URLs are presigned for 24h, so the list is
// cached and refetched with forceRefresh when an image fails to load.
export const getBodies = (token: string, options?: { forceRefresh?: boolean }) =>
  cached(
    cacheKey("bodies"),
    async () => (await apiClient.getWithAuth<{ bodies: Body[] }>("/bodies/", token)).bodies,
    options?.forceRefresh
  );

// Device setting, not account data: which mannequin new outfits start on.
const DEFAULT_BODY_KEY = "settings:default_body";
export const DEFAULT_BODY_ID = "mannequin_male";

export async function getDefaultBodyId(): Promise<string> {
  try {
    return (await AsyncStorage.getItem(DEFAULT_BODY_KEY)) ?? DEFAULT_BODY_ID;
  } catch {
    return DEFAULT_BODY_ID;
  }
}

export function setDefaultBodyId(id: string) {
  void AsyncStorage.setItem(DEFAULT_BODY_KEY, id);
}
