# Offline asset pipeline (plan 12): Anny (Apache-2.0, CC0 MakeHuman assets)
# generates the mannequin meshes + keypoints, Blender renders them.
# Not part of the running stack; run on demand (see app/backend/CLAUDE.md -> Bodies).
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libxkbcommon0 libsm6 libice6 libegl1 \
  && rm -rf /var/lib/apt/lists/*

# CPU-only torch, then Anny WITHOUT the [smpl] extra (non-commercial topology)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir anny trimesh numpy

# Blender as a Python module (official `bpy` wheel, Python 3.11): renders in
# the same process as Anny, no 1 GB tarball to unpack. GPL; used only as a
# tool on our machine, the renders are ours.
RUN pip install --no-cache-dir bpy==4.2.0

ENV ANNY_CACHE_DIR=/cache/anny
# parse MakeHuman assets once at build time (takes minutes on first run)
RUN python -c "import anny; anny.Anny()"

# trimesh cross-sections (torso outlines, girths)
RUN pip install --no-cache-dir scipy

WORKDIR /work
