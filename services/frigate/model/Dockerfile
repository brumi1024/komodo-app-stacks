# Frigate's documented YOLOv9 ONNX export for OpenVINO. Build on the Docker host, then copy the file into model_cache:
#   docker build services/frigate/model --output /tmp/frigate-model
#   cp /tmp/frigate-model/yolov9-s-320.onnx <CONFIG_DIR>/frigate/model_cache/
# The build pulls about 14 GB of layers; prune them afterwards.
FROM python:3.11 AS build
RUN apt-get update && apt-get install --no-install-recommends -y cmake libgl1 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /bin/
WORKDIR /yolov9
ADD https://github.com/WongKinYiu/yolov9.git#5b1ea9a8b3f0ffe4fe0e203ec6232d788bb3fcff .
RUN uv pip install --system -r requirements.txt
RUN uv pip install --system onnx==1.18.0 onnxruntime onnx-simplifier==0.4.* onnxscript
ARG MODEL_SIZE=s
ARG IMG_SIZE=320
ADD https://github.com/WongKinYiu/yolov9/releases/download/v0.1/yolov9-${MODEL_SIZE}-converted.pt yolov9-${MODEL_SIZE}.pt
RUN sed -i "s/ckpt = torch.load(attempt_download(w), map_location='cpu')/ckpt = torch.load(attempt_download(w), map_location='cpu', weights_only=False)/g" models/experimental.py
RUN python3 export.py --weights ./yolov9-${MODEL_SIZE}.pt --imgsz ${IMG_SIZE} --simplify --include onnx

FROM scratch
ARG MODEL_SIZE=s
ARG IMG_SIZE=320
COPY --from=build /yolov9/yolov9-${MODEL_SIZE}.onnx /yolov9-${MODEL_SIZE}-${IMG_SIZE}.onnx
