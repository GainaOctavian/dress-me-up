"""Queue a render for every dressed outfit that has no 3D model yet (renders
made before the GLB export), or for all of them with `all` (after renderer
changes). Same bump-and-publish as services/outfit._queue_render.

  docker compose -f app/infra/compose/compose.yaml exec renderer python -m app.backend.renderer.backfill [all]
"""
import sys

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.db.db import get_db


def main(everything: bool) -> None:
    outfits = get_db().get_collection(models.Outfit.COLLECTION_NAME)
    query = {"body_id": {"$ne": None}}
    if not everything:
        query["render.model_key"] = None  # also matches outfits never rendered
    n = 0
    for data in outfits.find(query):
        version = ((data.get("render") or {}).get("version") or 0) + 1
        render = {**(data.get("render") or {}), "status": "queued", "version": version, "error": None}
        outfits.update_one({"_id": data["_id"]}, {"$set": {"render": render}})
        queue.publish(queue.RENDER_QUEUE, {"outfit_id": data["_id"], "version": version})
        n += 1
    print(f"queued {n} outfit render(s)")


if __name__ == "__main__":
    main(sys.argv[1:] == ["all"])
