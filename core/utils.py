import io
import json
from pathlib import Path
from PIL import Image
import customtkinter as ctk


class AutoScrollableFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame customizado que oculta a barra de rolagem quando não necessária."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        if hasattr(self, "_scrollbar"):
            self._scrollbar.grid_remove()
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind(
                "<Configure>",
                lambda e: self._parent_canvas.itemconfig(
                    self._parent_canvas.find_withtag("all")[0], width=e.width
                ) if self._parent_canvas.find_withtag("all") else None
            )

    def _check_scrollbar(self, event=None):
        if not hasattr(self, "_parent_canvas") or not hasattr(self, "_scrollbar"):
            return
        
        bbox = self._parent_canvas.bbox("all")
        if bbox:
            content_height = bbox[3] - bbox[1]
            canvas_height = self._parent_canvas.winfo_height()

            if content_height > canvas_height:
                self._scrollbar.grid()
            else:
                self._scrollbar.grid_remove()


class LanguageManager:
    """Gerenciador central de traduções e textos em JSON."""
    def __init__(self, json_path: Path):
        self.translations = {}
        self.load_translations(json_path)

    def load_translations(self, path: Path):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        else:
            print(f"Aviso: Ficheiro de localização não encontrado em {path}")

    def get(self, key_path, **kwargs):
        keys = key_path.split(".")
        val = self.translations
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return key_path
        if isinstance(val, str) and kwargs:
            try:
                return val.format(**kwargs)
            except KeyError:
                return val
        return val


def convert_multi_images_to_pdf(file_list, target_res=None, quality=85, error_msg_func=None):
    """Converte múltiplas imagens da memória e mescla em um arquivo PDF único."""
    pil_images = []
    for file_item in file_list:
        raw_bytes = bytes(file_item['bytes'])
        img = Image.open(io.BytesIO(raw_bytes))
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        if target_res:
            img = img.resize(target_res, Image.Resampling.LANCZOS)
            
        pil_images.append(img)
        
    if not pil_images:
        msg = error_msg_func() if error_msg_func else "Nenhuma imagem válida foi fornecida."
        raise ValueError(msg)
        
    pdf_buffer = io.BytesIO()
    first_image = pil_images[0]
    rest_images = pil_images[1:]
    
    first_image.save(
        pdf_buffer,
        format="PDF",
        save_all=True,
        append_images=rest_images,
        quality=quality
    )
    pdf_buffer.seek(0)
    return pdf_buffer, pil_images