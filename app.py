from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import os
import zipfile
import uuid
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "work"
STATIC_DIR = BASE_DIR / "static"
WORK_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="分鏡切圖工具", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def make_zip_from_crops(image, boxes, job_dir: Path):
    output_dir = job_dir / "output"
    output_dir.mkdir(exist_ok=True)
    h_img, w_img = image.shape[:2]

    for idx, b in enumerate(boxes, start=1):
        x = max(0, int(round(float(b["x"]))))
        y = max(0, int(round(float(b["y"]))))
        w = max(1, int(round(float(b["w"]))))
        h = max(1, int(round(float(b["h"]))))
        x2 = min(w_img, x + w)
        y2 = min(h_img, y + h)
        if x >= w_img or y >= h_img or x2 <= x or y2 <= y:
            continue
        crop = image[y:y2, x:x2]
        cv2.imwrite(str(output_dir / f"scene_{idx:02d}.png"), crop)

    if not any(output_dir.iterdir()):
        raise HTTPException(status_code=422, detail="框線範圍無法切出圖片，請重新調整框線")

    zip_path = job_dir / "story_panels.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in sorted(output_dir.iterdir()):
            zipf.write(item, arcname=item.name)
    return zip_path


@app.get("/", response_class=HTMLResponse)
def home():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>分鏡切圖 API 已啟動</h1>"


@app.post("/split_with_boxes")
async def split_with_boxes(file: UploadFile = File(...), boxes: str = Form(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳 JPG 或 PNG 圖片")

    try:
        parsed_boxes = json.loads(boxes)
        if not isinstance(parsed_boxes, list) or len(parsed_boxes) == 0:
            raise ValueError("boxes must be a non-empty list")
    except Exception:
        raise HTTPException(status_code=400, detail="框線資料格式錯誤")

    job_id = uuid.uuid4().hex
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    npimg = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="圖片讀取失敗，請換一張圖試試")

    zip_path = make_zip_from_crops(image, parsed_boxes, job_dir)
    return FileResponse(
        path=str(zip_path),
        filename="story_panels.zip",
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=story_panels.zip"},
    )
