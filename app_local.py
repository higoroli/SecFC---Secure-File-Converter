import io
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import pandas as pd
from PIL import Image
import webbrowser

from core.image_conversor import convert_image
from core.sheet_conversor import convert_sheet
from core.text_conversor import convert_text, generate_pdf_pages_images
from core.utils import AutoScrollableFrame, LanguageManager, convert_multi_images_to_pdf

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

LOCALES_PATH = BASE_DIR / "locales" / "pt_BR.json"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class SecureConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Inicializa o suporte a Drag & Drop nativo no motor Tkinter
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception:
            try:
                self.TkdndVersion = self.tk.call('package', 'require', 'tkinterdnd2')
            except Exception:
                pass

        self.lang = LanguageManager(LOCALES_PATH)
        self.t = self.lang.get

        self.title(self.t("app.title"))
        self.geometry("1120x820")

        # Maximiza a tela com delay de renderização para evitar o 'snapback' para o modo janela
        self.after(200, self._maximize_window)

    def _maximize_window(self):
        """Aplica o estado maximizado com segurança após o CustomTkinter inicializar."""
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        # 1. Configurar Ícone da Janela e Logo Proporcional
        logo_light_path = BASE_DIR / "assets" / "Logo_squad_lat.png"
        logo_dark_path = BASE_DIR / "assets" / "Logo_squad_lat_b.png"

        icon_ico_path = BASE_DIR / "assets" / "app_icon.ico"
        icon_png_path = BASE_DIR / "assets" / "app_icon.png"
        
        # Define os caminhos de instância para alternar a imagem no cabeçalho
        self.logo_light_path = logo_light_path
        self.logo_dark_path = logo_dark_path

        if icon_ico_path.exists():
            try:
                # Método nativo do Windows para definir ícone da barra de título a partir do .ico
                self.iconbitmap(str(icon_ico_path))
            except Exception:
                pass
        elif icon_png_path.exists():
            try:
                img_obj = Image.open(icon_png_path)
                photo = ctk.CTkImage(light_image=img_obj, dark_image=img_obj)
                self.iconphoto(False, photo._light_image)
            except Exception:
                pass

        # 2. Inicialização do Menu de Contexto Superior (Exibição -> Tema)
        self.setup_menu()

        self.selected_files = []
        self.current_preview_index = 0
        
        self.converted_buffer = None
        self.file_type = None
        self.source_ext = None
        self.is_pdf_merge_mode = False

        self.preview_pages = []
        self.current_page_idx = 0
        self.zoom_level = 1.0
        
        self._update_job = None
        self._is_processing = False

        # Header Frame (Cabeçalho da aplicação)
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(15, 10))

        # Adiciona a Logo ao lado do Título Principal com suporte a Tema Claro e Escuro
        if self.logo_light_path.exists() and self.logo_dark_path.exists():
            pil_logo_light = Image.open(self.logo_light_path)
            pil_logo_dark = Image.open(self.logo_dark_path)

            ctk_logo_header = ctk.CTkImage(
                light_image=pil_logo_light, 
                dark_image=pil_logo_dark, 
                size=(158, 49)
            )
            self.lbl_logo_header = ctk.CTkLabel(self.header_frame, image=ctk_logo_header, text="")
            self.lbl_logo_header.pack(side="left", padx=(0, 10))
        elif self.logo_dark_path.exists():
            pil_logo = Image.open(self.logo_dark_path)
            ctk_logo_header = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(158, 49))
            self.lbl_logo_header = ctk.CTkLabel(self.header_frame, image=ctk_logo_header, text="")
            self.lbl_logo_header.pack(side="left", padx=(0, 10))

        self.lbl_title = ctk.CTkLabel(
            self.header_frame, 
            text=self.t("app.header_title"), 
            font=("Arial", 20, "bold"),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_title.pack(side="left", padx=5)

        self.btn_open_top = ctk.CTkButton(
            self.header_frame, text=self.t("buttons.open_file"), font=("Arial", 13, "bold"),
            command=self.open_file_dialog, fg_color="#1f538d", hover_color="#14375e"
        )

        self.lbl_privacy = ctk.CTkLabel(
            self.header_frame, text=self.t("app.privacy_notice"), 
            font=("Arial", 12), text_color=("gray40", "#a0a0a0")
        )
        self.lbl_privacy.pack(side="right", padx=5)

        # Container Principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)

        self.setup_settings_panel()
        self.setup_preview_panel()
        self.show_initial_state()

    def setup_menu(self):
        """Cria e estiliza a barra de menu no topo da janela principal."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        fg_color = "#ffffff" if is_dark else "#000000"
        active_bg = "#1f538d" if is_dark else "#14375e"
        active_fg = "#ffffff"

        # 1. Menu Principal
        self.menubar = tk.Menu(
            self, 
            bg=bg_color, 
            fg=fg_color, 
            activebackground=active_bg, 
            activeforeground=active_fg,
            activeborderwidth=0,
            bd=0,
            relief="flat"
        )
        
        # 2. Submenu "Tema do Aplicativo"
        self.theme_menu = tk.Menu(
            self.menubar, 
            tearoff=0, 
            bg=bg_color, 
            fg=fg_color, 
            activebackground=active_bg, 
            activeforeground=active_fg,
            activeborderwidth=0,
            bd=0,
            relief="flat"
        )
        
        self.theme_menu.add_command(
            label=self.t("options.theme_dark"), 
            command=lambda: self.change_appearance_mode("Dark")
        )
        self.theme_menu.add_command(
            label=self.t("options.theme_light"), 
            command=lambda: self.change_appearance_mode("Light")
        )
        self.theme_menu.add_command(
            label=self.t("options.theme_system"), 
            command=lambda: self.change_appearance_mode("System")
        )

        # 3. Menu "Exibição"
        self.view_menu = tk.Menu(
            self.menubar, 
            tearoff=0, 
            bg=bg_color, 
            fg=fg_color, 
            activebackground=active_bg, 
            activeforeground=active_fg,
            activeborderwidth=0,
            bd=0,
            relief="flat"
        )
        self.view_menu.add_cascade(label=self.t("menu.theme"), menu=self.theme_menu)
        self.menubar.add_cascade(label=self.t("menu.view"), menu=self.view_menu)

        # 4. Novo Menu "Avaliação" com o botão "Feedback"
        self.rating_menu = tk.Menu(
            self.menubar, 
            tearoff=0, 
            bg=bg_color, 
            fg=fg_color, 
            activebackground=active_bg, 
            activeforeground=active_fg,
            activeborderwidth=0,
            bd=0,
            relief="flat"
        )
        
        feedback_url = "https://redcap.bp.org.br/surveys/?s=ND83LP4MMFK7P7KY"
                
        self.rating_menu.add_command(
            label=self.t("menu.feedback"),
            command=lambda: webbrowser.open(feedback_url)
        )
        
        self.menubar.add_cascade(label=self.t("menu.rating"), menu=self.rating_menu)

        # Aplica a barra de menu na janela principal
        self.config(menu=self.menubar)

        
    def change_appearance_mode(self, mode: str):
        """Altera o tema e recria as cores do menu no topo."""
        ctk.set_appearance_mode(mode)
        self.setup_menu()

    def on_quality_change(self, value: float):
        val = int(value)
        if hasattr(self, 'lbl_qual_val'):
            self.lbl_qual_val.configure(text=self.t("labels.quality_adjust", val=val))
        self.debounce_update_preview()

    def on_resolution_change(self, choice: str):
        if choice == self.t("options.res_custom"):
            self.custom_res_frame.pack(fill="x", padx=0, pady=(0, 10), after=self.res_option)
        else:
            self.custom_res_frame.pack_forget()
        self.debounce_update_preview()

    def debounce_update_preview(self, delay_ms: int = 300):
        if self._update_job:
            self.after_cancel(self._update_job)
        self._update_job = self.after(delay_ms, self.update_preview)

    def setup_settings_panel(self):
        self.panel_left = ctk.CTkFrame(self.main_container, width=340)
        self.panel_left.pack(side="left", fill="both", expand=False, padx=(0, 10), pady=0)
        self.panel_left.pack_propagate(False)

        self.settings_scroll_frame = AutoScrollableFrame(
            self.panel_left, fg_color="transparent", label_text=""
        )
        self.settings_scroll_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.lbl_section = ctk.CTkLabel(
            self.settings_scroll_frame, 
            text=self.t("labels.section_settings"), 
            font=("Arial", 15, "bold"),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_section.pack(anchor="w", padx=10, pady=(10, 10))

        # Tela Inicial
        self.initial_sidebar_frame = ctk.CTkFrame(self.settings_scroll_frame, fg_color="transparent")

        self.btn_open_sidebar = ctk.CTkButton(
            self.initial_sidebar_frame, text=self.t("buttons.open_file"), font=("Arial", 13, "bold"),
            height=38, command=self.open_file_dialog, fg_color="#1f538d", hover_color="#14375e"
        )
        self.btn_open_sidebar.pack(fill="x", expand=True, padx=10, pady=(5, 6))

        self.btn_merge_pdf_sidebar = ctk.CTkButton(
            self.initial_sidebar_frame, text=self.t("buttons.merge_pdf_sidebar"), font=("Arial", 13, "bold"),
            height=38, command=self.open_merge_pdf_dialog, fg_color="#2fa572", hover_color="#227b54"
        )
        self.btn_merge_pdf_sidebar.pack(fill="x", expand=True, padx=10, pady=(0, 15))

        self.lbl_obs_title = ctk.CTkLabel(
            self.initial_sidebar_frame,
            text=self.t("labels.obs_title"),
            font=("Arial", 14, "bold"),
            text_color=("#1e7e53", "#2fa572")
        )
        self.lbl_obs_title.pack(anchor="w", padx=10, pady=(0, 4))

        self.lbl_obs_desc = ctk.CTkLabel(
            self.initial_sidebar_frame,
            text=self.t("labels.obs_desc"),
            font=("Arial", 13),
            text_color=("gray25", "#d0d0d0"),
            wraplength=280,
            justify="left"
        )
        self.lbl_obs_desc.pack(anchor="w", padx=10, pady=(0, 12))

        self.card_formats = ctk.CTkFrame(
            self.initial_sidebar_frame, 
            fg_color=("gray88", "#25272a"), 
            corner_radius=8, 
            border_width=1, 
            border_color=("gray75", "#3a3d42")
        )
        self.card_formats.pack(fill="x", expand=True, padx=10, pady=(0, 10))

        icon_size = (22, 22)
        assets_dir = BASE_DIR / "assets"
        
        img_icon_path = assets_dir / "imagem.png"
        sheet_icon_path = assets_dir / "planilhas.png"
        text_icon_path = assets_dir / "texto.png"
        pdf_icon_path = assets_dir / "pdf.png"

        def load_icon(path):
            if path.exists():
                pil_img = Image.open(path)
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=icon_size)
            return None

        icon_img = load_icon(img_icon_path)
        icon_sheet = load_icon(sheet_icon_path)
        icon_text = load_icon(text_icon_path)
        icon_pdf = load_icon(pdf_icon_path)

        sections_data = [
            (icon_img, "labels.fmt_img_title", "labels.fmt_img_desc"),
            (icon_sheet, "labels.fmt_sheet_title", "labels.fmt_sheet_desc"),
            (icon_text, "labels.fmt_text_title", "labels.fmt_text_desc"),
            (icon_pdf, "labels.fmt_pdf_merge_title", "labels.fmt_pdf_merge_desc"),
        ]

        for idx, (icon, title_key, desc_key) in enumerate(sections_data):
            sec_frame = ctk.CTkFrame(self.card_formats, fg_color="transparent")
            top_pad = 10 if idx == 0 else 6
            bottom_pad = 10 if idx == len(sections_data) - 1 else 0
            
            sec_frame.pack(fill="x", padx=12, pady=(top_pad, bottom_pad))

            header_sub = ctk.CTkFrame(sec_frame, fg_color="transparent")
            header_sub.pack(anchor="w", fill="x")

            if icon:
                lbl_ico = ctk.CTkLabel(header_sub, image=icon, text="")
                lbl_ico.pack(side="left", padx=(0, 6))

            lbl_title = ctk.CTkLabel(
                header_sub, 
                text=self.t(title_key), 
                font=("Arial", 13, "bold"), 
                text_color=("gray10", "#f0f0f0")
            )
            lbl_title.pack(side="left")

            lbl_desc = ctk.CTkLabel(
                sec_frame, 
                text=self.t(desc_key), 
                font=("Arial", 12), 
                text_color=("gray25", "#d0d0d0"), 
                justify="left"
            )
            lbl_desc.pack(anchor="w", padx=(28 if icon else 0, 0), pady=(2, 0))

        # Controles - Imagens
        self.image_controls_frame = ctk.CTkFrame(self.settings_scroll_frame, fg_color="transparent")
        self.lbl_res = ctk.CTkLabel(
            self.image_controls_frame, 
            text=self.t("labels.img_res"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_res.pack(anchor="w", padx=0, pady=(5, 2))
        
        self.res_option = ctk.CTkOptionMenu(
            self.image_controls_frame,
            values=[
                self.t("options.res_original"),
                self.t("options.res_option_fhd"),
                self.t("options.res_option_4k"),
                self.t("options.res_option_hd"),
                self.t("options.res_custom")
            ],
            command=self.on_resolution_change
        )
        self.res_option.pack(fill="x", expand=True, padx=0, pady=(0, 10))
        
        self.custom_res_frame = ctk.CTkFrame(self.image_controls_frame, fg_color="transparent")
        self.entry_width = ctk.CTkEntry(self.custom_res_frame, placeholder_text=self.t("placeholders.width_px"), width=120)
        self.entry_width.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.entry_width.bind("<KeyRelease>", lambda e: self.debounce_update_preview())
        
        self.entry_height = ctk.CTkEntry(self.custom_res_frame, placeholder_text=self.t("placeholders.height_px"), width=120)
        self.entry_height.pack(side="right", expand=True, fill="x", padx=(5, 0))
        self.entry_height.bind("<KeyRelease>", lambda e: self.debounce_update_preview())

        self.lbl_qual = ctk.CTkLabel(
            self.image_controls_frame, 
            text=self.t("labels.img_quality"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_qual.pack(anchor="w", padx=0, pady=(5, 2))
        self.slider_quality = ctk.CTkSlider(self.image_controls_frame, from_=10, to=100, number_of_steps=90, command=self.on_quality_change)
        self.slider_quality.set(85)
        self.slider_quality.pack(fill="x", expand=True, padx=0, pady=2)
        self.lbl_qual_val = ctk.CTkLabel(
            self.image_controls_frame, 
            text=self.t("labels.quality_high", val=85), 
            font=("Arial", 12, "bold"), 
            text_color=("#1e7e53", "#2fa572")
        )
        self.lbl_qual_val.pack(anchor="center", pady=(0, 10))

        self.lbl_fmt = ctk.CTkLabel(
            self.image_controls_frame, 
            text=self.t("labels.img_fmt"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_fmt.pack(anchor="w", padx=0, pady=(5, 2))
        self.segmented_fmt = ctk.CTkSegmentedButton(self.image_controls_frame, values=["JPEG", "PNG", "WEBP", "PDF"], command=lambda f: self.debounce_update_preview())
        self.segmented_fmt.set("JPEG")
        self.segmented_fmt.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        # Controles - Planilhas
        self.sheet_controls_frame = ctk.CTkFrame(self.settings_scroll_frame, fg_color="transparent")
        self.lbl_sep = ctk.CTkLabel(
            self.sheet_controls_frame, 
            text=self.t("labels.sheet_sep"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_sep.pack(anchor="w", padx=0, pady=(5, 2))
        self.opt_delimiter = ctk.CTkOptionMenu(
            self.sheet_controls_frame,
            values=[
                self.t("options.auto_detect"),
                self.t("options.sep_comma"),
                self.t("options.sep_semicolon"),
                self.t("options.sep_tab"),
                self.t("options.sep_pipe")
            ],
            command=lambda f: self.debounce_update_preview()
        )
        self.opt_delimiter.set(self.t("options.auto_detect"))
        self.opt_delimiter.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        self.lbl_enc = ctk.CTkLabel(
            self.sheet_controls_frame, 
            text=self.t("labels.sheet_enc"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_enc.pack(anchor="w", padx=0, pady=(5, 2))
        self.opt_encoding = ctk.CTkOptionMenu(
            self.sheet_controls_frame,
            values=[self.t("options.auto_detect"), "utf-8", "latin-1", "iso-8859-1", "cp1252"],
            command=lambda f: self.debounce_update_preview()
        )
        self.opt_encoding.set(self.t("options.auto_detect"))
        self.opt_encoding.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        self.lbl_sheet_fmt = ctk.CTkLabel(
            self.sheet_controls_frame, 
            text=self.t("labels.sheet_fmt"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_sheet_fmt.pack(anchor="w", padx=0, pady=(5, 2))
        self.segmented_sheet_fmt = ctk.CTkSegmentedButton(self.sheet_controls_frame, values=["XLSX", "CSV", "PDF"], command=lambda f: self.debounce_update_preview())
        self.segmented_sheet_fmt.set("XLSX")
        self.segmented_sheet_fmt.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        # Controles - Texto
        self.text_controls_frame = ctk.CTkFrame(self.settings_scroll_frame, fg_color="transparent")
        self.lbl_text_enc = ctk.CTkLabel(
            self.text_controls_frame, 
            text=self.t("labels.text_enc"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_text_enc.pack(anchor="w", padx=0, pady=(5, 2))
        self.opt_text_encoding = ctk.CTkOptionMenu(
            self.text_controls_frame,
            values=[self.t("options.auto_detect"), "utf-8", "latin-1", "iso-8859-1", "cp1252"],
            command=lambda f: self.debounce_update_preview()
        )
        self.opt_text_encoding.set(self.t("options.auto_detect"))
        self.opt_text_encoding.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        self.lbl_text_fmt = ctk.CTkLabel(
            self.text_controls_frame, 
            text=self.t("labels.text_fmt"), 
            font=("Arial", 12),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_text_fmt.pack(anchor="w", padx=0, pady=(5, 2))
        self.segmented_text_fmt = ctk.CTkSegmentedButton(self.text_controls_frame, values=["PDF", "DOCX", "TXT"], command=lambda f: self.debounce_update_preview())
        self.segmented_text_fmt.set("PDF")
        self.segmented_text_fmt.pack(fill="x", expand=True, padx=0, pady=(0, 10))

        # Multi-Seleção e Junção
        self.multi_file_frame = ctk.CTkFrame(
            self.settings_scroll_frame, 
            fg_color=("gray88", "#202225"), 
            corner_radius=8
        )
        
        self.btn_multi_select = ctk.CTkButton(
            self.multi_file_frame, text=self.t("buttons.multi_select"), font=("Arial", 12, "bold"),
            fg_color="#2fa572", hover_color="#227b54", height=32, command=self.add_additional_files
        )
        self.btn_multi_select.pack(fill="x", expand=True, padx=10, pady=(10, 5))

        self.scroll_file_list = AutoScrollableFrame(
            self.multi_file_frame, 
            height=130, 
            fg_color=("gray92", "#18191c")
        )
        self.scroll_file_list.pack(fill="both", expand=True, pady=(5, 5))

        self.switch_merge = ctk.CTkSwitch(
            self.multi_file_frame, 
            text=self.t("labels.merge_switch"), 
            font=("Arial", 12, "bold"),
            progress_color="#2fa572", 
            text_color=("gray10", "#ffffff"),
            command=self.debounce_update_preview
        )
        self.switch_merge.pack(anchor="w", padx=12, pady=(8, 10))

        # ÁREA INFERIOR FIXA
        self.action_frame = ctk.CTkFrame(self.panel_left, fg_color="transparent")
        
        self.lbl_status = ctk.CTkLabel(
            self.action_frame, 
            text="", 
            font=("Arial", 11), 
            text_color=("#1e7e53", "#2fa572"), 
            wraplength=300
        )
        self.progress_bar = ctk.CTkProgressBar(self.action_frame, height=8)
        self.progress_bar.set(0)

        self.lbl_status.pack_forget()
        self.progress_bar.pack_forget()

        self.btn_convert = ctk.CTkButton(
            self.action_frame, text=self.t("buttons.convert_file"), font=("Arial", 14, "bold"), height=36, command=self.process_conversion
        )
        self.btn_convert.pack(fill="x", expand=True, pady=(0, 6))

        self.btn_save = ctk.CTkButton(
            self.action_frame, text=self.t("buttons.save_file"), font=("Arial", 14, "bold"), height=36, fg_color="#2fa572", hover_color="#227b54", state="disabled", command=self.save_converted_file
        )
        self.btn_save.pack(fill="x", expand=True, pady=(0, 6))

        self.btn_cancel = ctk.CTkButton(
            self.action_frame, text=self.t("buttons.cancel"), font=("Arial", 13, "bold"), height=32, fg_color="#c93b2b", hover_color="#a12b1e", command=self.cancel_process
        )
        self.btn_cancel.pack(fill="x", expand=True)

        self.lbl_credits = ctk.CTkLabel(
            self.panel_left,
            text=self.t("app.credits"),
            font=("Arial", 11),
            text_color=("gray35", "#7a7a7a")
        )
        self.lbl_credits.pack(side="bottom", pady=(5, 10))

    def convert_multi_images_to_pdf(self, file_list, target_res=None, quality=85):
        """Wrapper local que delega o processamento de PDF para a função desacoplada no utils.py."""
        return convert_multi_images_to_pdf(
            file_list, 
            target_res=target_res, 
            quality=quality, 
        )

    def open_merge_pdf_dialog(self):
        file_paths = filedialog.askopenfilenames(
            filetypes=[(self.t("options.filetype_pdf_files"), "*.pdf")]
        )
        if not file_paths:
            return

        self.selected_files = []
        for path_str in file_paths:
            path = Path(path_str)
            try:
                filename = path.name
                with open(path, "rb") as f:
                    content = f.read()
                self.selected_files.append({
                    'name': filename,
                    'bytes': content,
                    'path': str(path)
                })
            except Exception as e:
                messagebox.showerror(
                    self.t("messages.read_error_title"),
                    self.t("messages.read_error_body", path=str(path), err=str(e))
                )

        if not self.selected_files:
            return

        self.is_pdf_merge_mode = True
        self.file_type = "text"
        self.source_ext = "pdf"
        self.segmented_text_fmt.set("PDF")

        self.show_active_state()
        self.switch_merge.select()
        self.hide_progress()
        self.update_preview()

    def setup_preview_panel(self):
        self.panel_right = ctk.CTkFrame(self.panel_right if hasattr(self, 'panel_right') else self.main_container)
        self.panel_right.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        self.preview_header = ctk.CTkFrame(self.panel_right, fg_color="transparent")
        self.preview_header.pack(fill="x", padx=15, pady=(15, 5))

        lbl_prev_title = ctk.CTkLabel(
            self.preview_header, 
            text=self.t("labels.preview_title"), 
            font=("Arial", 15, "bold"),
            text_color=("gray10", "#ffffff")
        )
        lbl_prev_title.pack(side="left")

        self.lbl_info = ctk.CTkLabel(
            self.preview_header, 
            text=self.t("labels.no_file_loaded"), 
            font=("Arial", 11), 
            text_color=("gray40", "#a0a0a0")
        )
        self.lbl_info.pack(side="right")

        self.preview_image_box = ctk.CTkLabel(
            self.panel_right, 
            text=self.t("labels.click_open_start"), 
            font=("Arial", 13),
            text_color=("gray30", "#d0d0d0")
        )
        self.preview_image_box.pack(fill="both", expand=True, padx=15, pady=15)

        # Registo do evento de Drag and Drop
        self.preview_image_box.drop_target_register(DND_FILES)
        self.preview_image_box.dnd_bind('<<Drop>>', self.on_file_drop)

        self.text_preview_frame = ctk.CTkFrame(self.panel_right, fg_color="transparent")

        self.toolbar_frame = ctk.CTkFrame(self.text_preview_frame, fg_color="transparent")
        self.toolbar_frame.pack(fill="x", pady=(0, 5))

        self.btn_prev_page = ctk.CTkButton(self.toolbar_frame, text=self.t("buttons.prev_page"), width=85, height=28, command=self.prev_page)
        self.btn_prev_page.pack(side="left", padx=(5, 2))

        self.lbl_page_count = ctk.CTkLabel(
            self.toolbar_frame, 
            text=self.t("labels.page_info", current=1, total=1), 
            font=("Arial", 12, "bold"),
            text_color=("gray10", "#ffffff")
        )
        self.lbl_page_count.pack(side="left", padx=10)

        self.btn_next_page = ctk.CTkButton(self.toolbar_frame, text=self.t("buttons.next_page"), width=85, height=28, command=self.next_page)
        self.btn_next_page.pack(side="left", padx=(2, 15))

        self.btn_zoom_out = ctk.CTkButton(self.toolbar_frame, text=self.t("buttons.zoom_out"), width=65, height=28, command=self.zoom_out)
        self.btn_zoom_out.pack(side="right", padx=3)

        self.lbl_zoom_val = ctk.CTkLabel(
            self.toolbar_frame, 
            text="100%", 
            font=("Arial", 12, "bold"), 
            width=50,
            text_color=("gray10", "#ffffff")
        )
        self.lbl_zoom_val.pack(side="right", padx=3)

        self.btn_zoom_in = ctk.CTkButton(self.toolbar_frame, text=self.t("buttons.zoom_in"), width=65, height=28, command=self.zoom_in)
        self.btn_zoom_in.pack(side="right", padx=3)

        self.btn_zoom_reset = ctk.CTkButton(self.toolbar_frame, text=self.t("buttons.zoom_reset"), width=55, height=28, fg_color="#444444", hover_color="#555555", command=self.zoom_reset)
        self.btn_zoom_reset.pack(side="right", padx=(0, 5))

        self.scroll_page = AutoScrollableFrame(
            self.text_preview_frame, 
            fg_color=("gray90", "#1a1a1a")
        )
        self.scroll_page.pack(fill="both", expand=True)

        if hasattr(self.scroll_page, "_parent_canvas"):
            self.scroll_page._parent_canvas.bind(
                "<Configure>",
                lambda e: self.scroll_page._parent_canvas.itemconfigure(
                    "all", width=e.width
                ) if self.scroll_page._parent_canvas.find_withtag("all") else None
            )

        self.lbl_page_image = ctk.CTkLabel(self.scroll_page, text="")
        self.lbl_page_image.pack(anchor="center", expand=True, pady=15)

        self.scroll_page.bind_all("<Control-MouseWheel>", self.on_ctrl_wheel)

        self.table_frame = ctk.CTkFrame(self.panel_right, fg_color="transparent")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=25)
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Arial", 10, "bold"))

        self.tree = ttk.Treeview(self.table_frame, show="headings")
        self.scrollbar_y = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.scrollbar_x = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def on_file_drop(self, event):
        """Callback acionado quando um ficheiro é arrastado e solto na prévia."""
        file_path_raw = event.data.strip()
        
        # Trata caminhos contendo espaços entre chaves no Windows
        if file_path_raw.startswith('{') and file_path_raw.endswith('}'):
            file_path_raw = file_path_raw[1:-1]
            
        file_path = Path(file_path_raw)
        
        if not file_path.exists() or not file_path.is_file():
            return

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            messagebox.showerror(
                self.t("messages.read_error_title"),
                self.t("messages.read_error_disk", err=str(e))
            )
            return

        filename = file_path.name
        ext = file_path.suffix.lstrip(".").lower()
        
        allowed_exts = ["png", "jpg", "jpeg", "webp", "csv", "xlsx", "docx", "txt", "pdf"]
        if ext not in allowed_exts:
            messagebox.showwarning("Formato não suportado", f"O formato .{ext} não é suportado pelo SecFC.")
            return

        self.source_ext = ext
        self.is_pdf_merge_mode = False

        self.selected_files = [{
            'name': filename,
            'bytes': file_bytes,
            'path': str(file_path)
        }]

        if ext in ["csv", "xlsx"]:
            self.file_type = "sheet"
            self.segmented_sheet_fmt.set("XLSX" if ext == "csv" else "CSV")
        elif ext in ["docx", "txt", "pdf"]:
            self.file_type = "text"
            if ext == "pdf":
                self.segmented_text_fmt.set("DOCX")
            else:
                self.segmented_text_fmt.set("PDF")
        else:
            self.file_type = "image"

        self.show_active_state()
        self.hide_progress()
        self.update_preview()

    def add_additional_files(self):
        if not self.file_type or self.file_type == "sheet":
            return

        if self.is_pdf_merge_mode:
            filetypes = [(self.t("options.filetype_pdf_files"), "*.pdf")]
        elif self.file_type == "text":
            filetypes = [(self.t("options.filetype_text_docs"), "*.docx *.txt *.pdf")]
        elif self.file_type == "image":
            filetypes = [(self.t("options.filetype_images"), "*.png *.jpg *.jpeg *.webp")]

        paths = filedialog.askopenfilenames(filetypes=filetypes)
        if not paths:
            return

        for path_str in paths:
            path = Path(path_str)
            try:
                filename = path.name
                if not any(f['path'] == str(path) for f in self.selected_files):
                    with open(path, "rb") as f:
                        content = f.read()
                    self.selected_files.append({
                        'name': filename,
                        'bytes': content,
                        'path': str(path)
                    })
            except Exception as e:
                messagebox.showerror(
                    self.t("messages.read_error_title"),
                    self.t("messages.read_error_body", path=str(path), err=str(e))
                )

        self.refresh_file_list_ui()
        self.debounce_update_preview()

    def move_file_up(self, idx):
        if idx > 0:
            self.selected_files[idx], self.selected_files[idx - 1] = self.selected_files[idx - 1], self.selected_files[idx]
            self.refresh_file_list_ui()
            self.debounce_update_preview()

    def move_file_down(self, idx):
        if idx < len(self.selected_files) - 1:
            self.selected_files[idx], self.selected_files[idx + 1] = self.selected_files[idx + 1], self.selected_files[idx]
            self.refresh_file_list_ui()
            self.debounce_update_preview()

    def remove_file(self, idx):
        if len(self.selected_files) <= 1:
            messagebox.showwarning(
                self.t("messages.file_remove_warning_title"),
                self.t("messages.file_remove_warning_body")
            )
            return
        self.selected_files.pop(idx)
        self.refresh_file_list_ui()
        self.debounce_update_preview()

    def refresh_file_list_ui(self):
        for widget in self.scroll_file_list.winfo_children():
            widget.destroy()

        if hasattr(self.scroll_file_list, "grid_columnconfigure"):
            self.scroll_file_list.grid_columnconfigure(0, weight=1)

        self.scroll_file_list.update_idletasks()
        container_width = self.scroll_file_list.winfo_width()

        for idx, file_info in enumerate(self.selected_files):
            item_frame = ctk.CTkFrame(
                self.scroll_file_list, 
                fg_color=("gray85", "#2b2d31"), 
                height=28
            )
            
            if container_width > 50:
                item_frame.configure(width=container_width - 15)

            item_frame.pack(fill="x", expand=True, pady=2, padx=4)

            raw_name = file_info['name']
            display_name = raw_name if len(raw_name) <= 35 else raw_name[:32] + "..."

            lbl_name = ctk.CTkLabel(
                item_frame, 
                text=display_name, 
                font=("Arial", 11),
                anchor="w",
                text_color=("gray10", "#ffffff")
            )
            lbl_name.pack(side="left", padx=5, fill="x", expand=True)

            btn_up = ctk.CTkButton(
                item_frame, text="▲", width=22, height=22, font=("Arial", 9),
                fg_color=("gray75", "#3a3d42"), hover_color=("gray65", "#4f535a"), 
                command=lambda i=idx: self.move_file_up(i)
            )
            btn_up.pack(side="left", padx=1)

            btn_down = ctk.CTkButton(
                item_frame, text="▼", width=22, height=22, font=("Arial", 9),
                fg_color=("gray75", "#3a3d42"), hover_color=("gray65", "#4f535a"), 
                command=lambda i=idx: self.move_file_down(i)
            )
            btn_down.pack(side="left", padx=1)

            btn_del = ctk.CTkButton(
                item_frame, text="✕", width=22, height=22, font=("Arial", 9, "bold"),
                fg_color="#c93b2b", hover_color="#a12b1e", command=lambda i=idx: self.remove_file(i)
            )
            btn_del.pack(side="left", padx=(1, 5))

        if hasattr(self.scroll_file_list, "_check_scrollbar"):
            self.scroll_file_list._check_scrollbar()

    def on_ctrl_wheel(self, event):
        if (self.file_type == "text" or (self.file_type == "image" and self.segmented_fmt.get() == "PDF")) and self.preview_pages:
            delta = getattr(event, 'delta', 0)
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()

    def zoom_in(self):
        if self.zoom_level < 2.5:
            self.zoom_level += 0.15
            self.render_current_page()

    def zoom_out(self):
        if self.zoom_level > 0.4:
            self.zoom_level -= 0.15
            self.render_current_page()

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.render_current_page()

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.render_current_page()

    def next_page(self):
        if self.current_page_idx < len(self.preview_pages) - 1:
            self.current_page_idx += 1
            self.render_current_page()

    def render_current_page(self):
        if not self.preview_pages:
            return

        total_pages = len(self.preview_pages)
        self.lbl_page_count.configure(text=self.t("labels.page_info", current=self.current_page_idx + 1, total=total_pages))
        self.lbl_zoom_val.configure(text=f"{int(self.zoom_level * 100)}%")

        self.btn_prev_page.configure(state="normal" if self.current_page_idx > 0 else "disabled")
        self.btn_next_page.configure(state="normal" if self.current_page_idx < total_pages - 1 else "disabled")

        img = self.preview_pages[self.current_page_idx].copy()

        base_width, base_height = 540, 750
        target_width = int(base_width * self.zoom_level)
        target_height = int(base_height * self.zoom_level)

        img.thumbnail((target_width, target_height))

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.lbl_page_image.configure(image=ctk_img, text="")
        
        self.lbl_page_image.pack(anchor="center", expand=True, pady=15)
        self.scroll_page._check_scrollbar()

    def show_initial_state(self):
        self.selected_files = []
        self.converted_buffer = None
        self.file_type = None
        self.source_ext = None
        self.is_pdf_merge_mode = False
        self.preview_pages = []
        self.current_page_idx = 0
        self.zoom_level = 1.0

        self.btn_open_top.pack_forget()
        self.image_controls_frame.pack_forget()
        self.custom_res_frame.pack_forget()
        self.sheet_controls_frame.pack_forget()
        self.text_controls_frame.pack_forget()
        self.multi_file_frame.pack_forget()
        self.action_frame.pack_forget()
        self.table_frame.pack_forget()
        self.text_preview_frame.pack_forget()

        self.tree.delete(*self.tree.get_children())
        self.preview_image_box.configure(image="", text=self.t("labels.click_open_start"))
        self.preview_image_box.pack(fill="both", expand=True, padx=15, pady=15)
        self.lbl_info.configure(text=self.t("labels.no_file_loaded"))

        self.btn_convert.configure(text=self.t("buttons.convert_file"))
        self.btn_save.configure(state="disabled")
        self.hide_progress()
        self.initial_sidebar_frame.pack(fill="x", anchor="n", padx=0, pady=0)

    def show_active_state(self):
        self.initial_sidebar_frame.pack_forget()
        
        self.image_controls_frame.pack_forget()
        self.custom_res_frame.pack_forget()
        self.sheet_controls_frame.pack_forget()
        self.text_controls_frame.pack_forget()
        self.multi_file_frame.pack_forget()

        # O título do cabeçalho da barra lateral fica sempre fixado como "Configurações"
        self.lbl_section.configure(text=self.t("labels.section_settings"))

        if self.is_pdf_merge_mode:
            self.btn_open_top.pack_forget()
            self.btn_convert.configure(text=self.t("buttons.merge_pdf"))
            self.multi_file_frame.pack(fill="x", expand=True, padx=10, pady=(10, 15))
        else:
            self.btn_open_top.pack(side="left", padx=20, after=self.lbl_title)
            self.btn_convert.configure(text=self.t("buttons.convert_file"))
            if self.file_type == "image":
                self.image_controls_frame.pack(fill="x", expand=True, padx=10, pady=0)
                if self.res_option.get() == self.t("options.res_custom"):
                    self.custom_res_frame.pack(fill="x", padx=0, pady=(0, 10), after=self.res_option)
                self.multi_file_frame.pack(fill="x", expand=True, padx=10, pady=(10, 15))
            elif self.file_type == "sheet":
                self.sheet_controls_frame.pack(fill="x", expand=True, padx=10, pady=0)
                self.multi_file_frame.pack_forget()
            elif self.file_type == "text":
                self.text_controls_frame.pack(fill="x", expand=True, padx=10, pady=0)
                self.multi_file_frame.pack(fill="x", expand=True, padx=10, pady=(10, 15))

        self.action_frame.pack(side="bottom", fill="x", padx=10, pady=15)
        self.refresh_file_list_ui()
        self.hide_progress()

    def cancel_process(self):
        self.show_initial_state()

    def open_file_dialog(self):
        file_path_str = filedialog.askopenfilename(
            filetypes=[
                (self.t("options.filetype_all"), "*.png *.jpg *.jpeg *.webp *.csv *.xlsx *.docx *.txt *.pdf"),
                (self.t("options.filetype_images"), "*.png *.jpg *.jpeg *.webp"),
                (self.t("options.filetype_sheets"), "*.csv *.xlsx"),
                (self.t("options.filetype_text_docs"), "*.docx *.txt *.pdf")
            ]
        )
        if not file_path_str:
            return

        file_path = Path(file_path_str)
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            messagebox.showerror(
                self.t("messages.read_error_title"),
                self.t("messages.read_error_disk", err=str(e))
            )
            return

        filename = file_path.name
        ext = file_path.suffix.lstrip(".").lower()
        self.source_ext = ext
        self.is_pdf_merge_mode = False

        self.selected_files = [{
            'name': filename,
            'bytes': file_bytes,
            'path': str(file_path)
        }]

        if ext in ["csv", "xlsx"]:
            self.file_type = "sheet"
            self.segmented_sheet_fmt.set("XLSX" if ext == "csv" else "CSV")
        elif ext in ["docx", "txt", "pdf"]:
            self.file_type = "text"
            if ext == "pdf":
                self.segmented_text_fmt.set("DOCX")
            else:
                self.segmented_text_fmt.set("PDF")
        else:
            self.file_type = "image"

        self.show_active_state()
        self.hide_progress()
        self.update_preview()

    def hide_progress(self):
        self.lbl_status.configure(text="")
        self.lbl_status.pack_forget()
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()
        self.converted_buffer = None
        self.btn_save.configure(state="disabled")

    def show_progress(self):
        self.lbl_status.pack(fill="x", pady=(0, 2), before=self.btn_convert)
        self.progress_bar.pack(fill="x", pady=(0, 6), before=self.btn_convert)
        self.lbl_status.configure(text=self.t("labels.status_converting_ram"), text_color="#1f538d")
        self.progress_bar.set(0.1)

    def get_selected_delimiter(self):
        val = self.opt_delimiter.get()
        mapping = {
            self.t("options.sep_comma"): ",",
            self.t("options.sep_semicolon"): ";",
            self.t("options.sep_tab"): "\t",
            self.t("options.sep_pipe"): "|"
        }
        return mapping.get(val, None)

    def get_selected_encoding(self, widget):
        val = widget.get()
        return None if val == self.t("options.auto_detect") else val

    def get_target_resolution(self):
        selected = self.res_option.get()
        res_map = {
            self.t("options.res_option_fhd"): (1920, 1080),
            self.t("options.res_option_4k"): (3840, 2160),
            self.t("options.res_option_hd"): (1280, 720)
        }
        if selected in res_map:
            return res_map[selected]
        elif selected == self.t("options.res_custom"):
            try:
                w = int(self.entry_width.get().strip())
                h = int(self.entry_height.get().strip())
                if w > 0 and h > 0:
                    return (w, h)
            except ValueError:
                pass
        return None

    def update_preview(self, *args):
        if not self.selected_files or self._is_processing:
            return

        self._is_processing = True
        self.lbl_info.configure(text=self.t("labels.loading_preview"))
        threading.Thread(target=self._update_preview_thread, daemon=True).start()

    def _update_preview_thread(self):
        try:
            if not self.selected_files:
                return

            merge_files = bool(self.switch_merge.get()) if self.file_type != "sheet" else False
            files_to_process = self.selected_files if merge_files else [self.selected_files[0]]

            if self.file_type == "image":
                target_fmt = self.segmented_fmt.get()
                quality = int(self.slider_quality.get())
                target_res = self.get_target_resolution()

                if target_fmt == "PDF" and len(files_to_process) >= 1:
                    pdf_buf, pil_imgs = self.convert_multi_images_to_pdf(
                        files_to_process, target_res=target_res, quality=quality
                    )
                    size_mb = len(pdf_buf.getvalue()) / (1024 * 1024)
                    info_text = self.t("labels.info_images_pdf", count=len(pil_imgs), size=size_mb)
                    self.after(0, self._render_text_preview, pil_imgs, info_text)
                else:
                    input_data = bytes(files_to_process[0]['bytes'])
                    try:
                        out_buffer, mime, img_post = convert_image(
                            input_data, target_format=target_fmt, quality=quality, resolution=target_res
                        )
                    except TypeError:
                        out_buffer, mime, img_post = convert_image(
                            input_data, target_format=target_fmt, quality=quality
                        )

                    size_mb = len(out_buffer.getvalue()) / (1024 * 1024)
                    info_text = self.t(
                        "labels.info_image_single", 
                        width=img_post.size[0], 
                        height=img_post.size[1], 
                        quality=quality, 
                        size=size_mb
                    )

                    display_img = img_post.copy()
                    display_img.thumbnail((550, 380))

                    self.after(0, self._render_image_preview, display_img, info_text)

            elif self.file_type == "sheet":
                sep = self.get_selected_delimiter()
                enc = self.get_selected_encoding(self.opt_encoding)
                target_sheet_fmt = self.segmented_sheet_fmt.get()
                input_data = bytes(files_to_process[0]['bytes'])
                src_ext = Path(files_to_process[0]['name']).suffix.lstrip(".").lower()

                out_buffer, out_ext, _, df_post, used_sep, used_enc = convert_sheet(
                    input_data, src_ext, target_format=target_sheet_fmt, delimiter=sep, encoding=enc
                )

                sep_display = repr(used_sep) if used_sep in ["\t", ";", ",", "|"] else used_sep
                info_text = self.t(
                    "labels.info_sheet", 
                    ext=out_ext.upper(), 
                    enc=used_enc, 
                    sep=sep_display, 
                    rows=len(df_post), 
                    cols=len(df_post.columns)
                )

                self.after(0, self._render_sheet_preview, df_post, info_text)

            elif self.file_type == "text":
                enc = None if self.is_pdf_merge_mode else self.get_selected_encoding(self.opt_text_encoding)
                target_text_fmt = "PDF" if self.is_pdf_merge_mode else self.segmented_text_fmt.get()

                all_preview_images = []
                total_bytes = 0
                used_enc_last = "N/A" if self.is_pdf_merge_mode else "utf-8"
                out_ext_last = target_text_fmt.lower()

                for f_info in files_to_process:
                    input_data = bytes(f_info['bytes'])
                    src_ext = Path(f_info['name']).suffix.lstrip(".").lower()

                    out_buf, out_ext_last, _, _, preview_images, used_enc_last = convert_text(
                        input_data, src_ext, target_format=target_text_fmt, encoding=enc
                    )
                    
                    if preview_images:
                        all_preview_images.extend(preview_images)
                    
                    if out_buf is not None:
                        total_bytes += len(out_buf.getvalue()) if hasattr(out_buf, "getvalue") else len(out_buf)

                size_mb = total_bytes / (1024 * 1024)
                if self.is_pdf_merge_mode:
                    info_text = self.t("labels.info_pdf_merge", count=len(files_to_process), size=size_mb)
                else:
                    info_text = self.t(
                        "labels.info_text_files", 
                        count=len(files_to_process), 
                        ext=out_ext_last.upper(), 
                        enc=used_enc_last, 
                        size=size_mb
                    )

                self.after(0, self._render_text_preview, all_preview_images, info_text)

        except Exception as e:
            err_text = str(e)
            self.after(0, self._render_error_preview, err_text)
        finally:
            self._is_processing = False

    def _render_error_preview(self, err_msg: str):
        self.lbl_info.configure(text=self.t("labels.preview_error"))
        self.preview_image_box.configure(image="", text=self.t("labels.preview_error_box", err=err_msg))
        self.table_frame.pack_forget()
        self.text_preview_frame.pack_forget()
        self.preview_image_box.pack(fill="both", expand=True, padx=15, pady=15)

    def _render_image_preview(self, display_img, info_text):
        self.table_frame.pack_forget()
        self.text_preview_frame.pack_forget()
        self.preview_image_box.pack(fill="both", expand=True, padx=15, pady=15)

        self.lbl_info.configure(text=info_text)
        ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=display_img.size)
        self.preview_image_box.configure(image=ctk_img, text="")

    def _render_sheet_preview(self, df_post, info_text):
        self.preview_image_box.pack_forget()
        self.text_preview_frame.pack_forget()
        self.table_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.lbl_info.configure(text=info_text)

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df_post.columns)

        for col in df_post.columns:
            col_str = str(col)
            max_len = len(col_str)
            if not df_post.empty:
                val_max = df_post[col].astype(str).str.len().max()
                if pd.notna(val_max):
                    max_len = max(max_len, int(val_max))
            col_width = int(min(max(max_len * 11, 100), 320))
            self.tree.heading(col, text=col_str)
            self.tree.column(col, width=col_width, minwidth=80, stretch=False)

        for _, row in df_post.head(500).iterrows():
            self.tree.insert("", "end", values=list(row.fillna("")))

    def _render_text_preview(self, preview_images, info_text):
        self.preview_image_box.pack_forget()
        self.table_frame.pack_forget()
        self.text_preview_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.lbl_info.configure(text=info_text)
        self.preview_pages = preview_images
        self.current_page_idx = 0
        self.zoom_level = 1.0
        self.render_current_page()

    def process_conversion(self):
        if not self.selected_files:
            messagebox.showwarning(
                self.t("messages.process_warning_title"),
                self.t("messages.process_warning_open")
            )
            return

        self.show_progress()
        status_msg = self.t("labels.status_merging_ram") if self.is_pdf_merge_mode else self.t("labels.status_converting_ram")
        self.lbl_status.configure(
            text=status_msg, text_color="#1f538d"
        )
        self.progress_bar.set(0.4)

        threading.Thread(
            target=self._process_conversion_thread, daemon=True
        ).start()

    def _process_conversion_thread(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass

        try:
            if not self.selected_files:
                raise ValueError(self.t("messages.no_input_data"))

            merge_files = bool(self.switch_merge.get()) if self.file_type != "sheet" else False
            files_to_process = (
                self.selected_files
                if merge_files
                else [self.selected_files[0]]
            )

            if self.file_type == "image":
                target_fmt = self.segmented_fmt.get()
                quality = int(self.slider_quality.get())
                target_res = self.get_target_resolution()

                if target_fmt == "PDF":
                    out_buffer, _ = self.convert_multi_images_to_pdf(
                        files_to_process, target_res=target_res, quality=quality
                    )
                else:
                    input_data = bytes(files_to_process[0]["bytes"])
                    try:
                        out_buffer, _, _ = convert_image(
                            input_data,
                            target_format=target_fmt,
                            quality=quality,
                            resolution=target_res,
                        )
                    except TypeError:
                        out_buffer, _, _ = convert_image(
                            input_data, target_format=target_fmt, quality=quality
                        )

            elif self.file_type == "sheet":
                sep = self.get_selected_delimiter()
                enc = self.get_selected_encoding(self.opt_encoding)
                target_sheet_fmt = self.segmented_sheet_fmt.get()
                input_data = bytes(files_to_process[0]["bytes"])
                src_ext = Path(files_to_process[0]["name"]).suffix.lstrip(".").lower()

                out_buffer, _, _, _, _, _ = convert_sheet(
                    input_data,
                    src_ext,
                    target_format=target_sheet_fmt,
                    delimiter=sep,
                    encoding=enc,
                )

            elif self.file_type == "text":
                enc = None if self.is_pdf_merge_mode else self.get_selected_encoding(self.opt_text_encoding)
                target_text_fmt = "PDF" if self.is_pdf_merge_mode else self.segmented_text_fmt.get()

                if len(files_to_process) == 1:
                    input_data = bytes(files_to_process[0]["bytes"])
                    src_ext = Path(files_to_process[0]["name"]).suffix.lstrip(".").lower()
                    out_buffer, _, _, _, _, _ = convert_text(
                        input_data,
                        src_ext,
                        target_format=target_text_fmt,
                        encoding=enc,
                    )
                else:
                    if target_text_fmt.upper() == "PDF":
                        from pypdf import PdfWriter

                        merger = PdfWriter()
                        for f_info in files_to_process:
                            input_data = bytes(f_info["bytes"])
                            src_ext = Path(f_info["name"]).suffix.lstrip(".").lower()

                            if src_ext == "pdf":
                                merger.append(io.BytesIO(input_data))
                            else:
                                res = convert_text(
                                    input_data,
                                    src_ext,
                                    target_format="PDF",
                                    encoding=enc,
                                )
                                pdf_bytes = res[0]
                                if pdf_bytes:
                                    pdf_data = pdf_bytes.getvalue() if hasattr(pdf_bytes, "getvalue") else pdf_bytes
                                    merger.append(io.BytesIO(pdf_data))

                        output_pdf_stream = io.BytesIO()
                        merger.write(output_pdf_stream)
                        merger.close()
                        out_buffer = output_pdf_stream
                    else:
                        full_text = ""
                        for f_info in files_to_process:
                            input_data = bytes(f_info["bytes"])
                            src_ext = Path(f_info["name"]).suffix.lstrip(".").lower()
                            res = convert_text(
                                input_data,
                                src_ext,
                                target_format="TXT",
                                encoding=enc,
                            )
                            txt_content = res[3] if isinstance(res, (tuple, list)) and len(res) > 3 else res
                            full_text += str(txt_content) + "\n\n"

                        out_buffer, _, _, _, _, _ = convert_text(
                            full_text.encode("utf-8"),
                            "txt",
                            target_format=target_text_fmt,
                            encoding="utf-8",
                        )

            self.converted_buffer = out_buffer
            self.after(0, self._on_conversion_success)

        except Exception as e:
            self.after(0, lambda err=str(e): self._on_conversion_error(err))
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except ImportError:
                pass

    def _on_conversion_success(self):
        self.progress_bar.set(1.0)
        success_msg = self.t("labels.status_merge_success") if self.is_pdf_merge_mode else self.t("labels.status_convert_success")
        self.lbl_status.configure(
            text=success_msg, 
            text_color=("#1e7e53", "#2ecc71")
        )
        self.btn_save.configure(state="normal")

        if self.file_type == "text" and self.converted_buffer:
            try:
                if hasattr(self.converted_buffer, "getvalue"):
                    pdf_bytes = self.converted_buffer.getvalue()
                elif isinstance(self.converted_buffer, bytes):
                    pdf_bytes = self.converted_buffer
                else:
                    pdf_bytes = None

                if pdf_bytes:
                    preview_imgs = generate_pdf_pages_images(pdf_bytes)
                    if preview_imgs:
                        merge_files = bool(self.switch_merge.get())
                        total_files = len(self.selected_files) if merge_files else 1
                        size_mb = len(pdf_bytes) / (1024 * 1024)
                        
                        if self.is_pdf_merge_mode:
                            info_text = self.t("labels.info_pdf_merge", count=total_files, size=size_mb)
                        else:
                            info_text = self.t("labels.info_pdf_preview", count=total_files, enc=self.opt_text_encoding.get(), size=size_mb)
                        
                        self._render_text_preview(preview_imgs, info_text)
            except Exception:
                pass

    def _on_conversion_error(self, error_msg: str):
        self.progress_bar.set(0)
        self.lbl_status.configure(
            text=self.t("labels.status_process_error", err=error_msg), 
            text_color=("#c93b2b", "#e74c3c")
        )
        messagebox.showerror(
            self.t("messages.process_error_title"),
            self.t("messages.process_error_body", err=error_msg)
        )

    def save_converted_file(self):
        if not self.converted_buffer:
            messagebox.showwarning(
                self.t("messages.process_warning_title"),
                self.t("messages.process_warning_process")
            )
            return

        if self.is_pdf_merge_mode:
            ext_save = "pdf"
        elif self.file_type == "image":
            ext_save = self.segmented_fmt.get().lower()
        elif self.file_type == "sheet":
            ext_save = self.segmented_sheet_fmt.get().lower()
        else:
            ext_save = self.segmented_text_fmt.get().lower()

        save_path_str = filedialog.asksaveasfilename(
            defaultextension=f".{ext_save}",
            filetypes=[(ext_save.upper(), f"*.{ext_save}")]
        )

        if save_path_str:
            save_path = Path(save_path_str)
            if hasattr(self.converted_buffer, "getvalue"):
                data_bytes = self.converted_buffer.getvalue()
            elif isinstance(self.converted_buffer, bytes):
                data_bytes = self.converted_buffer
            else:
                data_bytes = str(self.converted_buffer).encode("utf-8")

            with open(save_path, "wb") as f:
                f.write(data_bytes)
            self.lbl_status.configure(
                text=self.t("labels.status_saved_success"), 
                text_color=("#1e7e53", "#2fa572")
            )


if __name__ == "__main__":
    app = SecureConverterApp()
    app.mainloop()