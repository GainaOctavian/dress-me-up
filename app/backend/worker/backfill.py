"""Queue a suggestions-only pass for every processed photo, so existing items
get a subcategory (plan 11). Fills empty fields only; safe to re-run.
    docker compose -f app/infra/compose/compose.yaml exec worker python -m app.backend.worker.backfill
"""
from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.db.db import get_db

assets = get_db().get_collection(models.ImageAsset.COLLECTION_NAME)
n = 0
for a in assets.find({"status": models.ImageAssetStatus.PROCESSED}, {"_id": 1}):
    queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": a["_id"], "suggest_only": True})
    n += 1
print(f"queued {n} assets for suggestions")
