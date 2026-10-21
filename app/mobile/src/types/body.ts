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
}
