import io
from typing import List, Dict, Any, Tuple
from PIL import Image
import fitz
import os

from core.text_conversor import convert_text
from core.sheet_conversor import convert_sheet
from core.image_conversor import convert_image
from core.pdf_merger import merge_pdf_buffers


def process_batch_to_pdf(
    files: List[Dict[str, Any]], 
    merge_into_single_pdf: bool = False
) -> Dict[str, Any]:
    """
    Processa múltiplos arquivos para conversão em PDF.
    
    Args:
        files: Lista de dicionários no formato:
               [{ 'bytes': b'...', 'ext': 'docx', 'filename': 'doc1.docx' }, ...]
        merge_into_single_pdf: Booleano vindo da chave/slide da interface.
        
    Retorna:
        Um dicionário com a estrutura de saída para a UI:
        - Se merge_into_single_pdf == True:
            {
                'merged': True,
                'pdf_buffer': io.BytesIO,
                'filename': 'resultado_unificado.pdf',
                'previews': List[Image.Image]
            }
        - Se merge_into_single_pdf == False:
            {
                'merged': False,
                'items': [
                    { 'filename': 'doc1.pdf', 'buffer': io.BytesIO, 'previews': [...] },
                    ...
                ]
            }
    """
    individual_results = []
    pdf_buffers_for_merge = []

    for file_item in files:
        file_bytes = file_item['bytes']
        ext = file_item['ext'].lower().replace(".", "")
        orig_name = file_item.get('filename', 'arquivo')
        base_name = orig_name.rsplit('.', 1)[0]

        pdf_buffer = None
        previews = []

        # 1. Roteamento pelo tipo de arquivo para conversão individual em PDF
        if ext in ["docx", "doc", "txt", "pdf"]:
            pdf_buffer, _, _, _, previews, _ = convert_text(
                file_bytes=file_bytes,
                source_ext=ext,
                target_format="pdf"
            )
        elif ext in ["xlsx", "xls", "csv"]:
            pdf_buffer, _, _, _, _, _ = convert_sheet(
                file_bytes=file_bytes,
                source_ext=ext,
                target_format="pdf"
            )
            # Reutiliza o renderizador do PyMuPDF para gerar as prévias das planilhas convertidas
            from core.text_conversor import generate_pdf_pages_images
            previews = generate_pdf_pages_images(pdf_buffer.getvalue())
            
        elif ext in ["png", "jpg", "jpeg", "webp", "bmp", "tiff"]:
            img_buf, _, img_obj = convert_image(
                file_bytes=file_bytes,
                target_format="JPEG"
            )
            # Converte imagem direta para PDF
            pdf_doc = fitz.open()
            img_pdf_bytes = fitz.open(stream=img_buf.getvalue(), filetype="jpeg").convert_to_pdf()
            pdf_doc.insert_pdf(fitz.open("pdf", img_pdf_bytes))
            
            pdf_buffer = io.BytesIO(pdf_doc.tobytes())
            previews = [img_obj]
            pdf_doc.close()

        if pdf_buffer:
            pdf_buffers_for_merge.append(pdf_buffer)
            individual_results.append({
                'filename': f"{base_name}.pdf",
                'buffer': pdf_buffer,
                'previews': previews
            })

    # 2. Verificação do botão/slide de unificação
    if merge_into_single_pdf and pdf_buffers_for_merge:
        merged_buffer, merged_previews = merge_pdf_buffers(pdf_buffers_for_merge)
        return {
            'merged': True,
            'pdf_buffer': merged_buffer,
            'filename': 'documentos_unificados.pdf',
            'previews': merged_previews
        }

    return {
        'merged': False,
        'items': individual_results
    }

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