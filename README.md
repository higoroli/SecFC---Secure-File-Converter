# SecFC - Secure File Converter

<p align="center">
  <b>Conversor de Arquivos 100% Seguro, Local e em Memória RAM</b>
</p>

---

## 📌 Sobre o Projeto

O **SecFC (Secure File Converter)** é uma aplicação desktop desenvolvida para lidar com a conversão, unificação e pré-visualização de arquivos de maneira **totalmente isolada e privada**. 

Diferente de conversores online e ferramentas convencionais, o SecFC executa todo o processamento dos arquivos **exclusivamente na memória RAM** da máquina do usuário. Nenhum dado ou arquivo intermediário é gravado em disco ou transmitido via rede, garantindo conformidade rigorosa com normas de privacidade, LGPD e segurança corporativa.

---

## ✨ Principais Funcionalidades

- **🔒 Segurança & Privacidade Total**: Processamento em RAM sem persistência em disco ou envio para servidores externos.
- **🖼️ Conversão de Imagens**:
  - Formatos: `PNG`, `JPG`/`JPEG`, `WEBP`, `PDF`.
  - Ajuste personalizado ou predefinido de resolução (HD, Full HD, 4K, Custom).
  - Controle fino de qualidade/compressão (10% a 100%).
  - Suporte a correção automática de orientação EXIF.
- **📊 Conversão de Planilhas**:
  - Formatos: `XLSX`, `CSV`, `PDF` (com layout paisagem A4 e quebra de colunas adaptativa).
  - Detecção automática de *Encoding* (UTF-8, Latin-1, CP1252, etc.) e separador de colunas (`,`, `;`, `Tab`, `|`).
- **📝 Documentos de Texto & PDF**:
  - Formatos: `DOCX`, `TXT`, `PDF`.
  - Reconstrução estrutural nativa de PDF para DOCX editável (preservando tabelas, imagens e fontes).
  - Integração nativa com engine do Microsoft Word (Windows) e fallbacks resilientes (ReportLab / PyMuPDF).
- **🔗 Unificação / Fusão de PDFs**:
  - Junção direta e em lote de múltiplos arquivos PDF ou conversão massiva com reordenação dinâmica.
- **👁️ Visualização em Tempo Real (Preview)**:
  - Prévia de imagens, tabelas paginadas e páginas de PDF/texto com controles de zoom e navegação.
- **🎨 Interface Moderna**:
  - Construída com CustomTkinter, suporte a Drag & Drop nativo, alternância entre temas (Claro, Escuro e Sistema) e suporte multilíngue (`pt_BR`).

---

## 📂 Estrutura do Projeto

```text
├── app_local.py          # Ponto de entrada da aplicação GUI (CustomTkinter)
├── batch_processor.py      # Módulo para processamento em lote e unificação
├── requirements.txt        # Dependências do projeto
├── assets/                 # Ícones, logos e recursos visuais
│   ├── app_icon.ico
│   ├── app_icon.png
│   ├── Logo_squad_lat.png
│   ├── Logo_squad_lat_b.png
│   ├── imagem.png
│   ├── pdf.png
│   ├── planilhas.png
│   └── texto.png
├── core/                   # Núcleo de processamento e lógica de conversão
│   ├── image_conversor.py  # Processamento e otimização de imagens (Pillow)
│   ├── pdf_merger.py       # Fusão e manipulação de PDFs (PyMuPDF)
│   ├── sheet_conversor.py # Leitura/exportação de planilhas (Pandas, ReportLab)
│   ├── text_conversor.py  # Conversão de textos/PDFs (pdf2docx, win32com, PyMuPDF)
│   └── utils.py           # Utilitários de interface, scroll e i18n
└── locales/                # Arquivos de internacionalização
    └── pt_BR.json          # Dicionário de tradução em Português (Brasil)
```

---

## 🚀 Execução da Aplicação

Como o executável já está gerado (`.exe`), não há necessidade de instalação de dependências ou ambiente Python para execução final:

1. Execute o arquivo **`SecFC - Secure File Converter.exe`** (ou nome atribuído ao executável compilado).
2. Arraste e solte o arquivo desejado na área central ou clique em **"Abrir Arquivo"**.
3. Ajuste as configurações de conversão desejadas no painel esquerdo.
4. Clique em **"Converter Arquivo"** ou **"Juntar Arquivos PDF"**.
5. Visualize o resultado na área de prévia e clique em **"Salvar Arquivo"** para escolher o local de destino no seu computador.

---

## 🛠️ Tecnologias Utilizadas

- **Interface Gráfica**: CustomTkinter, TkinterDnD2.
- **Processamento de Texto & PDF**: PyMuPDF (`fitz`), `pdf2docx`, `python-docx`, ReportLab, `pywin32`.
- **Processamento de Dados**: Pandas, OpenPyXL, XlsxWriter, Chardet.
- **Processamento de Imagens**: Pillow (PIL).

---

## ✒️ Créditos e Autoria

- **Desenvolvedor**: Higor Oliveira — Squad de Dados.