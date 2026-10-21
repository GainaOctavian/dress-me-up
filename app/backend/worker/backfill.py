"""Re-queue every processed photo for a partial pass; safe to re-run.
    docker compose -f app/infra/compose/compose.yaml exec worker python -m app.backend.worker.backfill [suggest|fit]
- suggest (default): CLIP suggestions, fills empty item fields only (plan 11)
- fit: garment anchors for the outfit editor (plan 13)
- reprocess: full pipeline again (new outputs, e.g. the glow-free cutout);
  item fields are still only filled when empty
"""
import sys

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.db.db import get_db

mode = sys.argv[1] if len(sys.argv) > 1 else "suggest"
assert mode in ("suggest", "fit", "reprocess"), mode
assets = get_db().get_collection(models.ImageAsset.COLLECTION_NAME)
n = 0
for a in assets.find({"status": models.ImageAssetStatus.PROCESSED}, {"_id": 1}):
    if mode == "reprocess":
        # handle() only picks up ready/failed/processing assets
        assets.update_one({"_id": a["_id"]}, {"$set": {"status": models.ImageAssetStatus.READY}})
        queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": a["_id"]})
    else:
        queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": a["_id"], f"{mode}_only": True})
    n += 1
print(f"queued {n} assets ({mode})")
