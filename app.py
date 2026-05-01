from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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

app = FastAPI(title="分鏡切圖工具", version="2.0.0")

# ✅ CORS（給1shop用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ========================
# 共用：切圖打包
# ========================
def make_zip_from_crops(image, boxes, job_dir: Path):
    output_dir = job_dir / "output"
    output_dir.mkdir(exist_ok=True)
    h_img, w_img = image.shape[:2]

    for idx, b in enumerate(boxes, start=1):
        x = max(0, int(b["x"]))
        y = max(0, int(b["y"]))
        w = max(1, int(b["w"]))
        h = max(1, int(b["h"]))

        x2 = min(w_img, x + w)
        y2 = min(h_img, y + h)

        if x >= w_img or y >= h_img or x2 <= x or y2 <= y:
            continue

        crop = image[y:y2, x:x2]
        cv2.imwrite(str(output_dir / f"scene_{idx:02d}.png"), crop)

    if not any(output_dir.iterdir()):
        raise HTTPException(status_code=422, detail="切圖失敗，請檢查框線")

    zip_path = job_dir / "result.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in output_dir.iterdir():
            zipf.write(item, item.name)

    return zip_path


# ========================
# 首頁（可有可無）
# ========================
@app.get("/", response_class=HTMLResponse)
def home():
    return "<h2>分鏡切圖 API 已啟動</h2>"


# ========================
# 手動框切圖
# ========================
@app.post("/split_with_boxes")
async def split_with_boxes(
    file: UploadFile = File(...),
    boxes: str = Form(...)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳圖片")

    try:
        parsed_boxes = json.loads(boxes)
    except:
        raise HTTPException(status_code=400, detail="框線格式錯誤")

    job_id = uuid.uuid4().hex
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    npimg = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="圖片讀取失敗")

    zip_path = make_zip_from_crops(image, parsed_boxes, job_dir)

    return FileResponse(
        str(zip_path),
        filename="result.zip",
        media_type="application/zip"
    )


# ========================
# 九宮格自動切圖（🔥你現在主力用這個）
# ========================
@app.post("/auto_grid")
async def auto_grid(file: UploadFile = File(...)):
    content = await file.read()
    npimg = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="圖片讀取失敗")

    h, w = image.shape[:2]

    rows = 3
    cols = 3

    cell_w = w // cols
    cell_h = h // rows

    boxes = []

    for r in range(rows):
        for c in range(cols):
            boxes.append({
                "x": c * cell_w,
                "y": r * cell_h,
                "w": cell_w,
                "h": cell_h
            })

    return JSONResponse({"boxes": boxes})
