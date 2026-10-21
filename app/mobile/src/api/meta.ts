import { useEffect, useState } from "react";
import { apiClient } from "./client";
import { cached, cacheKey } from "./cache";
import { LayeringMeta } from "../types/layering";

let memo: LayeringMeta | null = null;

// Static table; cached in AsyncStorage and in memory for the session.
export async function getLayering(): Promise<LayeringMeta> {
  if (!memo) {
    memo = await cached(cacheKey("meta:layering"), () =>
      apiClient.get<LayeringMeta>("/meta/layering")
    );
  }
  return memo;
}

export function useLayering(): LayeringMeta | null {
  const [meta, setMeta] = useState<LayeringMeta | null>(memo);
  useEffect(() => {
    if (!meta) getLayering().then(setMeta).catch((e) => console.log("layering meta", e));
  }, [meta]);
  return meta;
}

// "dress_shoes" -> "Dress shoes" when the table isn't loaded yet
export const subcategoryLabel = (meta: LayeringMeta | null, sub?: string | null) =>
  sub ? meta?.subcategories[sub]?.label ?? sub.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()) : "";
