"""Extraction locale bornée de PDF, images et exports ERP."""
import io
import re
import warnings
from PIL import Image
import fitz
import pandas as pd
import pytesseract
from src.config import DATA, MAX_PIXELS, MAX_UPLOAD
from src.schemas.pydantic_models import Order


def bounded_image(data):
    if len(data) > MAX_UPLOAD:
        raise ValueError("Image supérieure à 8 Mo")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        image = Image.open(io.BytesIO(data))
        if image.width*image.height > MAX_PIXELS:
            raise ValueError("Image supérieure à 16 mégapixels")
        image.load()
        return image.convert("RGB")


def ocr(image):
    langs = pytesseract.get_languages(config="")
    lang = "fra+eng" if "fra" in langs else "eng"
    return pytesseract.image_to_string(image, lang=lang, config="--psm 6", timeout=15)[:16000]


def extract_pdf(data):
    if len(data) > MAX_UPLOAD:
        raise ValueError("PDF supérieur à 8 Mo")
    result = []
    with fitz.open(stream=data, filetype="pdf") as pdf:
        if len(pdf) > 20:
            raise ValueError("20 pages maximum par import")
        for index, page in enumerate(pdf):
            text = page.get_text()[:16000]
            if not text.strip():
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                text = ocr(Image.open(io.BytesIO(pix.tobytes("png"))))
            result.append({"page": index+1, "text": text, "figures": len(page.get_images())})
    return result


def parse_erp(data, extension):
    if len(data) > MAX_UPLOAD:
        raise ValueError("Export supérieur à 8 Mo")
    if extension == ".csv":
        frame = pd.read_csv(io.BytesIO(data), dtype={"id": str, "reference": str}, nrows=31)
    elif extension == ".xlsx":
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 32*1024*1024:
                raise ValueError("Archive Excel décompressée trop volumineuse")
        frame = pd.read_excel(io.BytesIO(data), nrows=31)
    else:
        raise ValueError("CSV et XLSX uniquement")
    required = {"id", "reference", "quantity", "due", "release", "priority"}
    if not required <= set(frame.columns) or not 1 <= len(frame) <= 30:
        raise ValueError("Colonnes requises : id, reference, quantity, due, release, priority ; 1 à 30 OF")
    import json
    catalog = json.loads((DATA/"synthetic/catalog.json").read_text())
    output = []
    for row in frame.to_dict("records"):
        if row["reference"] not in catalog:
            raise ValueError(f"Référence absente du catalogue : {row['reference']}")
        info = catalog[row["reference"]]
        clean = {k: row[k] for k in required}
        # Pas de coercition des nombres fractionnaires vers des entiers.
        for name in ["quantity", "due", "release", "priority"]:
            if pd.isna(clean[name]) or float(clean[name]) != int(clean[name]):
                raise ValueError(f"{name} doit être un entier")
            clean[name] = int(clean[name])
        sources = dict(info["sources"])
        for field in ["due", "release"]:
            sources[field] = {"document_id": "erp_import", "page": 1, "element_id": str(row["id"]), "version": "sha256-import"}
        clean.update({k: info[k] for k in ("family", "unit_minutes", "eligible", "tool")})
        clean.update(sources=sources)
        output.append(Order.model_validate(clean))
    if len({o.id for o in output}) != len(output):
        raise ValueError("OF dupliqués dans l'export")
    return output


def parse_observation(text):
    import unicodedata
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()
    machine = re.search(r"\b(?:CNC|TOUR)[ -]([A-D])\b", plain)
    if machine:
        prefix = "CNC" if machine.group().startswith("CNC") else "TOUR"
        return {"kind": "machine_display", "machine_id": f"{prefix}-{machine[1]}", "state": "stopped" if "ARRET" in plain or "STOP" in plain else "unknown", "downtime_minutes": None}
    of = re.search(r"\bOF[- ]?(\d{3,6})\b", plain)
    ref = re.search(r"\bREF[- ]?(\d{3,6})\b", plain)
    qty = re.search(r"QUANTIT[EY][ :]+(\d+)", plain)
    due = re.search(r"(?:ECHEANCE|DUE)[ :]+(\d{1,2}):(\d{2})", plain)
    if of:
        return {"kind": "work_order", "id": f"OF-{of[1]}", "reference": f"REF-{ref[1]}" if ref else None, "quantity": int(qty[1]) if qty else None, "due": (int(due[1])-8)*60+int(due[2]) if due else None}
    return {"kind": "unknown"}
