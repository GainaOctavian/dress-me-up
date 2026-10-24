import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.backend.api.src.routes import auth
from app.backend.api.src.routes import user
from app.backend.api.src.routes import wardrobe
from app.backend.api.src.routes import item
from app.backend.api.src.routes import image
from app.backend.api.src.routes import outfit
from app.backend.api.src.routes import meta
from app.backend.api.src.routes import body
from app.backend.api.src.routes import friend
from app.backend.api.src.routes import feed
from app.backend.common.db import models
from app.backend.common.db.db import get_db

logger = logging.getLogger(__name__)

INDEXES = [
    (models.Item.COLLECTION_NAME, "wardrobe_ids", {}),
    (models.Item.COLLECTION_NAME, "owner_id", {}),
    # wardrobes are looked up by roles.<user_id>; keys are dynamic
    (models.Wardrobe.COLLECTION_NAME, "roles.$**", {}),
    (models.User.COLLECTION_NAME, "email", {"unique": True}),
    (models.Outfit.COLLECTION_NAME, "owner_id", {}),
    (models.Outfit.COLLECTION_NAME, "wardrobe_id", {}),
    (models.Outfit.COLLECTION_NAME, "items.item_id", {}),
    (models.Body.COLLECTION_NAME, "owner_id", {}),
    (models.Outfit.COLLECTION_NAME, [("owner_id", 1), ("shared", 1), ("created_at", -1)], {}),  # feed
    (models.FriendRequest.COLLECTION_NAME, "to_user_id", {}),
    (models.FriendRequest.COLLECTION_NAME, "from_user_id", {}),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # honour dependency overrides, so tests index their fake DB, not Atlas
    db = app.dependency_overrides.get(get_db, get_db)()
    for collection, key, options in INDEXES:
        try:
            db.get_collection(collection).create_index(key, **options)
        except Exception as e:  # never block startup on an index
            logger.warning("Index %s.%s not created: %s", collection, key, e)
    yield


app = FastAPI(
    title="Dress Me Up API",
    version="1.0.0",
    lifespan=lifespan
)


# Browser clients (Expo web during development). Native apps don't need CORS.
# e.g. CORS_ORIGINS=http://localhost:8090 in app/infra/compose/.env
if os.getenv("CORS_ORIGINS"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in os.environ["CORS_ORIGINS"].split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(user.router)
app.include_router(auth.router)
app.include_router(wardrobe.router)
app.include_router(item.router)
app.include_router(image.router)
app.include_router(outfit.router)
app.include_router(meta.router)
app.include_router(body.router)
app.include_router(friend.router)
app.include_router(feed.router)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse("/docs")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
