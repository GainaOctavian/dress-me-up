# 3D outfit renderer (plan 19): Anny + Blender (bpy) + the shared app code.
# Python 3.11: the official bpy 4.2 wheel targets it.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libxkbcommon0 libsm6 libice6 libegl1 libgomp1 \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH="/" \
    PYTHONUNBUFFERED=1 \
    ANNY_CACHE_DIR=/cache/anny \
    BODY_ASSETS=/body-assets

# CPU torch + Anny WITHOUT the [smpl] extra (non-commercial topology)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir anny trimesh numpy scipy pillow \
 && pip install --no-cache-dir bpy==4.2.0
# parse the MakeHuman assets once at build time
RUN python -c "import anny; anny.Anny()"

COPY app/backend/renderer/requirements.txt /app/backend/renderer/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/renderer/requirements.txt

# solved poses + neutral keypoints (render_bodies.py output)
COPY app/infra/body-assets/out/bodies.json /body-assets/bodies.json
COPY app/infra/body-assets/out/mannequin_male/*.npy /body-assets/mannequin_male/
COPY app/infra/body-assets/out/mannequin_female/*.npy /body-assets/mannequin_female/

# 3D garment models (MakeHuman CC0, see app/infra/clothes/README.md)
COPY app/infra/clothes /clothes
ENV CLOTHES=/clothes

COPY app/backend/common /app/backend/common
COPY app/backend/renderer /app/backend/renderer

CMD ["python", "-m", "app.backend.renderer.main"]
