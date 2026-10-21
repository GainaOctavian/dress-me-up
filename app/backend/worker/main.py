"""Image processing worker (plan 04).

Consumes `image_processing` jobs ({"image_asset_id", "attempt"}), runs the
pipeline in processing.py, stores the cutout and suggestions on the asset,
and fills in empty colors/tags/categories of the item that uses it.
A sweeper thread re-queues stuck assets and deletes abandoned uploads.
"""
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import pika

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.db.db import get_db
from app.backend.common.storage import s3
from app.backend.worker import processing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

MAX_ATTEMPTS = 3
SWEEP_EVERY = 300  # seconds
Status = models.ImageAssetStatus


def _assets():
    return get_db().get_collection(models.ImageAsset.COLLECTION_NAME)


def _items():
    return get_db().get_collection(models.Item.COLLECTION_NAME)


def merge_into_item(asset_id: str, result: dict) -> None:
    """Fill what the user left empty; never overwrite their input
    (tags are merged, colors/categories only set when empty)."""
    item = _items().find_one({"image_asset_id": asset_id})
    if not item:
        return  # not saved yet; the form reads suggestions from the asset
    update = {}
    if not item.get("colors"):
        update["colors"] = result["colors"]
    if not item.get("categories") and result.get("category"):
        update["categories"] = [result["category"]]
    merged = list(dict.fromkeys((item.get("tags") or []) + result["tags"]))
    if merged != (item.get("tags") or []):
        update["tags"] = merged
    if update:
        _items().update_one({"_id": item["_id"]}, {"$set": update})


def handle(asset_id: str) -> None:
    asset = _assets().find_one({"_id": asset_id})
    if not asset:
        log.info("asset %s gone, skipping", asset_id)
        return
    if asset["status"] not in (Status.READY, Status.FAILED, Status.PROCESSING):
        log.info("asset %s is %s, skipping", asset_id, asset["status"])
        return  # already processed (redelivery) or never uploaded
    _assets().update_one({"_id": asset_id}, {"$set": {
        "status": Status.PROCESSING,
        "metadata.processing_started_at": datetime.now(timezone.utc),
    }})

    started = time.monotonic()
    result = processing.process(s3.get_bytes(asset["s3_key"]))
    key = f"processed/{asset['owner_id']}/{asset_id}.png"
    s3.put_bytes(key, result["png"], "image/png")

    _assets().update_one({"_id": asset_id}, {"$set": {
        "status": Status.PROCESSED,
        "processed_s3_key": key,
        "width": result["width"],
        "height": result["height"],
        "metadata.colors": result["colors"],
        "metadata.tags": result["tags"],
        "metadata.category": result["category"],
        "metadata.model": "u2net + plain-bg mask + ViT-B-32/laion2b",
        "metadata.seconds": round(time.monotonic() - started, 2),
    }})
    merge_into_item(asset_id, result)
    log.info("asset %s processed in %.1fs: %s %s %s", asset_id,
             time.monotonic() - started, result["category"], result["colors"], result["tags"])


def on_message(channel, method, _props, body):
    msg = json.loads(body)
    asset_id, attempt = msg["image_asset_id"], msg.get("attempt", 1)
    try:
        handle(asset_id)
    except Exception:
        log.exception("asset %s failed (attempt %d)", asset_id, attempt)
        if attempt < MAX_ATTEMPTS:
            queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": asset_id, "attempt": attempt + 1})
        else:
            # the item keeps showing the original photo
            _assets().update_one({"_id": asset_id}, {"$set": {"status": Status.FAILED}})
    channel.basic_ack(delivery_tag=method.delivery_tag)


def sweep() -> None:
    """Re-queue assets stuck in ready/processing; delete uploads nobody
    attached within a day (picked a photo, then cancelled)."""
    now = datetime.now(timezone.utc)
    stuck = _assets().find({"$or": [
        {"status": Status.READY, "uploaded_at": {"$lt": now - timedelta(minutes=5)}},
        {"status": Status.PROCESSING,
         "metadata.processing_started_at": {"$lt": now - timedelta(minutes=10)}},
    ]}, {"_id": 1})
    for a in stuck:
        log.info("sweeper: re-queue %s", a["_id"])
        queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": a["_id"]})

    abandoned = _assets().find({
        "attached": {"$ne": True},
        "uploaded_at": {"$lt": now - timedelta(hours=24)},
    })
    for a in abandoned:
        # older assets (before `attached` existed) may be in use: check items
        if _items().find_one({"image_asset_id": a["_id"]}, {"_id": 1}):
            _assets().update_one({"_id": a["_id"]}, {"$set": {"attached": True}})
            continue
        for key in (a.get("s3_key"), a.get("processed_s3_key")):
            if key:
                s3.delete(key)
        _assets().delete_one({"_id": a["_id"]})
        log.info("sweeper: deleted abandoned upload %s", a["_id"])


def sweeper_loop() -> None:
    while True:
        try:
            sweep()
        except Exception:
            log.exception("sweep failed")
        time.sleep(SWEEP_EVERY)


def main() -> None:
    log.info("loading models…")
    processing._rembg_session()
    processing._clip()
    threading.Thread(target=sweeper_loop, daemon=True).start()
    while True:  # reconnect forever: RabbitMQ may restart under us
        try:
            connection = pika.BlockingConnection(pika.URLParameters(queue.RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue=queue.IMAGE_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue.IMAGE_QUEUE, on_message_callback=on_message)
            log.info("waiting for jobs on %s", queue.IMAGE_QUEUE)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            log.warning("RabbitMQ unavailable, retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
