import io
from typing import Tuple, Optional
from PIL import Image, ImageOps, ImageFilter, ImageEnhance


def get_image_preview(file_bytes: bytes) -> Image.Image:
    """
    Carrega a imagem a partir dos bytes mantendo a orientação EXIF correta.
    """
    img = Image.open(io.BytesIO(file_bytes))
    return ImageOps.exif_transpose(img)


def enhance_image_quality(
    img: Image.Image, 
    scale_factor: float = 1.5, 
    sharpness_factor: float = 1.3
) -> Image.Image:
    """
    Aumenta a resolução e melhora a nitidez percebida da imagem.
    
    - scale_factor: Fator de multiplicação de resolução (ex: 1.5 aumenta 50%)
    - sharpness_factor: Intensidade do ganho de nitidez (1.0 é o original)
    """
    # 1. Redimensionamento de alta qualidade usando algoritmo Lanczos
    if scale_factor != 1.0:
        new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # 2. Máscara de nitidez para recuperar detalhes suavizados pelo upscale
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    
    # 3. Ajuste fino de nitidez (Sharpness)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpness_factor)
    
    return img


def convert_image(
    file_bytes: bytes, 
    target_format: str = "JPEG", 
    quality: int = 85,
    enhance: bool = False,
    scale_factor: float = 1.5,
    sharpness_factor: float = 1.3
) -> Tuple[io.BytesIO, str, Image.Image]:
    """
    Processa e converte imagens totalmente em memória (RAM) com alta eficiência.
    
    Parâmetros extras:
        - enhance: Ativa a melhoria de qualidade/nitidez e upscale
        - scale_factor: Multiplicador do tamanho da imagem se enhance=True
        - sharpness_factor: Ganho de nitidez aplicado se enhance=True
        
    Retorna:
        - output_buffer: io.BytesIO com o arquivo codificado
        - mime_type: Tipo MIME oficial do formato (ex: 'image/jpeg')
        - converted_img: Objeto PIL.Image processado para uso/exibição direta na UI
    """
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)  # Corrige rotação baseada na câmera/EXIF
    
    # Aplica o processo de melhoria de qualidade se solicitado
    if enhance:
        img = enhance_image_quality(
            img, 
            scale_factor=scale_factor, 
            sharpness_factor=sharpness_factor
        )

    fmt = target_format.upper().replace(".", "")
    if fmt == "JPG":
        fmt = "JPEG"

    # Mapeamento de tipos MIME oficiais
    mime_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "BMP": "image/bmp",
        "GIF": "image/gif",
        "TIFF": "image/tiff",
        "ICO": "image/x-icon"
    }
    mime_type = mime_map.get(fmt, f"image/{fmt.lower()}")

    # Tratamento de canais de cor e transparência para formatos incompatíveis
    if fmt in ["JPEG", "BMP"] and img.mode in ("RGBA", "LA", "P"):
        # Cria um fundo branco para mesclar transparências (evita fundo preto em JPG)
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background
    elif fmt == "PNG" and img.mode not in ("RGB", "RGBA", "L", "P"):
        img = img.convert("RGBA")

    output_buffer = io.BytesIO()

    # Otimização na escrita de acordo com as capacidades do formato
    save_kwargs = {}
    if fmt in ["JPEG", "WEBP"]:
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    elif fmt == "PNG":
        save_kwargs["optimize"] = True
        # Mapeia a escala 1-100 para o nível de compressão PNG (9-0)
        save_kwargs["compress_level"] = max(0, min(9, int((100 - quality) / 11)))

    img.save(output_buffer, format=fmt, **save_kwargs)
    output_buffer.seek(0)

    return output_buffer, mime_type, img