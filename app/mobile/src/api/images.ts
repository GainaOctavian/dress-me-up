import { Platform } from "react-native";
import { ImageManipulator, SaveFormat } from "expo-image-manipulator";
import { apiClient } from "./client";

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
    // React Native's FormData takes a {uri, name, type} file descriptor
    form.append("file", { uri: jpeg, name: "photo.jpg", type: "image/jpeg" } as any);
  }

  const res = await fetch(target.url, { method: "POST", body: form });
  if (!res.ok) {
    console.log("Upload failed", res.status, await res.text());
    throw new Error(`Upload failed (${res.status})`);
  }
  return target.image_asset_id;
}
