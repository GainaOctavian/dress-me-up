"""Upload the rendered mannequins and upsert their `bodies` docs (plan 12).

Runs in the worker image (it has app.backend.common, S3 and Mongo env):

    docker compose -f app/infra/compose/compose.yaml run --rm \
        -v <repo>/app/infra/body-assets:/assets worker python /assets/seed.py

Idempotent: same ids, docs replaced. Image keys carry a content hash, so a
re-render gets a new key (clients cache images by key) and the old object
is deleted.
"""
import hashlib
import json
import sys
from pathlib import Path

from app.backend.common.db import models
from app.backend.common.db.db import get_db
from app.backend.common.storage import s3

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "out")


def main():
    bodies = get_db().get_collection(models.Body.COLLECTION_NAME)
    for body_id, spec in json.loads((OUT / "bodies.json").read_text()).items():
        old = bodies.find_one({"_id": body_id}) or {"poses": {}}
        poses = {}
        for pose_id, pose in spec["poses"].items():
            png = (OUT / body_id / f"{pose_id}.png").read_bytes()
            key = f"bodies/{body_id}/{pose_id}-{hashlib.sha256(png).hexdigest()[:10]}.png"
            s3.put_bytes(key, png, "image/png")
            old_key = old["poses"].get(pose_id, {}).get("image_key")
            if old_key and old_key != key:
                s3.delete(old_key)
            poses[pose_id] = models.BodyPose(image_key=key, **pose)
        body = models.Body(
            id=body_id, gender=spec["gender"], poses=poses,
            measurements_cm=spec["measurements_cm"],
        )
        bodies.replace_one({"_id": body_id}, body.model_dump(by_alias=True), upsert=True)
        print("seeded", body_id, list(poses))


if __name__ == "__main__":
    main()
