import io
import csv
import html
import chardet
from typing import Tuple, Optional
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def detect_file_encoding(file_bytes: bytes) -> str:
    """Detecta a codificação lendo os primeiros 10KB."""
    result = chardet.detect(file_bytes[:10000])
    return result.get('encoding') or 'utf-8'


def detect_csv_delimiter(sample_text: str) -> str:
    """Detecta o delimitador CSV por análise estatística/sniffer."""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text)
        return dialect.delimiter
    except Exception:
        # Fallback por verificação de ocorrências
        counts = {
            ";": sample_text.count(";"),
            "\t": sample_text.count("\t"),
            "|": sample_text.count("|"),
            ",": sample_text.count(",")
        }
        return max(counts, key=counts.get)


def convert_sheet(
    file_bytes: bytes, 
    source_ext: str, 
    target_format: str = "XLSX",
    delimiter: Optional[str] = None, 
    encoding: Optional[str] = None
) -> Tuple[io.BytesIO, str, str, pd.DataFrame, str, str]:
    """
    Converte arquivos de planilhas (CSV, XLSX, XLS) para outros formatos (XLSX, CSV, PDF).
    
    Retorna:
        - output_buffer: io.BytesIO contendo os dados convertidos
        - output_format: formato do arquivo gerado ('xlsx', 'csv', 'pdf')
        - mime_type: MIME type correspondente
        - preview_df: Amostra (DataFrame) dos dados para exibição rápida na UI
        - detected_sep: Delimitador utilizado/detectado
        - detected_enc: Encoding utilizado/detectado
    """
    input_buffer = io.BytesIO(file_bytes)
    source_ext = source_ext.lower().replace(".", "")
    
    detected_enc = encoding or detect_file_encoding(file_bytes)
    detected_sep = delimiter
    
    # 1. Carregamento dos dados no Pandas
    if source_ext == "csv":
        if not detected_sep:
            sample_text = file_bytes[:5000].decode(detected_enc, errors="ignore")
            detected_sep = detect_csv_delimiter(sample_text)
        df = pd.read_csv(input_buffer, sep=detected_sep, encoding=detected_enc, low_memory=False)
    else:
        df = pd.read_excel(input_buffer)
        detected_sep = "N/A"
        
    output_format = target_format.lower()
    output_buffer = io.BytesIO()
    
    # 2. Conversão para o formato de destino
    if output_format == "xlsx":
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
            
    elif output_format == "csv":
        mime = "text/csv"
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        output_buffer.write(csv_bytes)
        
    elif output_format == "pdf":
        mime = "application/pdf"
        clean_df = df.fillna("")
        
        # Configurações de layout PDF (Paisagem A4)
        margin = 25
        page_width, page_height = landscape(A4)
        usable_width = page_width - (2 * margin)
        
        doc = SimpleDocTemplate(
            output_buffer, 
            pagesize=landscape(A4), 
            rightMargin=margin, 
            leftMargin=margin, 
            topMargin=margin, 
            bottomMargin=margin
        )
        
        styles = getSampleStyleSheet()
        
        # Estilos com quebra de linha ativada (wordWrap='CJK')
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.whitesmoke,
            alignment=0,
            wordWrap='CJK'
        )
        
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#222222'),
            alignment=0,
            wordWrap='CJK'
        )
        
        elements = []
        total_cols = len(clean_df.columns)
        
        # Define o número máximo de colunas por página para manter a boa visualização
        if total_cols <= 6:
            cols_per_page = total_cols
        elif total_cols <= 12:
            cols_per_page = 6
        else:
            cols_per_page = 8

        # Paginação por blocos de colunas
        for start_col in range(0, total_cols, cols_per_page):
            end_col = min(start_col + cols_per_page, total_cols)
            sub_df = clean_df.iloc[:, start_col:end_col]
            
            table_data = []
            
            # Cabeçalho do bloco
            header_row = [
                Paragraph(html.escape(str(col)), header_style) 
                for col in sub_df.columns
            ]
            table_data.append(header_row)
            
            # Linhas de dados do bloco
            for _, row in sub_df.iterrows():
                data_row = [
                    Paragraph(html.escape(str(val)), cell_style) 
                    for val in row
                ]
                table_data.append(data_row)
                
            num_sub_cols = len(sub_df.columns)
            col_widths = [usable_width / num_sub_cols] * num_sub_cols
            
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f538d')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f5f8')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0'))
            ]))
            
            elements.append(t)
            
            # Adiciona quebra de página se ainda existirem mais colunas para exibir
            if end_col < total_cols:
                elements.append(PageBreak())
                
        doc.build(elements)
        
    output_buffer.seek(0)
    
    # Amostra de prévia leve para retornar à interface gráfica
    preview_df = df.iloc[:100, :15]
    
    return output_buffer, output_format, mime, preview_df, detected_sep, detected_enc