"""3D outfit renderer (plan 19).

Consumes `outfit_render` jobs ({"outfit_id", "version"}): dresses the
outfit's mannequin in its pose (dress.py), uploads a WebP and stores it on
`outfit.render` - only if the outfit wasn't saved again meanwhile (a newer
version has its own job).
"""
import hashlib
import io
import json
import logging
import os
import tempfile
import time

import numpy as np
import pika
from PIL import Image

from app.backend.common import layering, queue
from app.backend.common.db import models
from app.backend.common.db.db import get_db
from app.backend.common.storage import s3
from app.backend.renderer import dress, outfit3d

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("renderer")


def garments(db, outfit: models.Outfit):
    """The outfit's visible items as Garments, bottom layer first."""
    visible = [oi for oi in outfit.items if oi.visible]
    items = {i["_id"]: i for i in db.items.find({"_id": {"$in": [oi.item_id for oi in visible]}})}
    assets = {a["_id"]: a for a in db.image_assets.find(
        {"_id": {"$in": [i.get("image_asset_id") for i in items.values()]}})}
    placed = [layering.Placed(items.get(oi.item_id, {}).get("subcategory"), oi.tucked,
                              oi.into_shoes, oi.layer_offset) for oi in visible]
    out = []
    for idx in layering.draw_order(placed):
        oi, p = visible[idx], placed[idx]
        item = items.get(oi.item_id)
        if not item:
            continue
        sub = layering.SUBCATEGORIES.get(p.subcategory or "")
        asset = assets.get(item.get("image_asset_id")) or {}
        key = asset.get("plain_s3_key")
        image = np.asarray(Image.open(io.BytesIO(s3.get_bytes(key))).convert("RGBA")) if key else None
        out.append(dress.Garment(
            subcategory=p.subcategory,
            slot=sub.slot.value if sub else None,
            role=sub.role.value if sub else None,
            band=layering.z_of(p),
            image=image,
            fit=(asset.get("metadata") or {}).get("fit"),
        ))
    return out


def handle(outfit_id: str, version: int) -> None:
    db = get_db()
    outfits = db.get_collection(models.Outfit.COLLECTION_NAME)
    data = outfits.find_one({"_id": outfit_id})
    if not data or not data.get("body_id") or (data.get("render") or {}).get("version") != version:
        log.info("outfit %s v%s: gone or superseded, skipping", outfit_id, version)
        return
    outfit = models.Outfit(**data)
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "render.png")
        outfit3d.render_outfit(outfit.body_id, outfit.pose_id or "neutral", garments(db, outfit), png)
        buf = io.BytesIO()
        Image.open(png).save(buf, "WEBP", quality=90, method=6)
    webp = buf.getvalue()
    key = f"renders/{outfit_id}/{outfit.pose_id or 'neutral'}-{hashlib.sha256(webp).hexdigest()[:10]}.webp"
    s3.put_bytes(key, webp, "image/webp")
    old = (data.get("render") or {}).get("image_key")
    result = outfits.update_one(
        {"_id": outfit_id, "render.version": version},
        {"$set": {"render.status": "done", "render.image_key": key, "render.error": None}},
    )
    if result.modified_count == 0:
        s3.delete(key)  # saved again while rendering: the newer job wins
        return
    if old and old != key:
        s3.delete(old)
    log.info("outfit %s v%s rendered in %.1fs", outfit_id, version, time.monotonic() - started)


def on_message(channel, method, _props, body):
    msg = json.loads(body)
    outfit_id, version = msg["outfit_id"], msg["version"]
    try:
        handle(outfit_id, version)
    except Exception as e:
        log.exception("outfit %s v%s failed", outfit_id, version)
        get_db().get_collection(models.Outfit.COLLECTION_NAME).update_one(
            {"_id": outfit_id, "render.version": version},
            {"$set": {"render.status": "failed", "render.error": str(e)[:300]}},
        )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    log.info("loading Anny…")
    outfit3d._model()
    while True:  # reconnect forever: RabbitMQ may restart under us
        try:
            connection = pika.BlockingConnection(pika.URLParameters(queue.RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue=queue.RENDER_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue.RENDER_QUEUE, on_message_callback=on_message)
            log.info("waiting for jobs on %s", queue.RENDER_QUEUE)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            log.warning("RabbitMQ unavailable, retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
