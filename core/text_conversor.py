import io
import os
import tempfile
import chardet
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from docx import Document

# Suporte ao pdf2docx para extração estrutural (texto, tabelas e figuras editáveis)
HAS_PDF2DOCX = False
try:
    from pdf2docx import Converter
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False

# Suporte ao Microsoft Word Engine no Windows (para DOCX -> PDF)
HAS_WIN32 = False
try:
    import win32com.client
    import pythoncom
    import winreg
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Fallback para criação de PDF sem MS Word
HAS_REPORTLAB = False
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def disable_word_pdf_warning():
    """Desativa no Registro do Windows o popup de aviso de conversão de PDF do Word."""
    if not HAS_WIN32:
        return
    try:
        key_path = r"Software\Microsoft\Office\16.0\Word\Options"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisableOpenReopenDialog", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass


def detect_file_encoding(file_bytes: bytes) -> str:
    """Detecta a codificação de texto inspecionando os primeiros 10KB."""
    sample = file_bytes[:10000]
    result = chardet.detect(sample)
    return result.get('encoding') or 'utf-8'


def convert_pdf_to_docx_structural(pdf_bytes: bytes) -> bytes:
    """
    Converte PDF para DOCX reconstruindo a estrutura nativa do Word:
    textos editáveis, fontes, tabelas e imagens extraídas separadamente.
    """
    tmp_in_path = None
    tmp_out_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
            tmp_in.write(pdf_bytes)
            tmp_in_path = tmp_in.name

        tmp_out_path = os.path.join(tempfile.gettempdir(), f"conv_{os.path.basename(tmp_in_path)}.docx")

        cv = Converter(tmp_in_path)
        # Parseia o PDF extraindo vetores, imagens e blocos de texto nativos
        cv.convert(tmp_out_path, start=0, end=None)
        cv.close()

        with open(tmp_out_path, "rb") as f_out:
            return f_out.read()
    finally:
        if tmp_in_path and os.path.exists(tmp_in_path):
            try: os.remove(tmp_in_path)
            except Exception: pass
        if tmp_out_path and os.path.exists(tmp_out_path):
            try: os.remove(tmp_out_path)
            except Exception: pass


def convert_with_word_engine(file_bytes: bytes, source_ext: str, target_format: str) -> bytes:
    """Realiza a conversão via MS Word apenas para DOCX -> PDF ou TXT."""
    if not HAS_WIN32:
        raise RuntimeError("win32com / Pythoncom não estão instalados.")

    disable_word_pdf_warning()
    pythoncom.CoInitialize()

    tmp_in_path = None
    tmp_out_path = None
    word = None
    doc = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{source_ext}") as tmp_in:
            tmp_in.write(file_bytes)
            tmp_in_path = tmp_in.name

        out_ext = target_format.lower()
        tmp_out_path = os.path.join(tempfile.gettempdir(), f"conv_{os.path.basename(tmp_in_path)}.{out_ext}")

        format_map = {"pdf": 17, "docx": 16, "txt": 2}
        export_fmt = format_map.get(out_ext, 17)

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(
            FileName=tmp_in_path,
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False
        )

        doc.SaveAs2(tmp_out_path, FileFormat=export_fmt)

        with open(tmp_out_path, "rb") as f_out:
            converted_bytes = f_out.read()

        return converted_bytes

    finally:
        if doc:
            try: doc.Close(False)
            except Exception: pass
        if word:
            try: word.Quit()
            except Exception: pass
        pythoncom.CoUninitialize()

        if tmp_in_path and os.path.exists(tmp_in_path):
            try: os.remove(tmp_in_path)
            except Exception: pass
        if tmp_out_path and os.path.exists(tmp_out_path):
            try: os.remove(tmp_out_path)
            except Exception: pass


def generate_fallback_pdf(text_content: str) -> bytes:
    """Gera um PDF em memória caso necessário."""
    buffer = io.BytesIO()
    if HAS_REPORTLAB:
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14
        )

        story = []
        for line in text_content.split('\n'):
            clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(clean_line if clean_line.strip() else "&nbsp;", style))
            story.append(Spacer(1, 4))

        doc.build(story)
    else:
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        page.insert_text((50, 50), text_content[:2000] if text_content else "Documento Vazio")
        pdf_doc.save(buffer)
        pdf_doc.close()

    return buffer.getvalue()


