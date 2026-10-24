import { useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiClient } from "./client";
import { cached, cacheKey } from "./cache";
import { Body, SaveMyBody } from "../types/body";
import { useAuth } from "../hooks/useAuth";

// Pose images are immutable; URLs are presigned for 24h, so the list is
// cached and refetched with forceRefresh when an image fails to load.
export const getBodies = (token: string, options?: { forceRefresh?: boolean }) =>
  cached(
    cacheKey("bodies"),
    async () => (await apiClient.getWithAuth<{ bodies: Body[] }>("/bodies/", token)).bodies,
    options?.forceRefresh
  );

// Bodies for canvases; `refresh()` refetches (expired or re-seeded image)
export function useBodies(): { bodies: Body[] | null; refresh: () => void } {
  const { token } = useAuth();
  const [bodies, setBodies] = useState<Body[] | null>(null);
  const load = (forceRefresh = false) => {
    if (token) getBodies(token, { forceRefresh }).then(setBodies).catch((e) => console.log("bodies", e));
  };
  useEffect(() => load(), [token]);
  return { bodies, refresh: () => load(true) };
}

// Plan 16a: my body from my measurements. The server builds it in ~1.5 min
// (status "building"); the result refreshes the cached list.
export async function saveMyBody(token: string, payload: SaveMyBody): Promise<Body> {
  const { body } = await apiClient.postJsonWithAuth<{ body: Body }>("/bodies/me", token, payload);
  await getBodies(token, { forceRefresh: true });
  return body;
}

export async function deleteMyBody(token: string): Promise<void> {
  await apiClient.deleteWithAuth<void>("/bodies/me", token);
  await getBodies(token, { forceRefresh: true });
}

export const myBody = (bodies: Body[] | null) => bodies?.find((b) => b.kind === "user") ?? null;

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
