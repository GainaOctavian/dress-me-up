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
from app.backend.renderer import backfill, bodies, dress, outfit3d

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


def body_spec(db, body_id: str) -> dress.BodySpec:
    """A mannequin from the files baked into the image; a user body from its
    doc, pose params from S3. Keyed by the neutral image (new on every build)."""
    if dress.is_mannequin(body_id):
        return dress.mannequin(body_id)
    body = models.Body(**db.get_collection(models.Body.COLLECTION_NAME).find_one({"_id": body_id}))
    if body.status != "ready":
        raise ValueError(f"body {body_id} is {body.status}")
    return dress.BodySpec(
        key=f"{body.id}:{body.poses['neutral'].image_key}", gender=body.gender, pheno=body.phenotype,
        params={p: np.load(io.BytesIO(s3.get_bytes(pose.params_key))) for p, pose in body.poses.items()},
        keypoints=body.poses["neutral"].keypoints,
    )


def build_body(body_id: str) -> None:
    """Plan 16a: the user's body from their measurements (bodies.fit_phenotype
    + bodies.build), stored like the mannequins (pose WebPs + keypoints) plus
    the pose params; then their outfits on it re-render."""
    db = get_db()
    col = db.get_collection(models.Body.COLLECTION_NAME)
    data = col.find_one({"_id": body_id})
    if not data or data.get("status") != "building":
        log.info("body %s: gone or not building, skipping", body_id)
        return
    body = models.Body(**data)
    started = time.monotonic()
    i = body.input_cm
    pheno = bodies.fit_phenotype(body.gender, i["height_cm"], i["weight_kg"],
                                 i.get("chest_cm"), i.get("waist_cm"), i.get("hips_cm"))
    poses = {}
    with tempfile.TemporaryDirectory() as tmp:
        spec = bodies.build(pheno, tmp)
        for pose_id, pose in spec["poses"].items():
            buf = io.BytesIO()
            Image.open(os.path.join(tmp, f"{pose_id}.png")).save(buf, "WEBP", quality=90, method=6)
            webp = buf.getvalue()
            # private prefix: presigned for the owner only (services/body)
            stem = f"bodies/{body.owner_id}/{body.id}/{pose_id}-{hashlib.sha256(webp).hexdigest()[:10]}"
            s3.put_bytes(f"{stem}.webp", webp, "image/webp")
            with open(os.path.join(tmp, f"{pose_id}.pose.npy"), "rb") as f:
                s3.put_bytes(f"{stem}.npy", f.read(), "application/octet-stream")
            poses[pose_id] = models.BodyPose(image_key=f"{stem}.webp", params_key=f"{stem}.npy", **pose)
    result = col.update_one(
        {"_id": body_id, "status": "building", "input_cm": body.input_cm},  # not re-saved meanwhile
        {"$set": {"status": "ready", "error": None, "phenotype": pheno,
                  "measurements_cm": spec["measurements_cm"],
                  "poses": {k: p.model_dump() for k, p in poses.items()}}},
    )
    new_keys = {k for p in poses.values() for k in (p.image_key, p.params_key)}
    if result.modified_count == 0:  # changed or deleted while building: drop this build
        for k in new_keys:
            s3.delete(k)
        return
    for p in body.poses.values():
        for k in (p.image_key, p.params_key):
            if k and k not in new_keys:
                s3.delete(k)
    n = backfill.queue_renders(db, {"body_id": body_id})
    log.info("body %s built in %.1fs (%s), %d outfit(s) re-rendering", body_id,
             time.monotonic() - started, spec["measurements_cm"], n)


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
        png, glb = os.path.join(tmp, "render.png"), os.path.join(tmp, "scene.glb")
        outfit3d.render_outfit(body_spec(db, outfit.body_id), outfit.pose_id or "neutral",
                               garments(db, outfit), png, glb)
        buf = io.BytesIO()
        Image.open(png).save(buf, "WEBP", quality=90, method=6)
        model = open(glb, "rb").read()
    webp = buf.getvalue()
    stem = f"renders/{outfit_id}/{outfit.pose_id or 'neutral'}-{hashlib.sha256(webp).hexdigest()[:10]}"
    key, model_key = f"{stem}.webp", f"{stem}.glb"
    s3.put_bytes(key, webp, "image/webp")
    s3.put_bytes(model_key, model, "model/gltf-binary")
    old = data.get("render") or {}
    result = outfits.update_one(
        {"_id": outfit_id, "render.version": version},
        {"$set": {"render.status": "done", "render.image_key": key, "render.model_key": model_key,
                  "render.error": None}},
    )
    if result.modified_count == 0:  # saved again while rendering: the newer job wins
        s3.delete(key)
        s3.delete(model_key)
        return
    for k in ("image_key", "model_key"):
        if old.get(k) and old[k] not in (key, model_key):
            s3.delete(old[k])
    log.info("outfit %s v%s rendered in %.1fs", outfit_id, version, time.monotonic() - started)


def on_body(channel, method, _props, body):
    body_id = json.loads(body)["body_id"]
    try:
        build_body(body_id)
    except Exception as e:
        log.exception("body %s failed", body_id)
        get_db().get_collection(models.Body.COLLECTION_NAME).update_one(
            {"_id": body_id, "status": "building"}, {"$set": {"status": "failed", "error": str(e)[:300]}})
    channel.basic_ack(delivery_tag=method.delivery_tag)


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
            params = pika.URLParameters(queue.RABBITMQ_URL)
            # a body build blocks this thread ~1.5 min: past the default
            # 60 s heartbeat RabbitMQ would drop the connection mid-job
            params.heartbeat = 600
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)  # one job at a time, either queue
            for name, callback in ((queue.RENDER_QUEUE, on_message), (queue.BODY_QUEUE, on_body)):
                channel.queue_declare(queue=name, durable=True)
                channel.basic_consume(queue=name, on_message_callback=callback)
            log.info("waiting for jobs on %s, %s", queue.RENDER_QUEUE, queue.BODY_QUEUE)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            log.warning("RabbitMQ unavailable, retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
