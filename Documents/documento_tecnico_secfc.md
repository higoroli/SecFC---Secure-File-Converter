# DOCUMENTO DE ESPECIFICAÇÃO TÉCNICA E ARQUITETURA DE SOFTWARE

**Sistema**: SecFC – Secure File Converter  
**Versão**: 1.0  
**Autor**: Higor de Oliveira da Silva (Squad de Dados)  
**Data**: Outubro de 2026  
**Status**: Produção / Executável Compilado  

---

## 1. SUMÁRIO EXECUTIVO

O **SecFC (Secure File Converter)** é um sistema de software desktop projetado para resolver a vulnerabilidade de vazamento e retenção não autorizada de dados decorrente do uso de conversores de arquivos baseados na web. 

A aplicação realiza a ingestão, parsing, transformação, renderização de pré-visualização e exportação de documentos em múltiplos formatos (`PNG`, `JPG`, `WEBP`, `CSV`, `XLSX`, `DOCX`, `TXT`, `PDF`), executando **100% das operações na memória RAM (In-Memory Processing)**. 

---

## 2. ARQUITETURA DO SISTEMA

### 2.1 Visão Geral do Fluxo de Dados

```text
[ Arquivo de Entrada ] 
        │
        ▼ (Leitura de Bytes / Drag & Drop)
[ Buffer RAM (io.BytesIO) ]
        │
        ├──► [ Detectores: Chardet / csv.Sniffer / EXIF ]
        │
        ├──► [ Núcleo de Conversão (Core) ]
        │      ├── Image Conversor (Pillow)
        │      ├── Sheet Conversor (Pandas / ReportLab)
        │      └── Text Conversor (pdf2docx / PyMuPDF / Win32Com)
        │
        ├──► [ Renderizador de Preview ] ──► (Interface CustomTkinter)
        │
        ▼ (Download do Usuário)
[ Arquivo Final Gravado pelo Usuário ]
```

### 2.2 Requisitos de Segurança & Isolamento

1. **In-Memory Guarantee**: Todos os buffers intermediários utilizam a classe `io.BytesIO`.
2. **Zero Disk Residual**: Nenhum arquivo temporário ou de *cache* é mantido em disco no ciclo de vida normal da conversão.
3. **Isolamento de Processos**: A conversão assíncrona é isolada por *threads* daemon (`threading.Thread`), evitando bloqueios da Thread Principal de UI (*Event Loop* do Tkinter).

---

## 3. ESPECIFICAÇÃO DOS MÓDULOS TÉCNICOS

### 3.1 Módulo Gráfico Principal (`app_local.py`)

- **Classe**: `SecureConverterApp(ctk.CTk)`
- **Responsabilidades**:
  - Inicialização do ambiente TkinterDnD2 para Suporte Nativo a Drag & Drop.
  - Gerenciamento de estado da interface (Modo Inicial vs. Modo Ativo).
  - Suporte Dinâmico a Temas (*Dark*, *Light*, *System*) com sincronização de cores no menu Tkinter clássico.
  - Gerenciamento de Threads assíncronas com técnica de *Debounce* (`debounce_update_preview`) para evitar atualizações concorrentes durante ajustes do usuário.

### 3.2 Módulo de Processamento de Imagens (`core/image_conversor.py`)

- **Função Principal**: `convert_image()`
- **Recursos Principais**:
  - `ImageOps.exif_transpose`: Normalização de rotações de imagem oriundas de sensores EXIF.
  - **Filtros e Upscaling**: Algoritmo `Lanczos` combinado com máscara de nitidez `UnsharpMask` e ajuste com `ImageEnhance.Sharpness`.
  - **Tratamento de Canais de Cor**: Fusão automática de canais Alfa (`RGBA`, `LA`, `P`) em fundos sólidos brancos ao exportar para formatos sem transparência (`JPEG`, `BMP`).

### 3.3 Módulo de Processamento de Planilhas (`core/sheet_conversor.py`)

- **Função Principal**: `convert_sheet()`
- **Recursos Principais**:
  - **Detecção de Codificação**: Inspeção automática com `chardet` nos primeiros 10KB.
  - **Detecção de Delimitador**: Algoritmo híbrido com `csv.Sniffer` e fallback por análise de freqüência de caracteres (`,`, `;`, `\t`, `|`).
  - **Motor de PDF (ReportLab)**: Exportação para PDF em orientação Paisagem (`landscape(A4)`), com quebra de colunas adaptativa por blocos e suporte a `wordWrap='CJK'` em células complexas.

### 3.4 Módulo de Documentos de Texto & PDF (`core/text_conversor.py`)

- **Função Principal**: `convert_text()`
- **Técnicas de Conversão**:
  1. **PDF ➔ DOCX**: Utilização da biblioteca `pdf2docx` para análise vetorial e extração de estruturas nativas (parágrafos, fontes, tabelas e imagens inline).
  2. **DOCX ➔ PDF (Windows)**: Automação via COM (`win32com.client`) controlando a engine nativa do Microsoft Word em modo *headless*. Supressão automatizada de popups via chave de registro `DisableOpenReopenDialog`.
  3. **Fallback Resiliente**: Fallback dinâmico para `ReportLab` ou `PyMuPDF` na ausência da suíte Office.

### 3.5 Módulo de Processamento em Lote e Fusão (`batch_processor.py` & `core/pdf_merger.py`)

- **Funções**: `process_batch_to_pdf()`, `merge_pdf_buffers()`
- **Funcionamento**: Unificação de múltiplos *streams* em formato PDF utilizando `fitz.open()` e inserção sequencial de páginas sem degradação de qualidade vetorial.

---

## 4. MATRIZ DE FORMATOS E SUPORTE

| Formato de Origem | Formatos de Destino Suportados | Recursos Especiais |
| :--- | :--- | :--- |
| **PNG / JPG / WEBP** | JPEG, PNG, WEBP, PDF | Resolução ajustável, qualidade (10-100%), fusão multi-imagem em PDF. |
| **CSV / XLSX / XLS** | XLSX, CSV, PDF | Detecção automática de encoding e separador, visualização paginada. |
| **DOCX / TXT** | PDF, DOCX, TXT | Preservação de formatação, conversão rápida em RAM. |
| **PDF** | DOCX, TXT, PDF (Merge) | Reconstrução estrutural para DOCX, fusão e reordenação de múltiplos PDFs. |

---

## 5. CONCLUSÃO

O **SecFC** representa uma solução completa, modular e altamente segura para conversão e manipulação local de arquivos. Seu design desacoplado facilita a manutenção e inclusão de novos formatos, mantendo a premissa fundamental de consumo zero de disco rígido e máxima eficiência operacional.