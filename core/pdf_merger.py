import io
from typing import List, Tuple
from PIL import Image
import fitz  # PyMuPDF


def merge_pdf_buffers(pdf_buffers: List[io.BytesIO]) -> Tuple[io.BytesIO, List[Image.Image]]:
    """
    Combina múltiplos buffers de PDF (io.BytesIO) em um único arquivo PDF.
    
    Retorna:
        - output_buffer: io.BytesIO contendo o PDF final unificado
        - preview_images: Lista de PIL.Image com todas as páginas do PDF unificado
    """
    merged_pdf = fitz.open()

    for buf in pdf_buffers:
        buf.seek(0)
        # Abre cada PDF a partir do stream de bytes
        with fitz.open(stream=buf.read(), filetype="pdf") as doc:
            merged_pdf.insert_pdf(doc)

    output_buffer = io.BytesIO()
    merged_pdf.save(output_buffer)
    output_buffer.seek(0)

    # Renderiza as páginas para a prévia visual na UI
    preview_images = []
    for page in merged_pdf:
        pix = page.get_pixmap(dpi=130)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        preview_images.append(img)

    merged_pdf.close()
    return output_buffer, preview_images

def merge_pdf_bytes(pdf_bytes_list: List[bytes]) -> bytes:
    """Junta uma lista de PDFs em formato bytes e retorna o PDF único resultante em bytes."""
    merged_doc = fitz.open()
    for pdf_bytes in pdf_bytes_list:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            merged_doc.insert_pdf(doc)
    
    output_buffer = io.BytesIO()
    merged_doc.save(output_buffer)
    merged_doc.close()
    return output_buffer.getvalue()