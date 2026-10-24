// GET /bodies (plan 12). Keypoints are normalized 0..1 in the pose image
// (x right, y down); left/right are the body's own left/right.
export type Keypoints = Record<string, [number, number]>;

export interface BodyPose {
  image_key: string;
  image_url: string;
  size: [number, number];
  keypoints: Keypoints;
}

export interface Body {
  id: string;
  kind: "mannequin" | "user";
  gender: "male" | "female";
  format: number;
  poses: Record<string, BodyPose>;
  measurements_cm: Record<string, number>;
  // the user's own body (plan 16): what they typed and the build's state
  input_cm?: Partial<Record<MeasurementKey, number>>;
  status?: "building" | "ready" | "failed";
  error?: string | null;
}

export type MeasurementKey = "height_cm" | "weight_kg" | "chest_cm" | "waist_cm" | "hips_cm";

export interface SaveMyBody extends Partial<Record<MeasurementKey, number>> {
  gender: "male" | "female";
  height_cm: number;
  weight_kg: number;
}
