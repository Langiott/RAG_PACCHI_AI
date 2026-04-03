# cat main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pytesseract
from PIL import Image
import io
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Errore generale: {str(exc)}")
    return JSONResponse(status_code=500, content={"error": str(exc)})

@app.get("/")
async def root():
    return {"status": "OCR server attivo", "version": "2.1", "engine": "Tesseract"}

def ocr_from_bytes(contents: bytes):
    if not contents:
        raise HTTPException(status_code=400, detail="File vuoto")

    try:
        image = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Immagine non valida: {str(e)}")

    if image.mode != "L":
        image = image.convert("L")

    text = pytesseract.image_to_string(image, lang="ita+eng").strip()
    lines = [l for l in text.split("\n") if l.strip()]

    return {
        "text": text,
        "status": "success",
        "lines_found": len(lines)
    }

@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Il file deve essere un'immagine")
    contents = await file.read()
    return ocr_from_bytes(contents)

class OCRUrlRequest(BaseModel):
    image_url: str

@app.post("/ocr-from-url")
async def run_ocr_from_url(payload: OCRUrlRequest):
    try:
        r = requests.get(payload.image_url, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Errore download immagine: {str(e)}")

    return ocr_from_bytes(r.content)