def generate_pdf_pages_images(pdf_bytes: bytes, dpi: int = 140) -> List[Image.Image]:
    """Renderiza as páginas do PDF em imagens para a pré-visualização no app."""
    images = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    return images


def generate_text_placeholder_image(text: str) -> Image.Image:
    """Cria uma imagem de visualização caso o PDF não possa ser renderizado."""
    img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")[:30] if text else ["Sem prévia disponível"]
    y = 40
    for line in lines:
        draw.text((40, y), line[:70], fill=(0, 0, 0))
        y += 20
    return img


def convert_text(
    file_bytes: bytes, 
    source_ext: str, 
    target_format: str = "PDF", 
    encoding: Optional[str] = None
) -> Tuple[io.BytesIO, str, str, str, List[Image.Image], str]:
    """Processa e converte documentos de texto (DOCX, TXT, PDF)."""
    source_ext = source_ext.lower().replace(".", "")
    target_format = target_format.lower()
    detected_enc = encoding or detect_file_encoding(file_bytes)

    output_buffer = io.BytesIO()
    pdf_bytes_for_preview = None
    extracted_text = ""

    # 1. Extração de texto para prévia
    if source_ext == "txt":
        extracted_text = file_bytes.decode(detected_enc, errors="ignore")
    elif source_ext == "docx":
        try:
            doc = Document(io.BytesIO(file_bytes))
            extracted_text = "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            extracted_text = ""
    elif source_ext == "pdf":
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as pdf_doc:
                extracted_text = "\n".join([page.get_text() for page in pdf_doc])
            pdf_bytes_for_preview = file_bytes
        except Exception:
            extracted_text = ""

    # 2. Conversão PDF -> DOCX (Estrutura Real e Editável)
    if source_ext == "pdf" and target_format == "docx":
        if HAS_PDF2DOCX:
            try:
                converted_bytes = convert_pdf_to_docx_structural(file_bytes)
                output_buffer.write(converted_bytes)
            except Exception:
                output_buffer.truncate(0)
                output_buffer.seek(0)

        # Fallback estruturado de parágrafos editáveis caso falhe
        if output_buffer.getvalue() == b"":
            doc = Document()
            for line in extracted_text.split("\n"):
                doc.add_paragraph(line)
            doc_io = io.BytesIO()
            doc.save(doc_io)
            output_buffer.write(doc_io.getvalue())

    # 3. Conversões de DOCX/TXT para PDF
    elif source_ext in ["docx", "txt"] and HAS_WIN32:
        try:
            converted_bytes = convert_with_word_engine(file_bytes, source_ext, target_format)
            output_buffer.write(converted_bytes)

            if target_format == "pdf":
                pdf_bytes_for_preview = converted_bytes
            else:
                pdf_bytes_for_preview = convert_with_word_engine(file_bytes, source_ext, "pdf")
        except Exception:
            output_buffer.truncate(0)
            output_buffer.seek(0)

    # 4. Fallbacks gerais
    if output_buffer.getvalue() == b"":
        if target_format == "pdf":
            pdf_bytes = file_bytes if source_ext == "pdf" else generate_fallback_pdf(extracted_text)
            output_buffer.write(pdf_bytes)
            pdf_bytes_for_preview = pdf_bytes
        elif target_format == "txt":
            output_buffer.write(extracted_text.encode("utf-8"))
        elif target_format == "docx":
            doc = Document()
            for line in extracted_text.split("\n"):
                doc.add_paragraph(line)
            doc_io = io.BytesIO()
            doc.save(doc_io)
            output_buffer.write(doc_io.getvalue())

    output_buffer.seek(0)

    mime_map = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    mime = mime_map.get(target_format, "application/octet-stream")

    # Renderiza a prévia visual na interface do app usando as páginas originais do PDF
    if pdf_bytes_for_preview:
        try:
            preview_images = generate_pdf_pages_images(pdf_bytes_for_preview)
        except Exception:
            preview_images = [generate_text_placeholder_image(extracted_text)]
    else:
        preview_images = [generate_text_placeholder_image(extracted_text)]

    return output_buffer, target_format, mime, extracted_text, preview_images, detected_enc