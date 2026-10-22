from pathlib import Path
from PIL import Image

# Caminho do teu PNG original (ajusta o nome se necessário, ex: "app_icon.png")
png_path = Path(r"C:/Users/bp559286/Documents/_geral doc/Script Python/projet/Conversor/assets/app_icon.png")
ico_path = Path(r"C:/Users/bp559286/Documents/_geral doc/Script Python/projet/Conversor/assets/app_icon.ico")

if png_path.exists():
    img = Image.open(png_path)
    
    # Garante o modo RGBA para preservar a nitidez e cantos arredondados/transparência
    img = img.convert("RGBA")
    
    # Gera o ICO incluindo múltiplos tamanhos para alta definição em qualquer escala do Windows
    img.save(
        ico_path, 
        format="ICO", 
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"Ícone gerado com sucesso em alta resolução: {ico_path.resolve()}")
else:
    print(f"Ficheiro não encontrado: {png_path}")