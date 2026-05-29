import base64
import logging
import fitz

logger = logging.getLogger(__name__)


def pdf_to_base64_images(pdf_path: str) -> list:
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("jpeg")
            b64 = base64.b64encode(img_bytes).decode()
            images.append(b64)
        doc.close()
        logger.info(f"Converted PDF {pdf_path}: {len(images)} pages")
    except Exception as e:
        logger.error(f"PDF conversion failed for {pdf_path}: {e}")
        if "password" in str(e).lower():
            raise Exception("Password protected PDF cannot be processed")
        raise
    return images
