import time
import io
import pdfplumber
from pypdf import PdfReader
from fastapi import UploadFile
from app.core.logging_conf import get_logger

logger = get_logger("app.services.parser")

class DocumentParserService:
    @staticmethod
    def _extract_pdfplumber(file_bytes: bytes) -> tuple[str, float]:
        start = time.time()
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            logger.warning("pdfplumber extraction failed", error=str(e))
        return text.strip(), time.time() - start

    @staticmethod
    def _extract_pypdf(file_bytes: bytes) -> tuple[str, float]:
        start = time.time()
        text = ""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            logger.warning("pypdf extraction failed", error=str(e))
        return text.strip(), time.time() - start

    @classmethod
    async def extract_best_text(cls, file: UploadFile) -> tuple[str, float]:
        raw_bytes = await file.read()
        await file.seek(0) 
        
        logger.info("Benchmarking text extraction architectures", filename=file.filename)
        
        txt_plumb, lat_plumb = cls._extract_pdfplumber(raw_bytes)
        txt_pypdf, lat_pypdf = cls._extract_pypdf(raw_bytes)
        
        logger.debug("Extraction benchmark results",
                     pdfplumber_latency=lat_plumb, pdfplumber_chars=len(txt_plumb),
                     pypdf_latency=lat_pypdf, pypdf_chars=len(txt_pypdf))
        
        best_text = txt_pypdf if len(txt_pypdf) >= len(txt_plumb) else txt_plumb
        max_lat = max(lat_plumb, lat_pypdf) 
        
        if not best_text:
            logger.error("Both extraction engines returned zero text volume")
            raise ValueError("Document appears to be empty or unreadable.")
            
        return best_text, lat_plumb + lat_pypdf