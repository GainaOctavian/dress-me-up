FROM python:3.12-slim

ENV PYTHONPATH="/" \
    PYTHONUNBUFFERED=1 \
    U2NET_HOME=/models/rembg \
    HF_HOME=/models/hf

# CPU-only torch keeps the image ~1 GB smaller than the default CUDA build
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY app/backend/worker/requirements.txt /app/backend/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/worker/requirements.txt

# bake the models into the image so the first job isn't a 1 GB download
RUN python -c "from rembg import new_session; new_session('u2net')" \
 && python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')"

COPY app/backend/common /app/backend/common
COPY app/backend/worker /app/backend/worker

CMD ["python", "-m", "app.backend.worker.main"]
