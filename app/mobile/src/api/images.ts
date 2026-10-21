import { Platform } from "react-native";
import { ImageManipulator, SaveFormat } from "expo-image-manipulator";
import { File } from "expo-file-system";
import { apiClient } from "./client";
import { ItemCategory } from "../types/item";

interface UploadTarget {
  image_asset_id: string;
  url: string;
  fields: Record<string, string>;
  max_bytes: number;
}

const MAX_WIDTH = 1600;

// Phone photos are 3-12 MB; a 1600px JPEG is plenty and uploads fast.
async function shrink(uri: string, width?: number): Promise<string> {
  let ctx = ImageManipulator.manipulate(uri);
  if (!width || width > MAX_WIDTH) ctx = ctx.resize({ width: MAX_WIDTH });
  const image = await ctx.renderAsync();
  const result = await image.saveAsync({ compress: 0.8, format: SaveFormat.JPEG });
  return result.uri;
}

// Uploads a local photo straight to storage (presigned POST) and returns the
// image_asset_id to send with the item.
export async function uploadImage(
  token: string,
  uri: string,
  width?: number
): Promise<string> {
  const jpeg = await shrink(uri, width);
  const target = await apiClient.postJsonWithAuth<UploadTarget>(
    "/images/upload-url",
    token,
    { mime_type: "image/jpeg" }
  );

  const form = new FormData();
  Object.entries(target.fields).forEach(([k, v]) => form.append(k, v));
  // S3 requires the file to be the last field
  if (Platform.OS === "web") {
    form.append("file", await (await fetch(jpeg)).blob(), "photo.jpg");
  } else {
    // Expo's fetch (SDK 52+) rejects RN-style {uri, name, type} parts;
    // expo-file-system's File implements Blob, so it's sent as bytes.
    form.append("file", new File(jpeg) as unknown as Blob);
  }

  const res = await fetch(target.url, { method: "POST", body: form });
  if (!res.ok) {
    console.log("Upload failed", res.status, await res.text());
    throw new Error(`Upload failed (${res.status})`);
  }
  // starts background removal + color/tag detection on the worker
  await apiClient.postJsonWithAuth<ImageStatus>(
    `/images/${target.image_asset_id}/uploaded`,
    token
  );
  return target.image_asset_id;
}

export type ImageProcessingStatus =
  | "pending_upload"
  | "ready"
  | "processing"
  | "processed"
  | "failed";

export interface ImageStatus {
  image_asset_id: string;
  status: ImageProcessingStatus;
  image_url: string; // cutout once processed
  colors: string[];
  tags: string[];
  category: ItemCategory | null;
  subcategory: string | null;
}

export const getImageStatus = (token: string, imageAssetId: string) =>
  apiClient.getWithAuth<ImageStatus>(`/images/${imageAssetId}`, token);

// Polls until the worker is done (or gives up after `timeoutMs`).
export async function waitForProcessing(
  token: string,
  imageAssetId: string,
  timeoutMs = 90_000
): Promise<ImageStatus> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const s = await getImageStatus(token, imageAssetId);
    if (s.status === "processed" || s.status === "failed" || Date.now() > deadline) {
      return s;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
}
