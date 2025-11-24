#!/usr/bin/env python3
"""
Instagram Post Planner - Windows GUI Application (Version 2)

Comprehensive GUI with all configuration parameters as user inputs.
NO hard-coded numeric thresholds - everything comes from GUI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
from datetime import datetime
from config import PlanConfig, create_default_config
# planner module is imported lazily when needed to avoid best_effort_analyzer dependency at startup
# from planner import run_planner, run_planner_with_best_effort


class ToolTip:
    """Tooltip widget for showing help text on hover"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None):
        self.show_tooltip(event)
    
    def on_motion(self, event=None):
        if self.tooltip_window:
            self.show_tooltip(event)
    
    def show_tooltip(self, event=None):
        if event:
            x = event.x_root + 10
            y = event.y_root + 10
        else:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 5
            y = self.widget.winfo_rooty() + 5
        
        if self.tooltip_window:
            self.tooltip_window.destroy()
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create frame with padding
        frame = tk.Frame(
            self.tooltip_window,
            background="#ffffe0",
            relief="solid",
            borderwidth=2
        )
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        label = tk.Label(
            frame,
            text=self.text,
            background="#ffffe0",
            font=("Arial", 9),
            justify="left",
            wraplength=450,
            padx=10,
            pady=8
        )
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class ScrollableFrame(ttk.Frame):
    """A scrollable frame for long forms"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        def _on_frame_configure(event):
            """Update scroll region when frame size changes"""
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
                # Scrollbar görünürlüğünü kontrol et
                canvas_height = canvas.winfo_height()
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height and canvas_height > 1:
                    scrollbar.pack(side="right", fill="y")
                else:
                    scrollbar.pack_forget()
            else:
                canvas.configure(scrollregion=(0, 0, 0, 0))
            # Force scrollbar to update
            canvas.update_idletasks()
        
        self.scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        def _on_canvas_configure(event):
            """Update canvas window width when canvas size changes"""
            canvas_width = event.width
            canvas.itemconfig(canvas_window_id, width=canvas_width)
            # Update scroll region after resize
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
                # Scrollbar görünürlüğünü kontrol et
                canvas_height = event.height
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height and canvas_height > 1:
                    scrollbar.pack(side="right", fill="y")
                else:
                    scrollbar.pack_forget()
        
        canvas_window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        # Scrollbar'ı her zaman göster (scrollregion ayarlanınca otomatik görünür/gizlenir)
        scrollbar.pack(side="right", fill="y")
        
        # Scrollbar'ın görünürlüğünü kontrol et
        def _check_scrollbar_visibility():
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas_height = canvas.winfo_height()
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height and canvas_height > 1:
                    # İçerik canvas'tan büyükse scrollbar'ı göster
                    scrollbar.pack(side="right", fill="y")
                else:
                    # İçerik canvas'tan küçükse scrollbar'ı gizle
                    scrollbar.pack_forget()
        
        # Scrollbar görünürlüğünü kontrol et
        self.after(100, _check_scrollbar_visibility)
        self.after(500, _check_scrollbar_visibility)
        self.after(1000, _check_scrollbar_visibility)
        
        def _on_mousewheel(event):
            # Windows ve Mac için
            if event.delta:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            # Linux için
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
        
        # Canvas'a focus verildiğinde scroll çalışsın
        def _on_canvas_enter(event):
            canvas.focus_set()
        
        # Tüm child widget'lara recursive olarak mouse wheel event'lerini bind et
        def _bind_mousewheel_recursive(widget):
            """Recursively bind mouse wheel events to widget and all its children"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
                widget.bind("<Button-4>", _on_mousewheel)    # Linux yukarı
                widget.bind("<Button-5>", _on_mousewheel)    # Linux aşağı
                # Widget'a mouse geldiğinde canvas'a focus ver (Windows'ta mouse wheel için gerekli)
                widget.bind("<Enter>", lambda e: canvas.focus_set())
            except:
                pass  # Bazı widget'lar bind desteklemeyebilir
            
            # Tüm child widget'lara recursive olarak bind et
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)
        
        # Mouse wheel event'lerini canvas ve scrollable_frame'e bind et
        canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind("<Button-4>", _on_mousewheel)    # Linux yukarı
        canvas.bind("<Button-5>", _on_mousewheel)    # Linux aşağı
        canvas.bind("<Enter>", _on_canvas_enter)
        
        # Scrollable frame'e de bind et (içerideki widget'lar üzerinde scroll çalışsın)
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-5>", _on_mousewheel)
        
        # Tüm mevcut child widget'lara recursive olarak bind et
        _bind_mousewheel_recursive(self.scrollable_frame)
        
        # Yeni widget'lar eklendiğinde de bind etmek için bir callback ekle
        def _on_widget_added(event=None):
            """Yeni widget eklendiğinde mouse wheel event'lerini bind et"""
            _bind_mousewheel_recursive(self.scrollable_frame)
        
        # Scrollable frame'e yeni widget eklendiğinde callback'i çağır
        # Not: Tkinter'da doğrudan bir "widget added" event'i yok, 
        # bu yüzden periyodik olarak kontrol edeceğiz veya widget ekleme işlemlerinden sonra çağıracağız
        self._bind_mousewheel_to_new_widgets = _bind_mousewheel_recursive
        
        # Canvas'a focus ver
        canvas.focus_set()
        
        # Store canvas and scrollbar for later access
        self.canvas = canvas
        self.scrollbar = scrollbar
        
        # Force initial scroll region update after a short delay
        def _update_scroll_region_initial():
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
        
        # Update scroll region multiple times to ensure it's set correctly
        self.after(100, _update_scroll_region_initial)
        self.after(500, _update_scroll_region_initial)
        self.after(1000, _update_scroll_region_initial)


class PlannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Post Planner - Comprehensive Configuration")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        self.config = create_default_config()
        
        self.excel_path = tk.StringVar()
        self.start_day = tk.StringVar(value="Pazartesi")
        self.num_days = tk.IntVar(value=7)
        
        self.use_yazlik_front = tk.BooleanVar(value=False)
        self.use_kislik_front = tk.BooleanVar(value=False)
        self.cekim_front_evet = tk.BooleanVar(value=False)
        self.cekim_front_na = tk.BooleanVar(value=False)
        self.one_atilma_allow_na = tk.BooleanVar(value=False)
        self.one_atilma_date = tk.StringVar(value="")
        self.one_atilma_days = tk.IntVar(value=0)
        self.min_stock_front = tk.IntVar(value=0)
        self.min_nos_front = tk.IntVar(value=0)
        self.min_dvm_front = tk.IntVar(value=0)
        
        self.front_size_y = {}
        self.front_size_z = {}
        for i in range(1, 9):
            self.front_size_y[i] = tk.IntVar(value=0)
            self.front_size_z[i] = tk.IntVar(value=0)
        
        self.use_yazlik_back = tk.BooleanVar(value=False)
        self.use_kislik_back = tk.BooleanVar(value=False)
        self.cekim_back_evet = tk.BooleanVar(value=False)
        self.cekim_back_na = tk.BooleanVar(value=False)
        self.min_stock_back = tk.IntVar(value=0)
        
        self.back_size_y = {}
        self.back_size_z = {}
        for i in range(1, 9):
            self.back_size_y[i] = tk.IntVar(value=0)
            self.back_size_z[i] = tk.IntVar(value=0)
        
        self.max_same_uruncinsi = tk.IntVar(value=0)
        self.min_distinct_uruncinsi = tk.IntVar(value=0)
        self.max_same_color = tk.IntVar(value=0)
        self.min_distinct_color = tk.IntVar(value=0)
        self.same_kisakod_gap = tk.IntVar(value=0)
        
        self.max_black_first_per_day = tk.IntVar(value=0)
        self.max_first_uses_per_kisakod = tk.IntVar(value=0)
        self.max_distinct_kisakod_repeatable = tk.IntVar(value=0)
        
        self.global_first_stock = tk.IntVar(value=0)
        self.global_total_stock = tk.IntVar(value=0)
        
        self.prioritize_by_newness = tk.BooleanVar(value=False)
        self.prioritize_by_stock = tk.BooleanVar(value=False)
        
        self.progress_queue = queue.Queue()
        self.decision_queue = queue.Queue()
        self.decision_result = None
        self.decision_event = threading.Event()
        self.is_running = False
        
        # Pool size tracking for live updates (initialized as None, will be set in create_*_tab methods)
        self.first_pool_size_label = None
        self.back_pool_size_label = None
        self.advanced_first_pool_label = None
        self.required_counts_label = None
        self.raw_df = None  # Will be loaded when Excel file is selected
        
        # Threading and debouncing for pool size updates
        self.pool_update_thread = None
        self.pool_update_timer = None
        
        self.create_widgets()
        self.auto_load_settings()
        self.setup_auto_save_triggers()
        self.check_progress_queue()
    
    def create_widgets(self):
        # Create custom button styles
        style = ttk.Style()
        
        # Try to configure custom styles, but fallback to default if not supported
        try:
            # Green button style for "Planı Oluştur" (%50 larger)
            style.configure("Green.TButton",
                         background="#2d8659",
                         foreground="white",
                         font=("Arial", 12, "bold"),
                         padding=12)
            style.map("Green.TButton",
                     background=[("active", "#1f5f3f"), ("pressed", "#1a4f34")])
        except:
            pass  # Style may not be supported on all systems
        
        try:
            # Gray button style for "Ayarları Sıfırla"
            style.configure("Gray.TButton",
                           background="#808080",
                           foreground="white",
                           font=("Arial", 10),
                           padding=6)
            style.map("Gray.TButton",
                     background=[("active", "#6a6a6a"), ("pressed", "#555555")])
        except:
            pass
        
        try:
            # Orange button style for "Rapor Öncesi Kontrol"
            style.configure("Orange.TButton",
                           background="#ff8c00",
                           foreground="white",
                           font=("Arial", 10, "bold"),
                           padding=6)
            style.map("Orange.TButton",
                     background=[("active", "#e67e00"), ("pressed", "#cc6f00")])
        except:
            pass
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        file_frame = ttk.LabelFrame(main_frame, text="Stok Dosyası", padding="5")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(file_frame, textvariable=self.excel_path, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(file_frame, text="Dosya Seç...", command=self.select_file).grid(
            row=0, column=1
        )
        
        # Global "Plan Length & Required Counts" box - visible on all tabs
        # Plan Uzunluğu & Gerekli Sayılar + Havuz Değerleri (sabit alan)
        self.required_counts_frame = ttk.LabelFrame(main_frame, text="Plan Uzunluğu & Gerekli Sayılar", padding="10")
        self.required_counts_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # İçeride üç sütun: Sol tarafta plan bilgileri, ortada buton, sağ tarafta havuz değerleri
        counts_inner_frame = ttk.Frame(self.required_counts_frame)
        counts_inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol taraf: Plan uzunluğu ve gerekli sayılar
        left_frame = ttk.Frame(counts_inner_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.required_counts_label = ttk.Label(
            left_frame,
            text="Plan uzunluğu ve günlük post sayılarına göre hesaplanıyor...",
            font=("Arial", 10)
        )
        self.required_counts_label.pack(anchor=tk.W)
        
        # Orta: Havuz hesaplama butonu
        center_frame = ttk.Frame(counts_inner_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(30, 30))
        self.pool_calculate_button = ttk.Button(
            center_frame,
            text="Havuz Hesapla",
            command=self.check_and_calculate_pool,
            width=20
        )
        self.pool_calculate_button.pack(anchor=tk.CENTER, pady=(10, 0))
        
        # Sağ taraf: Havuz değerleri
        right_frame = ttk.Frame(counts_inner_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        # FIRST Havuz Boyutu
        self.first_pool_size_label = ttk.Label(
            right_frame,
            text="FIRST Havuz Boyutu: Excel dosyası yüklenmedi",
            font=("Arial", 10, "bold"),
            foreground="blue"
        )
        self.first_pool_size_label.pack(anchor=tk.W, pady=(0, 5))
        
        # BACK Havuz Boyutu
        self.back_pool_size_label = ttk.Label(
            right_frame,
            text="BACK Havuz Boyutu: Excel dosyası yüklenmedi",
            font=("Arial", 10, "bold"),
            foreground="blue"
        )
        self.back_pool_size_label.pack(anchor=tk.W)
        
        # Don't call update_required_counts here - it will be called after all tabs are created
        
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.create_plan_tab(notebook)
        self.create_first_tab(notebook)
        self.create_back_tab(notebook)
        self.create_advanced_tab(notebook)
        # Preferred tab removed - moved to Advanced Rules tab
        self.create_output_tab(notebook)
        
        # Now that all tabs are created, update required counts and pool sizes
        self.update_required_counts()
    
    def create_plan_tab(self, notebook):
        """Plan Settings tab"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="Plan Ayarları")
        frame = scroll_frame.scrollable_frame
        
        row = 0
        
        ttk.Label(frame, text="Plan Başlangıç Günü:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        start_day_combo = ttk.Combobox(
            frame,
            textvariable=self.start_day,
            values=["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"],
            state="readonly",
            width=20
        )
        start_day_combo.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        # Update required counts when start_day changes
        self.start_day.trace_add("write", lambda *args: self.update_required_counts())
        row += 1
        
        ttk.Label(frame, text="Kaç Günlük Plan (1-7):", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        num_days_spinbox = ttk.Spinbox(
            frame,
            from_=1,
            to=7,
            textvariable=self.num_days,
            width=20
        )
        num_days_spinbox.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        # Update required counts when num_days changes
        self.num_days.trace_add("write", lambda *args: self.update_required_counts())
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Post Saatleri (Sabit)", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Hafta içi: 12 post/gün", font=("Arial", 9)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="09:00, 10:30, 11:30, 12:30, 13:30, 14:30,", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Label(frame, text="15:30, 16:30, 17:30, 19:30, 21:00, 22:30", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Label(frame, text="Haftasonu: 10 post/gün", font=("Arial", 9)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20, pady=(10, 0)
        )
        row += 1
        
        ttk.Label(frame, text="11:00, 12:00, 13:00, 14:00, 15:00,", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Label(frame, text="16:00, 17:00, 18:30, 19:30, 21:00", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        # Action buttons at the bottom
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 10)
        )
        row += 1
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Ayarları Sıfırla butonu (sol taraf) - tk.Button for better color support
        gray_button = tk.Button(
            button_frame,
            text="Ayarları Sıfırla",
            command=self.reset_settings,
            bg="#808080",
            fg="white",
            font=("Arial", 10),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=10,
            pady=6
        )
        gray_button.pack(side=tk.LEFT, padx=5)
        gray_button.bind("<Enter>", lambda e: gray_button.config(bg="#6a6a6a"))
        gray_button.bind("<Leave>", lambda e: gray_button.config(bg="#808080"))
        
        # Planı Oluştur butonu (sağ taraf, %50 büyük) - tk.Button for better color support
        green_button = tk.Button(
            button_frame,
            text="Planı Oluştur",
            command=self.run_planner,
            bg="#2d8659",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=15,
            pady=8
        )
        green_button.pack(side=tk.RIGHT, padx=5)
        green_button.bind("<Enter>", lambda e: green_button.config(bg="#1f5f3f"))
        green_button.bind("<Leave>", lambda e: green_button.config(bg="#2d8659"))
    
    def create_first_tab(self, notebook):
        """FIRST Product Criteria tab"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="FIRST Ürün Kriterleri")
        frame = scroll_frame.scrollable_frame
        
        row = 0
        
        ttk.Label(frame, text="Mevsim Filtresi:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(frame, text="Yazlık", variable=self.use_yazlik_front).grid(
            row=row, column=0, sticky=tk.W, padx=20
        )
        ttk.Checkbutton(frame, text="Kışlık", variable=self.use_kislik_front).grid(
            row=row, column=1, sticky=tk.W
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Cekim
        ttk.Label(frame, text="Cekim Filtresi:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(frame, text="EVET", variable=self.cekim_front_evet).grid(
            row=row, column=0, sticky=tk.W, padx=20
        )
        ttk.Checkbutton(frame, text="NA", variable=self.cekim_front_na).grid(
            row=row, column=1, sticky=tk.W
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # One Atilma Tarihi
        ttk.Label(frame, text="One Atilma Tarihi Filtresi:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(frame, text="Önde hiç kullanılmamışlar (önceliklidir)", variable=self.one_atilma_allow_na).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="Referans Tarih (T) (yyyy-mm-dd):", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Entry(frame, textvariable=self.one_atilma_date, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Minimum Gün Sayısı (X):", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=365, textvariable=self.one_atilma_days, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="(Ürün kabul: One Atilma < T - X gün)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Minimum Toplam Stok:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=10000, textvariable=self.min_stock_front, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Beden/Stok Kuralları:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Beden Sayısı", font=("Arial", 9, "bold")).grid(
            row=row, column=0, padx=20
        )
        ttk.Label(frame, text="Min Kaç Bedende (Y)", font=("Arial", 9, "bold")).grid(
            row=row, column=1, padx=5
        )
        ttk.Label(frame, text="Min Stok Değeri (Z)", font=("Arial", 9, "bold")).grid(
            row=row, column=2, padx=5
        )
        row += 1
        
        for i in range(1, 9):
            ttk.Label(frame, text=f"{i}", font=("Arial", 9)).grid(
                row=row, column=0, padx=20, pady=2
            )
            ttk.Spinbox(frame, from_=0, to=8, textvariable=self.front_size_y[i], width=10).grid(
                row=row, column=1, padx=5, pady=2
            )
            ttk.Spinbox(frame, from_=0, to=100, textvariable=self.front_size_z[i], width=10).grid(
                row=row, column=2, padx=5, pady=2
            )
            row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Action buttons at the bottom
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 10)
        )
        row += 1
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Ayarları Sıfırla butonu (sol taraf) - tk.Button for better color support
        gray_button = tk.Button(
            button_frame,
            text="Ayarları Sıfırla",
            command=self.reset_settings,
            bg="#808080",
            fg="white",
            font=("Arial", 10),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=10,
            pady=6
        )
        gray_button.pack(side=tk.LEFT, padx=5)
        gray_button.bind("<Enter>", lambda e: gray_button.config(bg="#6a6a6a"))
        gray_button.bind("<Leave>", lambda e: gray_button.config(bg="#808080"))
        
        # Planı Oluştur butonu (sağ taraf, %50 büyük) - tk.Button for better color support
        self.run_button = tk.Button(
            button_frame,
            text="Planı Oluştur",
            command=self.run_planner,
            bg="#2d8659",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.run_button.pack(side=tk.RIGHT, padx=5)
        self.run_button.bind("<Enter>", lambda e: self.run_button.config(bg="#1f5f3f"))
        self.run_button.bind("<Leave>", lambda e: self.run_button.config(bg="#2d8659"))
    
    def create_back_tab(self, notebook):
        """BACK Product Criteria tab"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="BACK Ürün Kriterleri")
        frame = scroll_frame.scrollable_frame
        
        row = 0
        
        ttk.Label(frame, text="Mevsim Filtresi:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(frame, text="Yazlık", variable=self.use_yazlik_back).grid(
            row=row, column=0, sticky=tk.W, padx=20
        )
        ttk.Checkbutton(frame, text="Kışlık", variable=self.use_kislik_back).grid(
            row=row, column=1, sticky=tk.W
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Cekim
        ttk.Label(frame, text="Cekim Filtresi:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(frame, text="EVET", variable=self.cekim_back_evet).grid(
            row=row, column=0, sticky=tk.W, padx=20
        )
        ttk.Checkbutton(frame, text="NA", variable=self.cekim_back_na).grid(
            row=row, column=1, sticky=tk.W
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Minimum Toplam Stok:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=10000, textvariable=self.min_stock_back, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Beden/Stok Kuralları:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Beden Sayısı", font=("Arial", 9, "bold")).grid(
            row=row, column=0, padx=20
        )
        ttk.Label(frame, text="Min Kaç Bedende (Y)", font=("Arial", 9, "bold")).grid(
            row=row, column=1, padx=5
        )
        ttk.Label(frame, text="Min Stok Değeri (Z)", font=("Arial", 9, "bold")).grid(
            row=row, column=2, padx=5
        )
        row += 1
        
        for i in range(1, 9):
            ttk.Label(frame, text=f"{i}", font=("Arial", 9)).grid(
                row=row, column=0, padx=20, pady=2
            )
            ttk.Spinbox(frame, from_=0, to=8, textvariable=self.back_size_y[i], width=10).grid(
                row=row, column=1, padx=5, pady=2
            )
            ttk.Spinbox(frame, from_=0, to=100, textvariable=self.back_size_z[i], width=10).grid(
                row=row, column=2, padx=5, pady=2
            )
            row += 1
        
        # Action buttons at the bottom
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 10)
        )
        row += 1
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Ayarları Sıfırla butonu (sol taraf) - tk.Button for better color support
        gray_button = tk.Button(
            button_frame,
            text="Ayarları Sıfırla",
            command=self.reset_settings,
            bg="#808080",
            fg="white",
            font=("Arial", 10),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=10,
            pady=6
        )
        gray_button.pack(side=tk.LEFT, padx=5)
        gray_button.bind("<Enter>", lambda e: gray_button.config(bg="#6a6a6a"))
        gray_button.bind("<Leave>", lambda e: gray_button.config(bg="#808080"))
        
        # Planı Oluştur butonu (sağ taraf, %50 büyük) - tk.Button for better color support
        green_button = tk.Button(
            button_frame,
            text="Planı Oluştur",
            command=self.run_planner,
            bg="#2d8659",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=15,
            pady=8
        )
        green_button.pack(side=tk.RIGHT, padx=5)
        green_button.bind("<Enter>", lambda e: green_button.config(bg="#1f5f3f"))
        green_button.bind("<Leave>", lambda e: green_button.config(bg="#2d8659"))
    
    def create_advanced_tab(self, notebook):
        """Placement Rules tab (formerly Advanced Rules)"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="Yerleştirme Kuralları")
        frame = scroll_frame.scrollable_frame
        
        # Column configure for proper layout
        # Note: Tercihli ürünler tablosu için yatay scrollbar eklenecek
        frame.columnconfigure(0, weight=1)  # Main content area - expandable
        
        row = 0
        
        # Tercihli FIRST Ürünler bölümü (en üstte)
        ttk.Label(frame, text="Tercihli FIRST Ürünler:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Bu ürünler FIRST olarak plana dahil edilmeye çalışılacaktır.", font=("Arial", 9)).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Gün+Saat seçilirse: O gün o saatte kullanılır (hard constraint)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="Sadece KisaKod+Renk girilirse: Herhangi bir günde kullanılır", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Tercihli ürünler tablosu - doğrudan frame içine yerleştir (yatay scrollbar yok)
        table_inner_frame = ttk.Frame(frame)
        table_inner_frame.grid(row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Table headers in inner frame
        table_row = 0
        ttk.Label(table_inner_frame, text="#", font=("Arial", 9, "bold"), width=3).grid(
            row=table_row, column=0, sticky=tk.W, padx=(0, 2)
        )
        ttk.Label(table_inner_frame, text="Aksiyon", font=("Arial", 9, "bold"), width=15).grid(
            row=table_row, column=1, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(table_inner_frame, text="KisaKod+Renk", font=("Arial", 9, "bold"), width=20).grid(
            row=table_row, column=2, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(table_inner_frame, text="Gün", font=("Arial", 9, "bold"), width=15).grid(
            row=table_row, column=3, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(table_inner_frame, text="Saat", font=("Arial", 9, "bold"), width=10).grid(
            row=table_row, column=4, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(table_inner_frame, text="Durum", font=("Arial", 9, "bold"), width=30).grid(
            row=table_row, column=5, sticky=tk.W, padx=(0, 5)
        )
        table_row += 1
        
        gun_options = ["", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        weekday_times = ["", "09:00", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:30", "17:30", "19:30", "21:00", "22:30"]
        weekend_times = ["", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:30", "19:30", "21:00"]
        
        # Initialize preferred_entries if not already initialized
        if not hasattr(self, 'preferred_entries'):
            self.preferred_entries = []
        
        # Clear existing entries if any
        self.preferred_entries = []
        
        for i in range(10):
            kisakodrenk_var = tk.StringVar()
            gun_var = tk.StringVar()
            time_var = tk.StringVar()
            
            ttk.Label(table_inner_frame, text=f"{i+1}.", font=("Arial", 9)).grid(
                row=table_row, column=0, sticky=tk.W, padx=(0, 2), pady=2
            )
            
            # Havuza ekle/çıkar butonu (başlangıçta gizli, KisaKod+Renk solunda)
            # Bu buton duruma göre "Yine de Havuza Ekle" veya "Havuzdan Çıkar" olacak
            pool_button = ttk.Button(
                table_inner_frame,
                text="Yine de Havuza Ekle",
                command=lambda idx=i: self.toggle_preferred_product_in_pool(idx),
                width=15
            )
            pool_button.grid(row=table_row, column=1, sticky=tk.W, padx=(0, 5), pady=2)
            pool_button.grid_remove()  # Başlangıçta gizli
            
            kisakodrenk_entry = ttk.Entry(table_inner_frame, textvariable=kisakodrenk_var, width=20)
            kisakodrenk_entry.grid(row=table_row, column=2, sticky=tk.W, padx=(0, 5), pady=2)
            self._attach_entry_context_menu(kisakodrenk_entry)
            
            gun_combo = ttk.Combobox(table_inner_frame, textvariable=gun_var, width=15, state="readonly", values=gun_options)
            gun_combo.grid(row=table_row, column=3, sticky=tk.W, padx=(0, 5), pady=2)
            
            time_combo = ttk.Combobox(table_inner_frame, textvariable=time_var, width=10, state="readonly")
            time_combo.grid(row=table_row, column=4, sticky=tk.W, padx=(0, 5), pady=2)
            
            def on_gun_change(event, gun_v=gun_var, time_v=time_var, time_c=time_combo, wdt=weekday_times, wet=weekend_times):
                gun = gun_v.get()
                if not gun:
                    time_c['values'] = [""]
                    time_v.set("")
                    time_c['state'] = 'disabled'
                elif gun in ["Cumartesi", "Pazar"]:
                    time_c['values'] = wet
                    time_c['state'] = 'readonly'
                else:
                    time_c['values'] = wdt
                    time_c['state'] = 'readonly'
            
            gun_combo.bind('<<ComboboxSelected>>', on_gun_change)
            time_combo['state'] = 'disabled'
            
            # Durum label'ı (scrollable)
            status_frame = ttk.Frame(table_inner_frame)
            status_frame.grid(row=table_row, column=5, sticky=(tk.W, tk.E), padx=(0, 5), pady=2)
            
            # ttk.Frame doesn't support bg option, use system default or parent's bg
            try:
                parent_bg = frame.winfo_toplevel().cget('bg')
            except:
                parent_bg = 'SystemButtonFace'  # Windows default
            status_canvas = tk.Canvas(status_frame, height=20, highlightthickness=0, bg=parent_bg)
            status_scrollbar = ttk.Scrollbar(status_frame, orient="horizontal", command=status_canvas.xview)
            status_canvas.configure(xscrollcommand=status_scrollbar.set)
            
            status_label = ttk.Label(status_canvas, text="", font=("Arial", 8), foreground="gray", anchor="w")
            status_canvas_window = status_canvas.create_window((0, 0), window=status_label, anchor="nw")
            
            def configure_status_scroll(event=None):
                status_canvas.update_idletasks()
                bbox = status_canvas.bbox("all")
                if bbox:
                    status_canvas.configure(scrollregion=bbox)
                    # Scrollbar'ı sadece gerektiğinde göster
                    canvas_width = status_canvas.winfo_width()
                    if canvas_width > 1 and bbox[2] > canvas_width:
                        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    else:
                        status_scrollbar.pack_forget()
            
            status_label.bind("<Configure>", configure_status_scroll)
            status_canvas.bind("<Configure>", lambda e: configure_status_scroll())
            
            status_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Store update function for later use
            status_update_scroll = configure_status_scroll
            
            # "Havuzdan Çıkar" butonu (başlangıçta gizli, sağ tarafta)
            remove_from_pool_button = ttk.Button(
                table_inner_frame,
                text="Havuzdan Çıkar",
                command=lambda idx=i: self.toggle_preferred_product_in_pool(idx),
                width=15
            )
            remove_from_pool_button.grid(row=table_row, column=6, sticky=tk.W, padx=(0, 0), pady=2)
            remove_from_pool_button.grid_remove()  # Başlangıçta gizli
            
            self.preferred_entries.append({
                'kisakodrenk': kisakodrenk_var,
                'kisakodrenk_entry': kisakodrenk_entry,
                'gun': gun_var,
                'time': time_var,
                'gun_combo': gun_combo,
                'time_combo': time_combo,
                'status_label': status_label,
                'pool_button': pool_button,  # Yine de Havuza Ekle butonu
                'remove_from_pool_button': remove_from_pool_button,  # Havuzdan Çıkar butonu
                'in_pool': False  # Havuzda mı değil mi
            })
            
            table_row += 1
        
        # Update scroll region after all rows are added (sadece bir kez, gecikmeli)
        # Canvas ve scrollbar kaldırıldı, güncelleme gerekmiyor
        
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # KRİTERLERE UYGUN MU butonu (Önemli Notlar'ın üzerine)
        ttk.Button(
            frame,
            text="KRİTERLERE UYGUN MU",
            command=self.check_preferred_products_criteria,
            width=25
        ).grid(row=row, column=0, columnspan=6, pady=10)
        row += 1
        
        ttk.Label(frame, text="Önemli Notlar:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="• Saat seçilirse gün de seçilmelidir (zorunlu)", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="• Gün plan aralığı içinde olmalıdır", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="• Tercihli ürünler tüm FIRST kriterlerine uymalıdır", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        # Scroll region'ı güncelle (scrollbar'ın görünmesi için)
        def update_scroll_region():
            try:
                scroll_frame.canvas.update_idletasks()
                bbox = scroll_frame.canvas.bbox("all")
                if bbox:
                    scroll_frame.canvas.configure(scrollregion=bbox)
                # Yeni widget'lar eklendiyse mouse wheel binding'lerini güncelle
                if hasattr(scroll_frame, '_bind_mousewheel_to_new_widgets'):
                    scroll_frame._bind_mousewheel_to_new_widgets(scroll_frame.scrollable_frame)
            except:
                pass
        
        # İlk yüklemeden sonra scroll region'ı güncelle (birden fazla kez)
        frame.after(100, update_scroll_region)
        frame.after(500, update_scroll_region)
        frame.after(1000, update_scroll_region)
        frame.after(2000, update_scroll_region)
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Global Prioritization (tercihli ürünlerden sonra)
        ttk.Label(frame, text="Global Önceliklendirme (FIRST Ürünler İçin):", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(
            frame, 
            text="Yeniliğe göre önceliklendir (en yeni ürünler önce)",
            variable=self.prioritize_by_newness
        ).grid(row=row, column=0, columnspan=5, sticky=tk.W, padx=20, pady=5)
        row += 1
        
        ttk.Checkbutton(
            frame, 
            text="Stok miktarına göre önceliklendir (yüksek stoklu ürünler önce)",
            variable=self.prioritize_by_stock
        ).grid(row=row, column=0, columnspan=5, sticky=tk.W, padx=20, pady=5)
        row += 1
        
        ttk.Label(frame, text="(Her ikisi seçilirse birleşik önceliklendirme kullanılır)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # NOS/DVM Minimumları bölümü
        ttk.Label(frame, text="NOS/DVM Minimumları:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Minimum NOS FIRST sayısı:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=100, textvariable=self.min_nos_front, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Minimum DVM FIRST sayısı:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=100, textvariable=self.min_dvm_front, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # FIRST Renk Kısıtı bölümü (Günlük Kısıtlar'dan önce)
        ttk.Label(frame, text="FIRST Renk Kısıtı:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Günde max kaç FIRST SİYAH renk:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=20, textvariable=self.max_black_first_per_day, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="(0 = kısıt yok)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Aynı KisaKod Kuralı (FIRST Renk Kısıtı'ndan sonra, Günlük Kısıtlar'dan önce)
        kisakod_rule_label = ttk.Label(frame, text="Aynı KisaKod Kuralı:", font=("Arial", 10, "bold"))
        kisakod_rule_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        
        # Info label with tooltip
        info_text = """Aynı KisaKod Kuralı Kriterleri:

1. Minimum Ara Gün Sayısı:
   Aynı KisaKod'un iki kullanımı arasında en az kaç gün olması gerektiğini belirler.
   Örnek: 2 seçilirse, 5Y123 siyah Pazartesi kullanıldıysa, 
   aynı KisaKod (farklı renk) en erken Çarşamba kullanılabilir.

2. Aynı KisaKod Max Kullanım (FIRST):
   Bir KisaKod'un planda en fazla kaç kez kullanılabileceğini belirler (farklı renklerle).
   Örnek: 2 seçilirse, 5Y123 siyah ve 5Y123 mavi kullanılabilir, 
   ancak 5Y123 kırmızı kullanılamaz (3. kullanım olur).

3. Kaç Farklı KisaKod Tekrarlı Kullanılabilir:
   Planda toplam kaç farklı KisaKod'un tekrarlı (2+ kez) kullanılabileceğini belirler.
   Örnek: 3 seçilirse ve max kullanım 2 ise:
   - 5Y123 siyah ve mavi (tekrarlı, sayılır)
   - 5Y156 kırmızı ve sarı (tekrarlı, sayılır)
   - 5Y235 siyah ve mavi (tekrarlı, sayılır)
   Toplam 3 farklı KisaKod tekrarlı kullanılmış olur."""
        
        info_label = tk.Label(
            frame,
            text="ℹ",
            font=("Arial", 12, "bold"),
            foreground="red",
            cursor="hand2"
        )
        info_label.grid(row=row, column=0, sticky=tk.W, padx=(150, 0), pady=5)
        ToolTip(info_label, info_text)
        
        row += 1
        
        ttk.Label(frame, text="Minimum ara gün sayısı:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=7, textvariable=self.same_kisakod_gap, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="(0 = kısıt yok, 1+ = N gün bekle)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Label(frame, text="Aynı KisaKod max kullanım (FIRST):", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=20, textvariable=self.max_first_uses_per_kisakod, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="(0 = kısıt yok, sadece FIRST için)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Label(frame, text="Kaç farklı KisaKod tekrarlı kullanılabilir:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=50, textvariable=self.max_distinct_kisakod_repeatable, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="(0 = kısıt yok, tekrarlı kullanılan farklı KisaKod sayısı)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        # Günlük Kısıtlar bölümü (en sonda)
        ttk.Label(frame, text="Günlük Kısıtlar:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Aynı ürün cinsi ardışık limit:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=10, textvariable=self.max_same_uruncinsi, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Minimum farklı ürün cinsi/gün:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=20, textvariable=self.min_distinct_uruncinsi, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Aynı renk ardışık limit:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=10, textvariable=self.max_same_color, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Minimum farklı renk/gün:", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=20, textvariable=self.min_distinct_color, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        # Rapor Öncesi Kontrol butonu - ön yerleştirme simülasyonu ve tüm kriterlerin kontrolü
        # Use tk.Button for better color support
        orange_button = tk.Button(
            frame,
            text="Rapor Öncesi Kontrol",
            command=self.pre_report_validation,
            width=25,
            bg="#ff8c00",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2"
        )
        orange_button.grid(row=row, column=0, columnspan=2, pady=10)
        orange_button.bind("<Enter>", lambda e: orange_button.config(bg="#e67e00"))
        orange_button.bind("<Leave>", lambda e: orange_button.config(bg="#ff8c00"))
        row += 1
        
        # Açıklama: Günlük kısıtlar havuz boyutunu değiştirmez
        ttk.Label(frame, text="Not: Günlük kısıtlar (ardışık limit, minimum farklı sayı) havuz boyutunu değiştirmez.", 
                  font=("Arial", 8, "italic"), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20, pady=(0, 5)
        )
        row += 1
        ttk.Label(frame, text="Bu kısıtlar sadece atama sırasında kontrol edilir.", 
                  font=("Arial", 8, "italic"), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20
        )
        row += 1
        
        # Action buttons at the bottom
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 10)
        )
        row += 1
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Ayarları Sıfırla butonu (sol taraf) - tk.Button for better color support
        gray_button = tk.Button(
            button_frame,
            text="Ayarları Sıfırla",
            command=self.reset_settings,
            bg="#808080",
            fg="white",
            font=("Arial", 10),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=10,
            pady=6
        )
        gray_button.pack(side=tk.LEFT, padx=5)
        gray_button.bind("<Enter>", lambda e: gray_button.config(bg="#6a6a6a"))
        gray_button.bind("<Leave>", lambda e: gray_button.config(bg="#808080"))
        
        # Planı Oluştur butonu (sağ taraf, %50 büyük) - tk.Button for better color support
        green_button = tk.Button(
            button_frame,
            text="Planı Oluştur",
            command=self.run_planner,
            bg="#2d8659",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=15,
            pady=8
        )
        green_button.pack(side=tk.RIGHT, padx=5)
        green_button.bind("<Enter>", lambda e: green_button.config(bg="#1f5f3f"))
        green_button.bind("<Leave>", lambda e: green_button.config(bg="#2d8659"))
    
    def create_global_tab(self, notebook):
        """Global Stock Targets tab"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="Global Stok Hedefleri")
        frame = scroll_frame.scrollable_frame
        
        row = 0
        
        ttk.Label(frame, text="Global Stok Hedefleri:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Tüm FIRST ürünlerin toplam stoku (minimum):", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=100000, textvariable=self.global_first_stock, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Tüm ürünlerin (FIRST+BACK) toplam stoku (minimum):", font=("Arial", 9)).grid(
            row=row, column=0, sticky=tk.W, padx=20, pady=5
        )
        ttk.Spinbox(frame, from_=0, to=100000, textvariable=self.global_total_stock, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Global Önceliklendirme:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Checkbutton(
            frame, 
            text="Yeniliğe göre önceliklendir (KisaKod yıl + sıra)", 
            variable=self.prioritize_by_newness
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=20, pady=5)
        row += 1
        
        ttk.Checkbutton(
            frame, 
            text="Stok miktarına göre önceliklendir", 
            variable=self.prioritize_by_stock
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=20, pady=5)
        row += 1
        
        ttk.Label(frame, text="(Her ikisi veya hiçbiri seçilirse mevcut sıralama kullanılır)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=40
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Not:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Bu hedefler karşılanmazsa, sistem uyarı verecek", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="ve best-effort modda devam etmek isteyip istemediğinizi soracaktır.", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=20
        )
    
    def _attach_entry_context_menu(self, entry):
        """Attach right-click context menu with Cut/Copy/Paste/Select All to Entry widget"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Kes\tCtrl+X", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Kopyala\tCtrl+C", command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="Yapıştır\tCtrl+V", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Tümünü Seç\tCtrl+A", command=lambda: (entry.select_range(0, 'end'), entry.icursor('end')))
        
        def show_menu(event):
            entry.focus_set()
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        
        entry.bind("<Button-3>", show_menu)
        entry.bind("<Control-a>", lambda e: (entry.select_range(0, 'end'), entry.icursor('end'), 'break'))
        entry.bind("<Control-Insert>", lambda e: (entry.event_generate("<<Copy>>"), 'break'))
        entry.bind("<Shift-Insert>", lambda e: (entry.event_generate("<<Paste>>"), 'break'))
        entry.bind("<Shift-Delete>", lambda e: (entry.event_generate("<<Cut>>"), 'break'))
    
    def create_preferred_tab(self, notebook):
        """Preferred FIRST Products tab (up to 10 rows)"""
        scroll_frame = ScrollableFrame(notebook)
        notebook.add(scroll_frame, text="Tercihli FIRST Ürünler")
        frame = scroll_frame.scrollable_frame
        
        row = 0
        
        ttk.Label(frame, text="Tercihli FIRST Ürünler (İsteğe Bağlı):", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Bu ürünler FIRST olarak plana dahil edilmeye çalışılacaktır.", font=("Arial", 9)).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="Gün+Saat seçilirse: O gün o saatte kullanılır (hard constraint)", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="Sadece KisaKod+Renk girilirse: Herhangi bir günde kullanılır", font=("Arial", 8, "italic")).grid(
            row=row, column=0, columnspan=6, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="#", font=("Arial", 9, "bold"), width=3).grid(
            row=row, column=0, sticky=tk.W, padx=(0, 2)
        )
        ttk.Label(frame, text="Aksiyon", font=("Arial", 9, "bold"), width=15).grid(
            row=row, column=1, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(frame, text="KisaKod+Renk", font=("Arial", 9, "bold"), width=20).grid(
            row=row, column=2, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(frame, text="Gün", font=("Arial", 9, "bold"), width=15).grid(
            row=row, column=3, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(frame, text="Saat", font=("Arial", 9, "bold"), width=10).grid(
            row=row, column=4, sticky=tk.W, padx=(0, 5)
        )
        ttk.Label(frame, text="Durum", font=("Arial", 9, "bold"), width=30).grid(
            row=row, column=5, sticky=tk.W, padx=(0, 5)
        )
        row += 1
        
        gun_options = ["", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        weekday_times = ["", "09:00", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:30", "17:30", "19:30", "21:00", "22:30"]
        weekend_times = ["", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:30", "19:30", "21:00"]
        
        self.preferred_entries = []
        for i in range(10):
            kisakodrenk_var = tk.StringVar()
            gun_var = tk.StringVar()
            time_var = tk.StringVar()
            force_use_var = tk.BooleanVar(value=False)
            
            ttk.Label(frame, text=f"{i+1}.", font=("Arial", 9)).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 2), pady=2
            )
            
            # Havuza ekle/çıkar butonu (başlangıçta gizli, KisaKod+Renk solunda)
            # Bu buton duruma göre "Yine de Havuza Ekle" veya "Havuzdan Çıkar" olacak
            pool_button = ttk.Button(
                frame,
                text="Yine de Havuza Ekle",
                command=lambda idx=i: self.toggle_preferred_product_in_pool(idx),
                width=15
            )
            pool_button.grid(row=row, column=1, sticky=tk.W, padx=(0, 5), pady=2)
            pool_button.grid_remove()  # Başlangıçta gizli
            
            kisakodrenk_entry = ttk.Entry(frame, textvariable=kisakodrenk_var, width=20)
            kisakodrenk_entry.grid(row=row, column=2, sticky=tk.W, padx=(0, 5), pady=2)
            self._attach_entry_context_menu(kisakodrenk_entry)
            
            gun_combo = ttk.Combobox(frame, textvariable=gun_var, width=15, state="readonly", values=gun_options)
            gun_combo.grid(row=row, column=3, sticky=tk.W, padx=(0, 5), pady=2)
            
            time_combo = ttk.Combobox(frame, textvariable=time_var, width=10, state="readonly")
            time_combo.grid(row=row, column=4, sticky=tk.W, padx=(0, 5), pady=2)
            
            def on_gun_change(event, gun_v=gun_var, time_v=time_var, time_c=time_combo, wdt=weekday_times, wet=weekend_times):
                gun = gun_v.get()
                if not gun:
                    time_c['values'] = [""]
                    time_v.set("")
                    time_c['state'] = 'disabled'
                elif gun in ["Cumartesi", "Pazar"]:
                    time_c['values'] = wet
                    time_c['state'] = 'readonly'
                else:
                    time_c['values'] = wdt
                    time_c['state'] = 'readonly'
            
            gun_combo.bind('<<ComboboxSelected>>', on_gun_change)
            time_combo['state'] = 'disabled'
            
            # Durum label'ı (scrollable)
            status_frame = ttk.Frame(frame)
            status_frame.grid(row=row, column=4, sticky=(tk.W, tk.E), padx=(0, 5), pady=2)
            
            # ttk.Frame doesn't support bg option, use system default or parent's bg
            try:
                parent_bg = frame.winfo_toplevel().cget('bg')
            except:
                parent_bg = 'SystemButtonFace'  # Windows default
            status_canvas = tk.Canvas(status_frame, height=20, highlightthickness=0, bg=parent_bg)
            status_scrollbar = ttk.Scrollbar(status_frame, orient="horizontal", command=status_canvas.xview)
            status_canvas.configure(xscrollcommand=status_scrollbar.set)
            
            status_label = ttk.Label(status_canvas, text="", font=("Arial", 8), foreground="gray", anchor="w")
            status_canvas_window = status_canvas.create_window((0, 0), window=status_label, anchor="nw")
            
            def configure_status_scroll(event=None):
                status_canvas.update_idletasks()
                bbox = status_canvas.bbox("all")
                if bbox:
                    status_canvas.configure(scrollregion=bbox)
                    # Scrollbar'ı sadece gerektiğinde göster
                    canvas_width = status_canvas.winfo_width()
                    if canvas_width > 1 and bbox[2] > canvas_width:
                        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    else:
                        status_scrollbar.pack_forget()
            
            status_label.bind("<Configure>", configure_status_scroll)
            status_canvas.bind("<Configure>", lambda e: configure_status_scroll())
            
            status_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Store update function for later use
            status_update_scroll = configure_status_scroll
            
            # "Yine de Kullan" butonu (başlangıçta gizli)
            force_use_button = ttk.Button(
                frame,
                text="Yine de Kullan",
                command=lambda idx=i: self.force_use_preferred_product(idx),
                width=15
            )
            force_use_button.grid(row=row, column=5, sticky=tk.W, padx=(0, 0), pady=2)
            force_use_button.grid_remove()  # Başlangıçta gizli
            
            self.preferred_entries.append({
                'kisakodrenk': kisakodrenk_var,
                'kisakodrenk_entry': kisakodrenk_entry,
                'gun': gun_var,
                'time': time_var,
                'gun_combo': gun_combo,
                'time_combo': time_combo,
                'status_label': status_label,
                'status_frame': status_frame,
                'status_canvas': status_canvas,
                'status_scrollbar': status_scrollbar,
                'status_update_scroll': status_update_scroll,  # Scrollbar güncelleme fonksiyonu
                'pool_button': pool_button,  # Tek buton: "Yine de Havuza Ekle" veya "Havuzdan Çıkar"
                'in_pool': False,  # Havuzda mı değil mi
                'force_use': force_use_var
            })
            
            row += 1
        
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10
        )
        row += 1
        
        ttk.Label(frame, text="Önemli Notlar:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, pady=5
        )
        row += 1
        
        ttk.Label(frame, text="• Saat seçilirse gün de seçilmelidir (zorunlu)", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="• Gün plan aralığı içinde olmalıdır", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, padx=20
        )
        row += 1
        
        ttk.Label(frame, text="• Tercihli ürünler tüm FIRST kriterlerine uymalıdır", font=("Arial", 8)).grid(
            row=row, column=0, columnspan=5, sticky=tk.W, padx=20
        )
        row += 1
        
        # KRİTERLERE UYGUN MU butonu
        ttk.Button(
            frame,
            text="KRİTERLERE UYGUN MU",
            command=self.check_preferred_products_criteria,
            width=25
        ).grid(row=row, column=0, columnspan=5, pady=10)
        row += 1
        
        # Action buttons at the bottom
        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(20, 10)
        )
        row += 1
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=10)
        
        # Ayarları Sıfırla butonu (sol taraf) - tk.Button for better color support
        gray_button = tk.Button(
            button_frame,
            text="Ayarları Sıfırla",
            command=self.reset_settings,
            bg="#808080",
            fg="white",
            font=("Arial", 10),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=10,
            pady=6
        )
        gray_button.pack(side=tk.LEFT, padx=5)
        gray_button.bind("<Enter>", lambda e: gray_button.config(bg="#6a6a6a"))
        gray_button.bind("<Leave>", lambda e: gray_button.config(bg="#808080"))
        
        # Planı Oluştur butonu (sağ taraf, %50 büyük) - tk.Button for better color support
        green_button = tk.Button(
            button_frame,
            text="Planı Oluştur",
            command=self.run_planner,
            bg="#2d8659",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=2,
            cursor="hand2",
            padx=15,
            pady=8
        )
        green_button.pack(side=tk.RIGHT, padx=5)
        green_button.bind("<Enter>", lambda e: green_button.config(bg="#1f5f3f"))
        green_button.bind("<Leave>", lambda e: green_button.config(bg="#2d8659"))
    
    def check_preferred_products_criteria(self):
        """Check if preferred products meet FIRST criteria"""
        if self.raw_df is None or self.raw_df.empty:
            for entry in self.preferred_entries:
                entry['status_label'].config(
                    text="Excel dosyası yüklenmedi",
                    foreground="red"
                )
            return
        
        try:
            from instagram_auto_post import build_unique_products, filter_first_products, build_post_calendar
            from instagram_auto_post import check_yazlik_kislik, check_one_atilma_tarihi_front, check_size_stock_rules
            
            # Config topla ve dict'e çevir
            config_obj = self.collect_config()
            cfg = config_obj.to_dict()
            
            # Unique products oluştur
            unique_products = build_unique_products(self.raw_df)
            
            # Takvim oluştur
            calendar = build_post_calendar(cfg)
            cfg_with_calendar = cfg.copy()
            cfg_with_calendar["_calendar_for_pool"] = calendar
            
            # FIRST havuzunu hesapla
            first_candidates = filter_first_products(unique_products, cfg_with_calendar)
            first_pool_kisakodrenk = set(first_candidates["kisakodrenk"].str.upper().str.strip())
            
            # Her tercihli ürün için kontrol et
            for idx, entry in enumerate(self.preferred_entries):
                kisakodrenk = entry['kisakodrenk'].get().strip().upper()
                status_label = entry.get('status_label')
                if not status_label:
                    continue
                
                if not kisakodrenk:
                    status_label.config(text="", foreground="gray")
                    # Butonu gizle
                    pool_button = entry.get('pool_button')
                    if pool_button:
                        pool_button.grid_remove()
                    entry['in_pool'] = False
                    continue
                
                # Eğer ürün zaten havuza eklenmişse, durumu göster
                if entry.get('in_pool', False):
                    status_label.config(
                        text="✓ Havuza Eklendi",
                        foreground="green"
                    )
                    # Scrollbar'ı güncelle
                    update_scroll = entry.get('status_update_scroll')
                    if update_scroll:
                        self.root.after(10, update_scroll)
                    # Butonu "Havuzdan Çıkar" olarak göster
                    pool_button = entry.get('pool_button')
                    if pool_button:
                        pool_button.config(text="Havuzdan Çıkar")
                        pool_button.grid()
                    continue
                
                # Ürünün unique_products'ta olup olmadığını kontrol et
                product_row = unique_products[unique_products["kisakodrenk"].str.upper().str.strip() == kisakodrenk]
                
                if len(product_row) == 0:
                    status_label.config(
                        text="Havuzda yok: Stok dosyasında bulunamadı",
                        foreground="red"
                    )
                    # Scrollbar'ı güncelle
                    update_scroll = entry.get('status_update_scroll')
                    if update_scroll:
                        self.root.after(10, update_scroll)
                    # "Yine de Havuza Ekle" butonunu göster (stok dosyasında yoksa bile kullanıcı ekleyebilir)
                    pool_button = entry.get('pool_button')
                    if pool_button:
                        pool_button.config(text="Yine de Havuza Ekle")
                        pool_button.grid()
                    continue
                
                product = product_row.iloc[0]
                
                # Ürünün FIRST havuzunda olup olmadığını kontrol et
                if kisakodrenk in first_pool_kisakodrenk:
                    # Uygun olan ürünü otomatik havuza ekle
                    if not entry.get('in_pool', False):
                        entry['in_pool'] = True
                    
                    status_label.config(
                        text="✓ Havuza Eklendi",
                        foreground="green"
                    )
                    # Butonu "Havuzdan Çıkar" olarak göster
                    pool_button = entry.get('pool_button')
                    if pool_button:
                        pool_button.config(text="Havuzdan Çıkar")
                        pool_button.grid()
                    # Scrollbar'ı güncelle
                    update_scroll = entry.get('status_update_scroll')
                    if update_scroll:
                        self.root.after(10, update_scroll)
                    continue
                
                # Hangi kriterleri sağlamadığını kontrol et
                failed_criteria = []
                
                # Mevsim kontrolü
                use_yazlik = cfg.get("use_yazlik_front", False)
                use_kislik = cfg.get("use_kislik_front", False)
                if use_yazlik or use_kislik:
                    try:
                        if not check_yazlik_kislik(product, use_yazlik, use_kislik):
                            failed_criteria.append("Mevsim")
                    except Exception as e:
                        print(f"DEBUG: Mevsim kontrolü hatası: {e}")
                        failed_criteria.append("Mevsim")
                
                # Çekim kontrolü
                allowed_cekim = cfg.get("allowed_cekim_front", [])
                if allowed_cekim:
                    cekim_val = str(product.get("Cekim", "")).strip().upper()
                    if cekim_val not in [c.upper() for c in allowed_cekim]:
                        failed_criteria.append("Çekim")
                
                # One Atilma Tarihi kontrolü
                if not check_one_atilma_tarihi_front(product, cfg):
                    failed_criteria.append("Öne Atılma Tarihi")
                
                # Min stok kontrolü
                min_stock = cfg.get("min_total_stock_front", 0)
                if product.get("total_stock", 0) < min_stock:
                    failed_criteria.append(f"Min Stok ({min_stock})")
                
                # Beden/stok kuralları kontrolü
                front_size_stock_rules = cfg.get("front_size_stock_rules", [])
                if front_size_stock_rules:
                    size_stocks = product.get("size_stocks", [])
                    if not check_size_stock_rules(size_stocks, front_size_stock_rules):
                        failed_criteria.append("Beden/Stok Kuralları")
                
                # Gelişmiş kısıtlar kontrolü (havuz seviyesinde)
                max_black = cfg.get("max_black_first_per_day", 0)
                max_kisakod = cfg.get("max_first_uses_per_kisakod", 0)
                if max_black > 0 or max_kisakod > 0:
                    # Bu kısıtlar havuz seviyesinde kontrol edilir, ama tek bir ürün için kontrol edemeyiz
                    # Sadece havuzda olmadığını biliyoruz
                    pass
                
                # Durum mesajı
                if failed_criteria:
                    criteria_text = ", ".join(failed_criteria)
                    status_label.config(
                        text=f"Havuzda yok: {criteria_text} sağlamıyor",
                        foreground="red"
                    )
                else:
                    status_label.config(
                        text="Havuzda yok: Gelişmiş kısıtlar nedeniyle",
                        foreground="orange"
                    )
                
                # Scrollbar'ı güncelle
                update_scroll = entry.get('status_update_scroll')
                if update_scroll:
                    self.root.after(10, update_scroll)
                
                # "Yine de Havuza Ekle" butonunu göster (eğer havuza eklenmemişse)
                if not entry.get('in_pool', False):
                    pool_button = entry.get('pool_button')
                    if pool_button:
                        pool_button.config(text="Yine de Havuza Ekle")
                        pool_button.grid()
        
        except Exception as e:
            import traceback
            error_msg = f"Hata: {str(e)}"
            print(f"ERROR in check_preferred_products_criteria: {e}")
            print(traceback.format_exc())
            for entry in self.preferred_entries:
                entry['status_label'].config(
                    text=error_msg,
                    foreground="red"
                )
    
    def toggle_preferred_product_in_pool(self, idx):
        """Toggle preferred product in/out of pool"""
        if idx < 0 or idx >= len(self.preferred_entries):
            return
        
        entry = self.preferred_entries[idx]
        kisakodrenk = entry['kisakodrenk'].get().strip().upper()
        
        if not kisakodrenk:
            import tkinter.messagebox as messagebox
            messagebox.showwarning("Uyarı", "Lütfen önce KisaKod+Renk girin.")
            return
        
        old_in_pool = entry.get('in_pool', False)
        print(f"DEBUG: toggle_preferred_product_in_pool - kisakodrenk: {kisakodrenk}, old in_pool: {old_in_pool}")
        
        # Toggle havuz durumu
        if old_in_pool:
            # Havuzdan çıkar
            entry['in_pool'] = False
            entry['status_label'].config(
                text="Havuzdan çıkarıldı",
                foreground="gray"
            )
            # Scrollbar'ı güncelle
            update_scroll = entry.get('status_update_scroll')
            if update_scroll:
                self.root.after(10, update_scroll)
            # Butonu "Yine de Havuza Ekle" olarak güncelle
            pool_button = entry.get('pool_button')
            if pool_button:
                pool_button.config(text="Yine de Havuza Ekle")
                pool_button.grid()
        else:
            # Havuza ekle
            entry['in_pool'] = True
            entry['status_label'].config(
                text="✓ Havuza Eklendi",
                foreground="green"
            )
            # Scrollbar'ı güncelle
            update_scroll = entry.get('status_update_scroll')
            if update_scroll:
                self.root.after(10, update_scroll)
            # Butonu "Havuzdan Çıkar" olarak güncelle
            pool_button = entry.get('pool_button')
            if pool_button:
                pool_button.config(text="Havuzdan Çıkar")
                pool_button.grid()
        
        # Havuz boyutunu güncelle (tercihli ürünler havuz boyutunu etkileyebilir)
        new_in_pool = entry.get('in_pool', False)
        print(f"DEBUG: toggle_preferred_product_in_pool - Yeni in_pool değeri: {new_in_pool}")
        
        if self.raw_df is not None and not self.raw_df.empty:
            # Havuz boyutunu yeniden hesapla
            print(f"DEBUG: toggle_preferred_product_in_pool - Havuz boyutu güncelleniyor (kisakodrenk: {kisakodrenk}, in_pool: {new_in_pool})")
            # Verify that the entry's in_pool value is correctly set
            print(f"DEBUG: toggle_preferred_product_in_pool - Entry in_pool value after toggle: {entry.get('in_pool', False)}")
            self.update_all_pool_sizes(immediate=True)
        else:
            print(f"DEBUG: toggle_preferred_product_in_pool - raw_df is None or empty, havuz boyutu güncellenemiyor")
    
    def check_daily_constraints(self):
        """Check if daily constraints are feasible for placement (kept for backward compatibility)"""
        self.pre_report_validation()
    
    def pre_report_validation(self):
        """Ön yerleştirme simülasyonu yap ve tüm kriterleri kontrol et"""
        import tkinter.messagebox as messagebox
        
        if self.raw_df is None or self.raw_df.empty:
            messagebox.showwarning(
                "Excel Dosyası Yüklenmedi",
                "Lütfen önce Excel dosyasını yükleyin."
            )
            return
        
        try:
            from instagram_auto_post import (
                build_unique_products, 
                filter_first_products, 
                filter_back_products,
                build_post_calendar,
                assign_first_products,
                assign_back_products,
                check_advanced_first_constraints,
                check_weekly_nos_dvm
            )
            from validator import PlanValidator
            
            # Config topla
            config_obj = self.collect_config()
            cfg = config_obj.to_dict()
            
            # Takvim oluştur
            calendar = build_post_calendar(cfg)
            cfg_with_calendar = cfg.copy()
            cfg_with_calendar["_calendar_for_pool"] = calendar
            
            # Havuzları oluştur
            unique_products = build_unique_products(self.raw_df)
            first_candidates = filter_first_products(unique_products, cfg_with_calendar)
            back_candidates = filter_back_products(unique_products, cfg_with_calendar)
            
            if len(first_candidates) == 0:
                messagebox.showwarning(
                    "Yerleştirme Yapılamıyor",
                    "FIRST ürün havuzu boş. Kriterleri yumuşatın."
                )
                return
            
            if len(back_candidates) == 0:
                messagebox.showwarning(
                    "Yerleştirme Yapılamıyor",
                    "BACK ürün havuzu boş. Kriterleri yumuşatın."
                )
                return
            
            # Ön yerleştirme simülasyonu
            # decide callback'i True döndürerek tüm kontrolleri geç
            def auto_decide(msg):
                return True
            
            # FIRST ürünleri ata
            trial_posts = assign_first_products(calendar, first_candidates, cfg, decide=auto_decide)
            
            if not trial_posts or len(trial_posts) < len(calendar):
                missing = len(calendar) - (len(trial_posts) if trial_posts else 0)
                messagebox.showwarning(
                    "Yerleştirme Yapılamıyor",
                    f"FIRST ürün ataması başarısız.\n\n"
                    f"Gerekli: {len(calendar)} post\n"
                    f"Atanan: {len(trial_posts) if trial_posts else 0} post\n"
                    f"Eksik: {missing} post\n\n"
                    f"Kriterleri yumuşatın veya havuz boyutunu artırın."
                )
                return
            
            # BACK ürünleri ata
            trial_posts = assign_back_products(trial_posts, back_candidates, cfg)
            
            # İhlalleri topla (kategorize edilmiş)
            all_violations = []  # [(kategori_adi, [ihlal_listesi]), ...]
            
            # 1. Gelişmiş FIRST kısıtları ihlalleri
            advanced_violations = []
            try:
                from validator import compute_black_first_counts_by_day, compute_first_uses_per_kisakod
                max_black_per_day = cfg.get("max_black_first_per_day", 0)
                max_kisakod_uses = cfg.get("max_first_uses_per_kisakod", 0)
                
                if max_black_per_day > 0:
                    # Tercihli ürünleri ihlal kontrolünden hariç tut
                    black_counts = compute_black_first_counts_by_day(trial_posts, cfg)
                    for day_name, count in black_counts.items():
                        if count > max_black_per_day:
                            advanced_violations.append(
                                f"Günlük SİYAH FIRST limiti: {day_name} günü {count} adet (limit: {max_black_per_day})"
                            )
                
                if max_kisakod_uses > 0:
                    # Tercihli ürünleri ihlal kontrolünden hariç tut
                    kisakod_counts = compute_first_uses_per_kisakod(trial_posts, cfg)
                    for kisakod, count in kisakod_counts.items():
                        if count > max_kisakod_uses:
                            advanced_violations.append(
                                f"KisaKod FIRST kullanım limiti: {kisakod} {count} kez (limit: {max_kisakod_uses})"
                            )
            except Exception as e:
                advanced_violations.append(f"Gelişmiş kısıt kontrolü hatası: {str(e)}")
            
            if advanced_violations:
                all_violations.append(("Gelişmiş FIRST Kısıtları", advanced_violations))
            
            # 2. NOS/DVM ihlalleri (sadece aktif kısıtlar için)
            nos_dvm_violations = []
            try:
                min_nos = cfg.get("min_nos_front", 0)
                min_dvm = cfg.get("min_dvm_front", 0)
                
                # Sadece aktif kısıtları kontrol et (0 değerli kısıtlar kısıt yok demektir)
                if min_nos > 0:
                    nos_first_plan = {
                        p["first_product"]["kisakodrenk"]
                        for p in trial_posts
                        if p.get("first_product", {}).get("Nos", "") == "E"
                    }
                    if len(nos_first_plan) < min_nos:
                        nos_dvm_violations.append(
                            f"NOS FIRST sayısı: {len(nos_first_plan)} (hedef: {min_nos})"
                        )
                
                if min_dvm > 0:
                    dvm_first_plan = {
                        p["first_product"]["kisakodrenk"]
                        for p in trial_posts
                        if p.get("first_product", {}).get("DVM", "") == "DVM"
                    }
                    if len(dvm_first_plan) < min_dvm:
                        nos_dvm_violations.append(
                            f"DVM FIRST sayısı: {len(dvm_first_plan)} (hedef: {min_dvm})"
                        )
            except Exception as e:
                nos_dvm_violations.append(f"NOS/DVM kontrolü hatası: {str(e)}")
            
            if nos_dvm_violations:
                all_violations.append(("NOS/DVM Kısıtları", nos_dvm_violations))
            
            # 3. Validator ihlalleri (iyileştirilmiş hata yönetimi)
            validation_results = []
            failed_results = []
            validator_errors = []
            try:
                import re
                validator = PlanValidator(trial_posts, cfg, first_candidates, back_candidates)
                validation_results = validator.validate_all()
                
                # Sadece gerçekten aktif olan kriterlerin ihlallerini göster
                # 0 değerli kriterler "kısıt yok" anlamına gelir, bunları ihlal olarak sayma
                for r in validation_results:
                    if r.durum == "FAILED":
                        beklenen = r.beklenen_deger
                        kriter_adi = r.kriter_adi.lower()
                        
                        # 0 değerli kriterleri filtrele
                        # Örnek: ">= 0" veya "<= 0" veya "Her gün >= 0" veya "Tüm FIRST ürünler >= 0" gibi
                        if ">= 0" in beklenen or "<= 0" in beklenen or "kısıt yok" in beklenen.lower():
                            continue
                        
                        # Beklenen değerden sayıyı çıkar (regex ile)
                        # Örnek: ">= 5", "Her gün >= 3", "Tüm FIRST ürünler >= 10"
                        match = re.search(r'>= (\d+(?:\.\d+)?)', beklenen)
                        if match:
                            target_value = float(match.group(1))
                            # Eğer hedef değer 0 ise, bu kısıt yok demektir, atla
                            if target_value == 0:
                                continue
                        
                        # Bu gerçek bir ihlal (hedef değer > 0 ve gerçekleşen < hedef)
                        failed_results.append(r)
            except KeyError as e:
                # Eksik veri alanı
                validator_errors.append(f"Eksik veri alanı: {str(e)}")
            except AttributeError as e:
                # Veri yapısı hatası
                validator_errors.append(f"Veri yapısı hatası: {str(e)}")
            except ValueError as e:
                # Değer dönüştürme hatası
                validator_errors.append(f"Değer dönüştürme hatası: {str(e)}")
            except Exception as e:
                # Diğer hatalar
                validator_errors.append(f"Validator hatası: {type(e).__name__}: {str(e)}")
            
            if validator_errors:
                all_violations.append(("Validator Hataları", validator_errors))
            
            # 4. Sonuç mesajı oluştur (kategorize edilmiş)
            total_posts = len(trial_posts)
            required_first = len(calendar)
            placed_first = sum(1 for p in trial_posts if p.get("first_product"))
            required_back = len(calendar) * 9
            placed_back = sum(len(p.get("back_products", [])) for p in trial_posts)
            
            if all_violations or failed_results:
                message = "⚠️ Simülasyon Tamamlandı - İhlal Raporu\n\n"
                message += "=" * 50 + "\n\n"
                
                # Kategorize edilmiş ihlaller
                for category, violations in all_violations:
                    message += f"📋 {category}:\n"
                    for violation in violations[:5]:  # İlk 5'ini göster
                        message += f"  • {violation}\n"
                    if len(violations) > 5:
                        message += f"  ... ve {len(violations) - 5} ihlal daha\n"
                    message += "\n"
                
                # Validator başarısız kriterleri
                if failed_results:
                    message += "📋 Validator Başarısız Kriterler:\n"
                    for result in failed_results[:10]:
                        message += f"  • {result.kriter_adi}: {result.gerceklesen_deger}\n"
                        if result.notlar:
                            message += f"    ({result.notlar})\n"
                    if len(failed_results) > 10:
                        message += f"  ... ve {len(failed_results) - 10} kriter daha\n"
                    message += "\n"
                
                message += "=" * 50 + "\n\n"
                message += "Simülasyon Sonuçları:\n"
                message += f"• Toplam post: {total_posts}\n"
                message += f"• FIRST ürün: {placed_first}/{required_first}\n"
                message += f"• BACK ürün: {placed_back}/{required_back}\n"
                message += "\nKriterleri yumuşatın veya havuz boyutunu artırın."
                
                messagebox.showwarning("Simülasyon İhlal Raporu", message)
            else:
                # Başarılı kriterleri özetle
                passed_count = len([r for r in validation_results if r.durum == "OK"]) if validation_results else 0
                
                message = "✓ Tüm kriterler karşılandı!\n\n"
                message += f"Simülasyon Sonuçları:\n"
                message += f"• Toplam post: {total_posts}\n"
                message += f"• FIRST ürün: {placed_first}/{required_first}\n"
                message += f"• BACK ürün: {placed_back}/{required_back}\n"
                if validation_results:
                    message += f"• Kontrol edilen kriter: {len(validation_results)}\n"
                    message += f"• Başarılı kriter: {passed_count}\n"
                message += "\nRaporu başlatabilirsiniz."
                messagebox.showinfo("Rapor Öncesi Kontrol Başarılı", message)
                
        except Exception as e:
            import traceback
            error_msg = f"Hata oluştu: {str(e)}\n\n{traceback.format_exc()}"
            print(f"ERROR in pre_report_validation: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Hata", error_msg)
    
    def create_output_tab(self, notebook):
        """Output and Status tab"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Çıktı ve Durum")
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            width=80,
            height=30,
            font=("Courier", 9)
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu for copy/paste
        output_menu = tk.Menu(self.root, tearoff=0)
        output_menu.add_command(label="Kopyala\tCtrl+C", command=lambda: self._copy_output_text())
        output_menu.add_command(label="Tümünü Seç\tCtrl+A", command=lambda: self._select_all_output())
        output_menu.add_separator()
        output_menu.add_command(label="Temizle", command=lambda: self.clear_output())
        
        def show_output_menu(event):
            try:
                output_menu.tk_popup(event.x_root, event.y_root)
            finally:
                output_menu.grab_release()
        
        self.output_text.bind("<Button-3>", show_output_menu)  # Right-click
        self.output_text.bind("<Control-c>", lambda e: (self._copy_output_text(), 'break'))  # Ctrl+C
        self.output_text.bind("<Control-a>", lambda e: (self._select_all_output(), 'break'))  # Ctrl+A
    
    def _copy_output_text(self):
        """Copy selected text from output text widget to clipboard"""
        try:
            if self.output_text.tag_ranges(tk.SEL):
                # If text is selected, copy it
                text = self.output_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                # If no text is selected, copy all
                text = self.output_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as e:
            print(f"Error copying text: {e}")
    
    def _select_all_output(self):
        """Select all text in output text widget"""
        self.output_text.tag_add(tk.SEL, "1.0", tk.END)
        self.output_text.mark_set(tk.INSERT, "1.0")
        self.output_text.see(tk.INSERT)
    
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Stok Dosyasını Seç",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filename:
            self.excel_path.set(filename)
            self.append_output(f"Dosya seçildi: {filename}\n")
            # Load raw_df for pool calculations
            try:
                import pandas as pd
                print(f"DEBUG: Excel dosyası yükleniyor: {filename}")
                print(f"DEBUG: Dosya var mı? {os.path.exists(filename)}")
                
                # Try with openpyxl engine first (for .xlsx files)
                try:
                    self.raw_df = pd.read_excel(filename, engine="openpyxl")
                except Exception as e1:
                    print(f"DEBUG: openpyxl engine ile yüklenemedi: {e1}")
                    # Try without engine (for .xls files)
                    try:
                        self.raw_df = pd.read_excel(filename)
                    except Exception as e2:
                        print(f"DEBUG: Varsayılan engine ile de yüklenemedi: {e2}")
                        raise e2
                
                print(f"DEBUG: Excel dosyası yüklendi. Satır sayısı: {len(self.raw_df)}")
                print(f"DEBUG: Sütunlar: {list(self.raw_df.columns)}")
                print(f"DEBUG: raw_df type: {type(self.raw_df)}")
                print(f"DEBUG: raw_df is None? {self.raw_df is None}")
                print(f"DEBUG: raw_df.empty? {hasattr(self.raw_df, 'empty') and self.raw_df.empty}")
                
                if self.raw_df is None:
                    print("DEBUG: ERROR - raw_df None!")
                    self.append_output("HATA: Excel dosyası yüklenemedi (None döndü)\n")
                    self.raw_df = None
                elif hasattr(self.raw_df, 'empty') and self.raw_df.empty:
                    print("DEBUG: WARNING - raw_df boş!")
                    self.append_output("UYARI: Excel dosyası boş görünüyor!\n")
                    self.raw_df = None
                else:
                    print(f"DEBUG: raw_df başarıyla yüklendi, {len(self.raw_df)} satır var")
                    print(f"DEBUG: raw_df object ID: {id(self.raw_df)}")
                    print(f"DEBUG: raw_df columns: {list(self.raw_df.columns)}")
                    self.append_output(f"Excel dosyası başarıyla yüklendi: {len(self.raw_df)} satır\n")
                
                # Don't update pool sizes automatically - wait for user to select criteria
                # Pool sizes will be calculated when user changes any filter criteria
            except Exception as e:
                error_msg = f"Excel dosyası yüklenirken hata: {str(e)}"
                print(f"ERROR loading Excel for pool calculation: {e}")
                import traceback
                traceback.print_exc()
                self.raw_df = None
                self.append_output(f"HATA: {error_msg}\n")
                # Show error message in pool labels
                if hasattr(self, 'first_pool_size_label') and self.first_pool_size_label:
                    self.first_pool_size_label.config(
                        text=f"FIRST Havuz Boyutu: {error_msg}",
                        foreground="red"
                    )
                if hasattr(self, 'back_pool_size_label') and self.back_pool_size_label:
                    self.back_pool_size_label.config(
                        text=f"BACK Havuz Boyutu: {error_msg}",
                        foreground="red"
                    )
    
    def calculate_required_counts(self):
        """Calculate required FIRST and BACK counts based on plan length and daily post counts"""
        start_day_name = self.start_day.get()
        num_days = self.num_days.get()
        
        # Weekday: 12 posts/day, Weekend: 10 posts/day
        weekday_times = [
            "09:00", "10:30", "11:30", "12:30", "13:30", "14:30",
            "15:30", "16:30", "17:30", "19:30", "21:00", "22:30",
        ]
        weekend_times = [
            "11:00", "12:00", "13:00", "14:00", "15:00",
            "16:00", "17:00", "18:30", "19:30", "21:00",
        ]
        
        TURKISH_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        
        if start_day_name not in TURKISH_DAYS:
            return 0, 0
        
        start_idx = TURKISH_DAYS.index(start_day_name)
        total_slots = 0
        
        for i in range(num_days):
            day_idx = (start_idx + i) % 7
            is_weekend = day_idx in (5, 6)  # Cumartesi, Pazar
            times = weekend_times if is_weekend else weekday_times
            total_slots += len(times)
        
        required_first = total_slots
        required_back = total_slots * 9
        
        return required_first, required_back
    
    def update_required_counts(self):
        """Update the required counts display"""
        required_first, required_back = self.calculate_required_counts()
        text = f"""Plan Uzunluğu: {self.num_days.get()} gün (Başlangıç: {self.start_day.get()})
Gerekli FIRST Post Sayısı: {required_first}
Gerekli BACK Ürün Sayısı: {required_back}"""
        if hasattr(self, 'required_counts_label') and self.required_counts_label:
            self.required_counts_label.config(text=text)
        # Otomatik havuz hesaplama kaldırıldı - kullanıcı "Havuz Hesapla" butonuna basarak manuel olarak hesaplayacak
    
    def calculate_first_pool_size(self, raw_df=None):
        """Calculate current FIRST pool size based on all active criteria"""
        # Use provided raw_df or fall back to self.raw_df
        df_to_use = raw_df if raw_df is not None else self.raw_df
        
        if df_to_use is None:
            print("DEBUG: calculate_first_pool_size - raw_df is None")
            return None
        
        try:
            if hasattr(df_to_use, 'empty') and df_to_use.empty:
                print("DEBUG: calculate_first_pool_size - raw_df is empty")
                return 0
        except Exception:
            pass  # Continue if empty check fails
        
        try:
            print(f"DEBUG: calculate_first_pool_size - df_to_use ID: {id(df_to_use)}, rows: {len(df_to_use)}, columns: {list(df_to_use.columns)}")
            
            # Check required columns before proceeding
            required_cols = ["KisaKod", "Renk", "ToplamStok", "Sezon", "Nos", "DVM", "Cekim", "UrunCinsi"]
            missing_cols = [col for col in required_cols if col not in df_to_use.columns]
            if missing_cols:
                print(f"ERROR: Missing required columns: {missing_cols}")
                print(f"DEBUG: Available columns: {list(df_to_use.columns)}")
                return None
            
            from instagram_auto_post import build_unique_products, filter_first_products, build_post_calendar
            
            # Force print to console immediately
            import sys
            if sys.stdout:
                sys.stdout.flush()
            
            # In thread context, redirect print() to GUI output
            import io
            
            class PrintCapture:
                def __init__(self, gui_instance):
                    self.gui = gui_instance
                    self.original_stdout = sys.stdout if sys.stdout else None
                    self.buffer = []
                
                def write(self, text):
                    if text and text.strip():  # Only capture non-empty lines
                        self.buffer.append(text)
                        # Use root.after to safely update GUI from thread
                        # Capture text in closure to avoid lambda capture issues
                        text_copy = text
                        self.gui.root.after(0, lambda: self.gui.append_output(text_copy))
                    if self.original_stdout:
                        try:
                            self.original_stdout.write(text)
                        except:
                            pass
                
                def flush(self):
                    if self.original_stdout:
                        try:
                            self.original_stdout.flush()
                        except:
                            pass
            
            # Only redirect if we're in a thread (check if we have a root)
            original_stdout = sys.stdout
            print_capture = PrintCapture(self)
            sys.stdout = print_capture
            
            try:
                # Build unique products
                try:
                    unique_products = build_unique_products(df_to_use)
                except Exception as e:
                    error_msg = f"ERROR in build_unique_products: {e}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    # Also write to GUI output
                    self.root.after(0, lambda: self.append_output(f"{error_msg}\n{traceback.format_exc()}\n"))
                    sys.stdout = original_stdout
                    return None
                
                if unique_products is None or unique_products.empty:
                    sys.stdout = original_stdout
                    return 0
                
                # Build calendar for advanced constraints
                try:
                    config_obj = self.collect_config()
                    cfg = config_obj.to_dict()
                    # Debug: Check if preferred_products_in_pool is in cfg
                    if "preferred_products_in_pool" not in cfg:
                        cfg["preferred_products_in_pool"] = []
                    preferred_count = len(cfg.get('preferred_products_in_pool', []))
                    preferred_list = cfg.get('preferred_products_in_pool', [])
                    print(f"DEBUG: collect_config() successful, preferred_products_in_pool count: {preferred_count}")
                    print(f"DEBUG: preferred_products_in_pool list: {preferred_list}")
                    # Debug: Check preferred_entries directly
                    preferred_entries = getattr(self, "preferred_entries", [])
                    in_pool_count = sum(1 for entry in preferred_entries if entry.get('in_pool', False))
                    print(f"DEBUG: preferred_entries count: {len(preferred_entries)}, in_pool count: {in_pool_count}")
                    
                    # Store raw_df in cfg for preferred products lookup if not in unique_products
                    cfg["_raw_df_for_preferred"] = df_to_use
                except Exception as e:
                    error_msg = f"ERROR in collect_config(): {e}"
                    print(error_msg)
                    import traceback
                    traceback_str = traceback.format_exc()
                    traceback.print_exc()
                    # Also write to GUI output with more details
                    detailed_error = f"{error_msg}\n{traceback_str}\n"
                    detailed_error += f"DEBUG: preferred_entries count: {len(getattr(self, 'preferred_entries', []))}\n"
                    self.root.after(0, lambda: self.append_output(detailed_error))
                    sys.stdout = original_stdout
                    return None
                
                try:
                    calendar = build_post_calendar(cfg)
                    cfg["_calendar_for_pool"] = calendar
                except Exception as e:
                    error_msg = f"ERROR in build_post_calendar: {e}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    # Also write to GUI output
                    self.root.after(0, lambda: self.append_output(f"{error_msg}\n{traceback.format_exc()}\n"))
                    sys.stdout = original_stdout
                    return None
                
                # Filter FIRST products (print capture already active)
                try:
                    # Debug: Print cfg keys before filtering
                    print(f"DEBUG: Before filter_first_products, cfg keys: {list(cfg.keys())[:20]}")
                    print(f"DEBUG: preferred_products_in_pool in cfg: {'preferred_products_in_pool' in cfg}")
                    if "preferred_products_in_pool" in cfg:
                        print(f"DEBUG: preferred_products_in_pool value: {cfg['preferred_products_in_pool']}")
                    
                    first_candidates = filter_first_products(unique_products, cfg)
                    pool_size = len(first_candidates) if first_candidates is not None else 0
                    print(f"DEBUG: filter_first_products successful, pool_size: {pool_size}")
                    sys.stdout = original_stdout
                    return pool_size
                except Exception as e:
                    error_msg = f"ERROR in filter_first_products: {e}"
                    print(error_msg)
                    import traceback
                    traceback_str = traceback.format_exc()
                    traceback.print_exc()
                    # Also write to GUI output with more details
                    detailed_error = f"{error_msg}\n{traceback_str}\n"
                    detailed_error += f"DEBUG: unique_products shape: {unique_products.shape if unique_products is not None else 'None'}\n"
                    detailed_error += f"DEBUG: cfg keys: {list(cfg.keys())[:20]}\n"
                    detailed_error += f"DEBUG: preferred_products_in_pool: {cfg.get('preferred_products_in_pool', 'NOT IN CFG')}\n"
                    self.root.after(0, lambda: self.append_output(detailed_error))
                    sys.stdout = original_stdout
                    return None
            finally:
                # Always restore stdout
                sys.stdout = original_stdout
        except KeyError as e:
            error_msg = f"Kolon bulunamadı: {str(e)}. Excel dosyasında gerekli kolonlar eksik olabilir."
            print(f"ERROR calculating FIRST pool size (KeyError): {e}")
            print(f"DEBUG: Available columns: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}")
            import traceback
            traceback.print_exc()
            # Also write to GUI output
            self.root.after(0, lambda: self.append_output(f"FIRST Havuz Hesaplama Hatası: {error_msg}\nMevcut kolonlar: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}\n{traceback.format_exc()}\n"))
            return None
        except Exception as e:
            error_msg = f"Hesaplama hatası: {str(e)}"
            print(f"ERROR calculating FIRST pool size: {e}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            print(f"DEBUG: df_to_use columns: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}")
            import traceback
            traceback.print_exc()
            # Also write to GUI output
            self.root.after(0, lambda: self.append_output(f"FIRST Havuz Hesaplama Hatası: {error_msg}\nHata tipi: {type(e).__name__}\nMevcut kolonlar: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}\n{traceback.format_exc()}\n"))
            return None
    
    def calculate_back_pool_size(self, raw_df=None):
        """Calculate current BACK pool size based on all active criteria"""
        # Use provided raw_df or fall back to self.raw_df
        df_to_use = raw_df if raw_df is not None else self.raw_df
        
        if df_to_use is None:
            print("DEBUG: calculate_back_pool_size - raw_df is None")
            return None
        
        try:
            if hasattr(df_to_use, 'empty') and df_to_use.empty:
                print("DEBUG: calculate_back_pool_size - raw_df is empty")
                return 0
        except Exception:
            pass  # Continue if empty check fails
        
        try:
            print(f"DEBUG: calculate_back_pool_size - df_to_use ID: {id(df_to_use)}, rows: {len(df_to_use)}, columns: {list(df_to_use.columns)}")
            
            from instagram_auto_post import build_unique_products, filter_back_products, build_post_calendar
            
            # Build unique products
            print("DEBUG: Building unique products for BACK...")
            unique_products = build_unique_products(df_to_use)
            if unique_products is None or unique_products.empty:
                print("DEBUG: unique_products is None or empty")
                return 0
            print(f"DEBUG: unique_products created: {len(unique_products)} products")
            
            # Build calendar
            print("DEBUG: Building calendar for BACK...")
            try:
                config_obj = self.collect_config()
                cfg = config_obj.to_dict()
                # Debug: Check if preferred_products_in_pool is in cfg
                if "preferred_products_in_pool" not in cfg:
                    cfg["preferred_products_in_pool"] = []
                print(f"DEBUG: collect_config() successful for BACK, preferred_products_in_pool count: {len(cfg.get('preferred_products_in_pool', []))}")
            except Exception as e:
                error_msg = f"ERROR in collect_config() for BACK: {e}"
                print(error_msg)
                import traceback
                traceback_str = traceback.format_exc()
                traceback.print_exc()
                # Also write to GUI output with more details
                detailed_error = f"{error_msg}\n{traceback_str}\n"
                detailed_error += f"DEBUG: preferred_entries count: {len(getattr(self, 'preferred_entries', []))}\n"
                self.root.after(0, lambda: self.append_output(detailed_error))
                return None
            
            try:
                calendar = build_post_calendar(cfg)
                cfg["_calendar_for_pool"] = calendar
                print(f"DEBUG: Calendar created: {len(calendar)} slots")
            except Exception as e:
                error_msg = f"ERROR in build_post_calendar for BACK: {e}"
                print(error_msg)
                import traceback
                traceback_str = traceback.format_exc()
                traceback.print_exc()
                self.root.after(0, lambda: self.append_output(f"{error_msg}\n{traceback_str}\n"))
                return None
            
            # Filter BACK products
            print("DEBUG: Filtering BACK products...")
            try:
                # Debug: Print cfg keys before filtering
                print(f"DEBUG: Before filter_back_products, cfg keys: {list(cfg.keys())[:20]}")
                
                back_candidates = filter_back_products(unique_products, cfg)
                pool_size = len(back_candidates) if back_candidates is not None else 0
                print(f"DEBUG: filter_back_products successful, pool_size: {pool_size}")
                return pool_size
            except Exception as e:
                error_msg = f"ERROR in filter_back_products: {e}"
                print(error_msg)
                import traceback
                traceback_str = traceback.format_exc()
                traceback.print_exc()
                # Also write to GUI output with more details
                detailed_error = f"{error_msg}\n{traceback_str}\n"
                detailed_error += f"DEBUG: unique_products shape: {unique_products.shape if unique_products is not None else 'None'}\n"
                detailed_error += f"DEBUG: cfg keys: {list(cfg.keys())[:20]}\n"
                self.root.after(0, lambda: self.append_output(detailed_error))
                return None
        except KeyError as e:
            error_msg = f"Kolon bulunamadı: {str(e)}. Excel dosyasında gerekli kolonlar eksik olabilir."
            print(f"ERROR calculating BACK pool size (KeyError): {e}")
            print(f"DEBUG: Available columns: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}")
            import traceback
            traceback.print_exc()
            # Also write to GUI output
            self.root.after(0, lambda: self.append_output(f"BACK Havuz Hesaplama Hatası: {error_msg}\nMevcut kolonlar: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}\n{traceback.format_exc()}\n"))
            return None
        except Exception as e:
            error_msg = f"Hesaplama hatası: {str(e)}"
            print(f"ERROR calculating BACK pool size: {e}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            print(f"DEBUG: df_to_use columns: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}")
            import traceback
            traceback.print_exc()
            # Also write to GUI output
            self.root.after(0, lambda: self.append_output(f"BACK Havuz Hesaplama Hatası: {error_msg}\nHata tipi: {type(e).__name__}\nMevcut kolonlar: {list(df_to_use.columns) if df_to_use is not None else 'N/A'}\n{traceback.format_exc()}\n"))
            return None
    
    def check_and_calculate_pool(self):
        """Check if Excel file is selected before calculating pool"""
        if not self.excel_path.get() or not self.excel_path.get().strip():
            from tkinter import messagebox
            messagebox.showwarning(
                "Dosya Seçilmedi",
                "Lütfen önce stok dosyasını seçin (Dosya Seç butonuna tıklayın)."
            )
            return
        
        # Check if file exists
        import os
        if not os.path.exists(self.excel_path.get()):
            from tkinter import messagebox
            messagebox.showwarning(
                "Dosya Bulunamadı",
                f"Seçilen dosya bulunamadı:\n{self.excel_path.get()}\n\nLütfen dosyayı tekrar seçin."
            )
            return
        
        # If raw_df is not loaded, try to load it
        if self.raw_df is None:
            try:
                import pandas as pd
                self.raw_df = pd.read_excel(self.excel_path.get(), engine="openpyxl")
                self.append_output(f"Excel dosyası yüklendi: {self.excel_path.get()}\n")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(
                    "Dosya Yükleme Hatası",
                    f"Excel dosyası yüklenirken hata oluştu:\n{str(e)}\n\nLütfen dosyayı kontrol edin."
                )
                return
        
        # Proceed with pool calculation
        self.update_all_pool_sizes(immediate=True)
    
    def update_all_pool_sizes(self, immediate=False):
        """
        Update all pool size displays across all tabs.
        Uses debouncing to avoid too frequent updates, and threading to prevent UI freezing.
        """
        # Cancel previous timer if exists
        if self.pool_update_timer:
            self.root.after_cancel(self.pool_update_timer)
            self.pool_update_timer = None
        
        # If Excel file is not loaded, show message immediately
        if self.raw_df is None:
            print("DEBUG: update_all_pool_sizes - raw_df is None")
            if hasattr(self, 'first_pool_size_label') and self.first_pool_size_label:
                self.first_pool_size_label.config(
                    text="FIRST Havuz Boyutu: Excel dosyası yüklenmedi (Dosya Seç butonuna tıklayın)",
                    foreground="orange"
                )
            if hasattr(self, 'back_pool_size_label') and self.back_pool_size_label:
                self.back_pool_size_label.config(
                    text="BACK Havuz Boyutu: Excel dosyası yüklenmedi (Dosya Seç butonuna tıklayın)",
                    foreground="orange"
                )
            return
        
        # Check if DataFrame is empty
        try:
            if hasattr(self.raw_df, 'empty') and self.raw_df.empty:
                if hasattr(self, 'first_pool_size_label') and self.first_pool_size_label:
                    self.first_pool_size_label.config(
                        text="FIRST Havuz Boyutu: Excel dosyası boş (dosyada veri yok)",
                        foreground="orange"
                    )
                if hasattr(self, 'back_pool_size_label') and self.back_pool_size_label:
                    self.back_pool_size_label.config(
                        text="BACK Havuz Boyutu: Excel dosyası boş (dosyada veri yok)",
                        foreground="orange"
                    )
                return
        except Exception:
            # Continue anyway
            pass
        
        # Show "calculating" message
        if hasattr(self, 'first_pool_size_label') and self.first_pool_size_label:
            self.first_pool_size_label.config(text="FIRST Havuz Boyutu: Hesaplanıyor...", foreground="blue")
        if hasattr(self, 'back_pool_size_label') and self.back_pool_size_label:
            self.back_pool_size_label.config(text="BACK Havuz Boyutu: Hesaplanıyor...", foreground="blue")
        
        # Debounce: wait 800ms before calculating (unless immediate is True)
        # Increased to 800ms to avoid performance issues when user is rapidly changing settings
        if not immediate:
            self.pool_update_timer = self.root.after(800, self._calculate_pool_sizes_in_thread)
        else:
            self._calculate_pool_sizes_in_thread()
    
    def _calculate_pool_sizes_in_thread(self):
        """Calculate pool sizes in a separate thread to avoid freezing UI"""
        import sys
        # Cancel timer
        if self.pool_update_timer:
            self.root.after_cancel(self.pool_update_timer)
            self.pool_update_timer = None
        
        # If a calculation is already running, skip this one (don't print debug to avoid spam)
        if self.pool_update_thread and self.pool_update_thread.is_alive():
            return
        
        def calculate_in_background():
            error_msg = None
            try:
                # Force print to console immediately (flush) AND to GUI output
                import sys
                if sys.stdout:
                    sys.stdout.flush()
                
                # Check if Excel is loaded (in thread)
                # IMPORTANT: Access raw_df from the instance, not from closure
                raw_df_ref = self.raw_df
                if raw_df_ref is None:
                    error_msg = "Excel dosyası yüklenmedi (Dosya Seç butonuna tıklayın)"
                    self.root.after(0, lambda: self._update_pool_size_labels(None, None, 0, 0, error_msg))
                    return
                
                # Check if DataFrame is empty (safely)
                try:
                    if hasattr(raw_df_ref, 'empty') and raw_df_ref.empty:
                        error_msg = "Excel dosyası boş (dosyada veri yok)"
                        self.root.after(0, lambda: self._update_pool_size_labels(None, None, 0, 0, error_msg))
                        return
                except Exception:
                    pass
                
                # Pass raw_df_ref explicitly to avoid thread access issues
                first_size = self.calculate_first_pool_size(raw_df=raw_df_ref)
                back_size = self.calculate_back_pool_size(raw_df=raw_df_ref)
                required_first, required_back = self.calculate_required_counts()
                
                # Update UI in main thread
                self.root.after(0, lambda: self._update_pool_size_labels(
                    first_size, back_size, required_first, required_back, None
                ))
            except Exception as e:
                error_msg = f"Hesaplama hatası: {str(e)}"
                print(f"ERROR calculating pool sizes in thread: {e}")
                import traceback
                traceback_str = traceback.format_exc()
                traceback.print_exc()
                import sys
                if sys.stdout:
                    sys.stdout.flush()
                # Also write to GUI output
                self.root.after(0, lambda: self.append_output(f"Havuz Hesaplama Hatası: {error_msg}\n{traceback_str}\n"))
                self.root.after(0, lambda: self._update_pool_size_labels(None, None, 0, 0, error_msg))
        
        self.pool_update_thread = threading.Thread(target=calculate_in_background, daemon=True)
        self.pool_update_thread.start()
    
    def _update_pool_size_labels(self, first_size, back_size, required_first, required_back, error_msg=None):
        """Update pool size labels in the main thread"""
        print(f"DEBUG: _update_pool_size_labels - first_size={first_size}, back_size={back_size}, error_msg={error_msg}")
        print(f"DEBUG: _update_pool_size_labels - self.raw_df ID: {id(self.raw_df) if self.raw_df is not None else 'None'}")
        
        # Update FIRST pool size
        if hasattr(self, 'first_pool_size_label') and self.first_pool_size_label:
            if error_msg:
                self.first_pool_size_label.config(
                    text=f"FIRST Havuz Boyutu: {error_msg}",
                    foreground="red"
                )
            elif first_size is None:
                # None means calculation failed - show more specific error
                self.first_pool_size_label.config(
                    text="FIRST Havuz Boyutu: ❌ Hesaplama başarısız\n⚠️ Detaylar için 'Çıktı ve Durum' sekmesine bakın",
                    foreground="red"
                )
            elif first_size is not None:
                if first_size == 0:
                    self.first_pool_size_label.config(
                        text=f"Mevcut FIRST Havuz Boyutu: 0 ürün (Gerekli: {required_first}) - ✗ Yetersiz\n⚠️ Hiçbir ürün seçilen kriterlere uymuyor. Kriterleri gevşetin.",
                        foreground="red"
                    )
                else:
                    status = "✓ Yeterli" if first_size >= required_first else "✗ Yetersiz"
                    self.first_pool_size_label.config(
                        text=f"Mevcut FIRST Havuz Boyutu: {first_size} ürün (Gerekli: {required_first}) - {status}",
                        foreground="green" if first_size >= required_first else "red"
                    )
            else:
                self.first_pool_size_label.config(
                    text="FIRST Havuz Boyutu: Excel dosyası yüklenmedi",
                    foreground="orange"
                )
        
        # Update BACK pool size
        if hasattr(self, 'back_pool_size_label') and self.back_pool_size_label:
            if error_msg:
                self.back_pool_size_label.config(
                    text=f"BACK Havuz Boyutu: {error_msg}",
                    foreground="red"
                )
            elif back_size is None:
                # None means calculation failed - show more specific error
                self.back_pool_size_label.config(
                    text="BACK Havuz Boyutu: ❌ Hesaplama başarısız\n⚠️ Detaylar için 'Çıktı ve Durum' sekmesine bakın",
                    foreground="red"
                )
            elif back_size is not None:
                if back_size == 0:
                    self.back_pool_size_label.config(
                        text=f"Mevcut BACK Havuz Boyutu: 0 ürün (Gerekli: {required_back}) - ✗ Yetersiz\n⚠️ Hiçbir ürün seçilen kriterlere uymuyor. Kriterleri gevşetin.",
                        foreground="red"
                    )
                else:
                    status = "✓ Yeterli" if back_size >= required_back else "✗ Yetersiz"
                    self.back_pool_size_label.config(
                        text=f"Mevcut BACK Havuz Boyutu: {back_size} ürün (Gerekli: {required_back}) - {status}",
                        foreground="green" if back_size >= required_back else "red"
                    )
            else:
                self.back_pool_size_label.config(
                    text="BACK Havuz Boyutu: Excel dosyası yüklenmedi",
                    foreground="orange"
                )
    
    def append_output(self, text):
        """Append text to output widget and auto-scroll"""
        if hasattr(self, 'output_text') and self.output_text:
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)
            self.output_text.update_idletasks()
    
    def _redirect_print_to_output(self):
        """Redirect print() calls to both console and GUI output"""
        class PrintRedirector:
            def __init__(self, gui_instance):
                self.gui = gui_instance
                self.original_stdout = sys.stdout if sys.stdout else None
                self.original_stderr = sys.stderr if sys.stderr else None
            
            def write(self, text):
                # Write to original stdout (console)
                if self.original_stdout:
                    self.original_stdout.write(text)
                    if hasattr(self.original_stdout, 'flush'):
                        self.original_stdout.flush()
                # Also write to GUI output if available
                if hasattr(self.gui, 'output_text') and self.gui.output_text:
                    try:
                        self.gui.root.after(0, lambda: self.gui.append_output(text))
                    except:
                        pass  # Ignore errors in GUI update
            
            def flush(self):
                if self.original_stdout and hasattr(self.original_stdout, 'flush'):
                    self.original_stdout.flush()
        
        # Only redirect if stdout is not None
        if sys.stdout:
            sys.stdout = PrintRedirector(self)
        if sys.stderr:
            sys.stderr = PrintRedirector(self)
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
    
    def check_progress_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                self.append_output(msg + "\n")
        except queue.Empty:
            pass
        
        try:
            while True:
                decision_msg = self.decision_queue.get_nowait()
                result = messagebox.askyesno(
                    "Kriter Uyarısı",
                    decision_msg + "\n\nBest-effort ile devam edilsin mi?",
                    icon="warning"
                )
                self.decision_result = result
                self.decision_event.set()
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_progress_queue)
    
    def on_progress(self, msg):
        self.progress_queue.put(msg)
    
    def on_decision(self, msg):
        self.decision_queue.put(msg)
        self.decision_event.clear()
        self.decision_event.wait()
        return self.decision_result
    
    def on_relaxation_choice(self, suggestions, message, missing_first, missing_back, preferred_report, soft_violations=None, hard_violations=None, pool_info=None, unique_products=None, calendar=None, current_cfg=None):
        """Handle relaxation choice dialog with checkboxes and three buttons - thread-safe version"""
        import threading
        
        # Ensure suggestions is a list (not None)
        if suggestions is None:
            suggestions = []
            print("DEBUG: suggestions was None, converting to empty list")
        
        choice_result = {"choice": "manual", "selected": []}
        choice_event = threading.Event()
        
        def format_preferred_report(report):
            if not report:
                return ""
            status_labels = {
                "assigned": "Plana yerleştirildi",
                "slot_missing": "Takvimde uygun slot yok",
                "day_not_in_plan": "Gün plan aralığında değil",
                "not_in_first_pool": "FIRST kriterlerini geçmedi",
                "missing_code": "KisaKod/Renk girilmedi",
                "queued_any_slot": "Uygun ilk slot aranıyor",
            }
            lines = ["Tercihli FIRST ürün durumu:"]
            for entry in report:
                label = status_labels.get(entry.get("status"), entry.get("status", "bilinmiyor"))
                detail = entry.get("detail", "")
                requested = entry.get("requested_day") or ""
                if entry.get("requested_time"):
                    requested += f" {entry.get('requested_time')}"
                requested = requested.strip()
                if requested:
                    requested = f" (Talep: {requested})"
                lines.append(f"{entry.get('index', '?')}. {entry.get('kisakodrenk', '')}: {label}{requested}")
                if detail:
                    lines.append(f"   - {detail}")
            return "\n".join(lines)
        
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("Kriter Uyarısı / Bu ayarlarla plan oluşturulamıyor (v2.1)")
            dialog.geometry("950x700")
            dialog.minsize(700, 500)
            dialog.resizable(True, True)
            dialog.transient(self.root)
            dialog.grab_set()
            
            def on_window_close():
                choice_result["choice"] = "manual"
                choice_result["selected"] = []
                dialog.destroy()
                choice_event.set()
            
            dialog.protocol("WM_DELETE_WINDOW", on_window_close)
            
            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill="both", expand=True)
            
            # Display comprehensive pool and shortage information
            pool_info_frame = ttk.LabelFrame(frame, text="Havuz ve Eksiklik Bilgileri (Pool & Shortage Info)")
            pool_info_frame.pack(fill="x", padx=5, pady=(0, 10))
            
            if pool_info:
                req_first = pool_info.get("required_first", 0)
                req_back = pool_info.get("required_back", 0)
                avail_first = pool_info.get("available_first", 0)
                avail_back = pool_info.get("available_back", 0)
                miss_first = pool_info.get("missing_first", missing_first)
                miss_back = pool_info.get("missing_back", missing_back)
                
                pool_text = f"""FIRST Ürünler:
  • Gerekli: {req_first} post
  • Havuzda Mevcut: {avail_first} ürün
  • Eksik: {miss_first} ürün

BACK Ürünler:
  • Gerekli: {req_back} ürün
  • Havuzda Mevcut: {avail_back} ürün
  • Eksik: {miss_back} ürün

ℹ️ Not: "Havuzda Mevcut" sayıları tüm kriterlere göre hesaplanmıştır:
   • Temel kriterler: yazlık/kışlık, çekim, minimum stok, beden/stok kuralları
   • Gelişmiş kriterler: günlük limitler (örn: günde max 2 siyah FIRST),
     KisaKod kullanım limitleri (örn: aynı KisaKod max X kez FIRST olarak)
   
   Bu kısıtlar havuz hesaplamasında da uygulanır. Eğer havuz yeterli görünüyor
   ama plan oluşmuyorsa, atama sırasında günlük sıralama kısıtları (örn: aynı
   KisaKod arası minimum gün sayısı) ihlal ediliyor olabilir."""
            else:
                pool_text = f"""FIRST Ürünler:
  • Eksik: {missing_first} ürün

BACK Ürünler:
  • Eksik: {missing_back} ürün"""
            
            pool_label = ttk.Label(pool_info_frame, text=pool_text, font=("Courier", 9))
            pool_label.pack(padx=10, pady=10)
            
            # Different message if missing counts are 0/0 (plan can be created, but constraints violated)
            if missing_first == 0 and missing_back == 0:
                title_label = ttk.Label(frame, text="Plan oluşturulabilir, ancak bazı kısıtlar ihlal ediliyor.", 
                                        font=("Arial", 12, "bold"))
                title_label.pack(pady=(0, 5))
                
                explanation_text = """Havuz yeterli görünüyor, ancak plan oluşturulurken bazı kısıtlar ihlal ediliyor.

Gelişmiş kısıtlar havuz hesaplamasında da uygulanır (günlük limitler, KisaKod limitleri).
Ancak atama sırasında şu kısıtlar da kontrol edilir:
• Günlük sıralama kısıtları (örn: aynı KisaKod arası minimum gün sayısı)
• Renk limitleri (örn: aynı renk arka arkaya limiti)
• Günlük farklılık kısıtları (örn: günde minimum X farklı renk)

Bu kısıtları görmezden gelerek devam edebilir veya esnetmeleri uygulayabilirsiniz."""
                
                info_label = ttk.Label(
                    frame,
                    text=explanation_text,
                    font=("Arial", 9),
                    foreground="blue",
                    wraplength=900,
                    justify="left",
                )
                info_label.pack(pady=(0, 5))
            else:
                title_label = ttk.Label(frame, text="Bu ayarlarla plan oluşturulamıyor.", 
                                        font=("Arial", 12, "bold"))
                title_label.pack(pady=(0, 5))
            
            if preferred_report:
                pref_frame = ttk.LabelFrame(frame, text="Tercihli FIRST ürün özeti")
                pref_frame.pack(fill="x", padx=5, pady=(0, 10))
                pref_text = scrolledtext.ScrolledText(pref_frame, height=6, wrap=tk.WORD, font=("Courier", 9))
                pref_text.insert(tk.END, format_preferred_report(preferred_report))
                pref_text.configure(state="disabled")
                pref_text.pack(fill="both", expand=True)
            
            # Show constraint violations if available
            if soft_violations or hard_violations:
                violations_frame = ttk.LabelFrame(frame, text="İhlal Edilen Kısıtlar (Constraint Violations)")
                violations_frame.pack(fill="x", padx=5, pady=(0, 10))
                
                violations_text = scrolledtext.ScrolledText(violations_frame, height=4, wrap=tk.WORD, font=("Courier", 9))
                violations_lines = []
                
                if hard_violations:
                    violations_lines.append("Esnetilemez (Hard) Kısıtlar:")
                    for v in hard_violations:
                        violations_lines.append(f"  ❌ {v.get('rule_name', 'Unknown')}: {v.get('reason', 'No reason provided')}")
                    violations_lines.append("")
                
                if soft_violations:
                    violations_lines.append("Esnetilebilir (Soft) Kısıtlar:")
                    for v in soft_violations:
                        violations_lines.append(f"  ⚠️  {v.get('rule_name', 'Unknown')}: {v.get('reason', 'No reason provided')}")
                
                violations_text.insert(tk.END, "\n".join(violations_lines))
                violations_text.configure(state="disabled")
                violations_text.pack(fill="both", expand=True)
            
            # Filter relaxations based on missing counts
            # CRITICAL: Use a different variable name to avoid shadowing the closure variable
            display_suggestions = list(suggestions) if suggestions else []
            original_suggestion_count = len(display_suggestions)
            
            if missing_first > 0 or missing_back > 0:
                # Show ALL suggestions when there are shortages - user needs to see all options
                # Don't filter - show everything so user can choose the most aggressive relaxations
                subtitle_label = ttk.Label(
                    frame, 
                    text=f"Tüm esnetilebilir kurallar listelenmiştir ({len(display_suggestions)} öneri). Havuzu doldurmak için birden fazla esnetmeyi seçebilirsiniz.",
                    font=("Arial", 10)
                )
            else:
                # Missing counts are 0/0 - show all relaxations (they affect assignment constraints)
                subtitle_label = ttk.Label(
                    frame, 
                    text="Aşağıdaki kısıtlar esnetilebilir. İsteğe bağlı olarak gevşetebilirsiniz (tüm slotlar dolu olduğu için bu esnetmeler havuz büyüklüğünü artırmaz, ancak atama kısıtlarını gevşetebilir).",
                    font=("Arial", 10)
                )
            subtitle_label.pack(pady=(0, 10))
            
            print(f"DEBUG: After filtering, display_suggestions count: {len(display_suggestions)}")
            
            # Create main container with proper layout
            # CRITICAL FIX: Use pack order to ensure button_frame is always visible
            # Strategy: main_container for scrollable content, button_frame at bottom of frame
            # Pack button_frame FIRST (at bottom), then main_container (fills remaining space)
            
            # Create button_frame FIRST and pack it at bottom
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill="x", pady=(10, 0), side="bottom")
            
            # Then create main_container and pack it (will fill space above button_frame)
            main_container = ttk.Frame(frame)
            main_container.pack(fill="both", expand=True, before=button_frame)
            
            # Content container for scrollable suggestions
            content_container = ttk.Frame(main_container)
            content_container.pack(fill="both", expand=True)
            
            canvas = tk.Canvas(content_container, borderwidth=0, highlightthickness=0)
            scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            def on_content_resize(event):
                canvas.itemconfig(window_id, width=event.width)
            
            content_container.bind("<Configure>", on_content_resize)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Track applied relaxations for real-time pool updates
            applied_relaxations_list = []
            
            def update_pool_info():
                """Recalculate pool sizes after applying relaxations"""
                if unique_products is None or calendar is None or current_cfg is None:
                    return
                
                try:
                    from best_effort_analyzer import BestEffortAnalyzer
                    from instagram_auto_post import filter_first_products, filter_back_products
                    from planner import _summarize_missing_counts
                    
                    # Apply all currently applied relaxations
                    test_cfg = current_cfg.copy()
                    test_cfg["_calendar_for_pool"] = calendar
                    if applied_relaxations_list:
                        analyzer_temp = BestEffortAnalyzer(calendar, unique_products, test_cfg, None)
                        test_cfg = analyzer_temp.apply_relaxations(applied_relaxations_list)
                        test_cfg["_calendar_for_pool"] = calendar  # Re-add calendar after applying relaxations
                    
                    # Recalculate pool sizes
                    first_candidates_new = filter_first_products(unique_products, test_cfg)
                    back_candidates_new = filter_back_products(unique_products, test_cfg)
                    first_pool_size_new = len(first_candidates_new)
                    back_pool_size_new = len(back_candidates_new)
                    
                    # Recalculate missing counts
                    missing_stats_new = _summarize_missing_counts(
                        calendar,
                        first_pool_size_new,
                        back_pool_size_new,
                        0,
                        0,
                    )
                    
                    # Update pool info display
                    req_first = missing_stats_new["required_first"]
                    req_back = missing_stats_new["required_back"]
                    avail_first = missing_stats_new["available_first"]
                    avail_back = missing_stats_new["available_back"]
                    miss_first = missing_stats_new["missing_first"]
                    miss_back = missing_stats_new["missing_back"]
                    
                    pool_text_new = f"""FIRST Ürünler:
  • Gerekli: {req_first} post
  • Havuzda Mevcut: {avail_first} ürün
  • Eksik: {miss_first} ürün

BACK Ürünler:
  • Gerekli: {req_back} ürün
  • Havuzda Mevcut: {avail_back} ürün
  • Eksik: {miss_back} ürün

ℹ️ Not: "Havuzda Mevcut" sayıları temel kriterlere göre hesaplanmıştır
   (yazlık/kışlık, çekim, minimum stok, beden/stok kuralları).
   Gelişmiş kurallar (günlük limitler, renk limitleri, KisaKod limitleri)
   havuz hesaplamasında da dikkate alınır ve esnetme önerilerinde havuz
   büyüklüğüne etkileri gösterilir.
   
   Uygulanan esnetmeler: {len(applied_relaxations_list)}"""
                    
                    pool_label.config(text=pool_text_new)
                except Exception as e:
                    import traceback
                    print(f"Error updating pool info: {e}")
                    traceback.print_exc()
            
            def on_apply_relaxation(sug_index):
                """Apply a single relaxation and update pool info"""
                if sug_index >= len(display_suggestions):
                    return
                
                sug = display_suggestions[sug_index]
                
                # Check if already applied
                if any(s.get("rule_type") == sug.get("rule_type") and 
                       s.get("rule_name") == sug.get("rule_name") 
                       for s in applied_relaxations_list):
                    return
                
                # Add to applied list
                applied_relaxations_list.append(sug)
                
                # Update button state
                apply_buttons[sug_index].config(state="disabled", text="✓ Uygulandı")
                
                # Recalculate pool
                update_pool_info()
            
            # Debug: Print suggestions count
            print(f"DEBUG: on_relaxation_choice called with {len(suggestions) if suggestions else 0} suggestions")
            print(f"DEBUG: missing_first={missing_first}, missing_back={missing_back}")
            if suggestions:
                print(f"DEBUG: First 3 suggestions: {[s.get('rule_name', 'N/A') for s in suggestions[:3]]}")
            
            # CRITICAL FIX: Use display_suggestions instead of suggestions to avoid closure shadowing
            checkbox_vars = []
            apply_buttons = []
            if display_suggestions and len(display_suggestions) > 0:
                print(f"DEBUG: Displaying {len(display_suggestions)} suggestions in GUI")
                for i, sug in enumerate(display_suggestions):
                    preselected = sug.get("preselected", True)
                    var = tk.BooleanVar(value=preselected)
                    checkbox_vars.append(var)
                    
                    cb_frame = ttk.Frame(scrollable_frame)
                    cb_frame.pack(fill="x", pady=5, padx=5)
                    
                    cb = ttk.Checkbutton(cb_frame, variable=var)
                    cb.pack(side="left", padx=(0, 5))
                    
                    impact = sug.get('estimated_new_candidates', 0)
                    if impact > 0:
                        impact_text = f"Tahmini etki: +{impact} aday"
                    elif missing_first == 0 and missing_back == 0:
                        impact_text = "Tahmini etki: +0 aday (havuz zaten dolu, ancak atama kısıtlarını gevşetebilir)"
                    else:
                        impact_text = "Tahmini etki: +0 aday (düşük etki)"
                    
                    label_text = f"{sug['rule_name']}: {sug['original_value']} → {sug['suggested_value']}, {impact_text}"
                    label = ttk.Label(cb_frame, text=label_text, wraplength=600)
                    label.pack(side="left", fill="x", expand=True)
                    
                    # Add "Uygula" button
                    apply_btn = ttk.Button(cb_frame, text="Uygula", width=10,
                                          command=lambda idx=i: on_apply_relaxation(idx))
                    apply_btn.pack(side="right", padx=(5, 0))
                    apply_buttons.append(apply_btn)
            else:
                # No suggestions available - show explanation
                print("DEBUG: No suggestions to display - showing explanation message")
                no_suggestions_label = ttk.Label(
                    scrollable_frame,
                    text="Şu anda esnetilebilir kural önerisi bulunmuyor.\nKısıtları görmezden gelerek devam edebilirsiniz.\n\n(Best effort ile plan yap butonunu kullanabilirsiniz.)",
                    font=("Arial", 10),
                    foreground="gray",
                    justify="center",
                )
                no_suggestions_label.pack(pady=20)
            
            # Action buttons are already created above - just define handlers
            def on_manual():
                choice_result["choice"] = "manual"
                choice_result["selected"] = []
                dialog.destroy()
                choice_event.set()
            
            def on_apply_selected():
                """Apply all selected relaxations and create plan"""
                if display_suggestions and checkbox_vars:
                    selected = [sug for i, sug in enumerate(display_suggestions) if i < len(checkbox_vars) and checkbox_vars[i].get()]
                else:
                    selected = []
                # Also include any relaxations applied via "Uygula" buttons
                selected.extend(applied_relaxations_list)
                # Remove duplicates
                seen = set()
                unique_selected = []
                for s in selected:
                    key = (s.get("rule_type"), s.get("rule_name"))
                    if key not in seen:
                        seen.add(key)
                        unique_selected.append(s)
                choice_result["choice"] = "retry_strict"
                choice_result["selected"] = unique_selected
                dialog.destroy()
                choice_event.set()
            
            def on_continue_best():
                """Continue with best-effort mode"""
                if display_suggestions and checkbox_vars:
                    selected = [sug for i, sug in enumerate(display_suggestions) if i < len(checkbox_vars) and checkbox_vars[i].get()]
                else:
                    selected = []
                # Also include any relaxations applied via "Uygula" buttons
                selected.extend(applied_relaxations_list)
                # Remove duplicates
                seen = set()
                unique_selected = []
                for s in selected:
                    key = (s.get("rule_type"), s.get("rule_name"))
                    if key not in seen:
                        seen.add(key)
                        unique_selected.append(s)
                choice_result["choice"] = "continue_best"
                choice_result["selected"] = unique_selected
                dialog.destroy()
                choice_event.set()
            
            # Action buttons - ALWAYS visible
            # button_frame already packed above, just create buttons
            print("DEBUG: Creating action buttons in button_frame")
            
            apply_selected_button = ttk.Button(button_frame, text="İşaretli kriterleri uygula", 
                                               command=on_apply_selected)
            apply_selected_button.pack(side="top", fill="x", padx=10, pady=(0, 6))
            
            manual_button = ttk.Button(button_frame, text="Rapora dön, manuel değiştireceğim", 
                                       command=on_manual)
            manual_button.pack(side="top", fill="x", padx=10, pady=(0, 6))
            
            best_button = ttk.Button(button_frame, text="Best effort ile plan yap", 
                                     command=on_continue_best)
            best_button.pack(side="top", fill="x", padx=10, pady=(0, 6))
            
            print("DEBUG: All action buttons created")
            
            dialog.wait_window()
        
        self.root.after(0, show_dialog)
        
        if not choice_event.wait(timeout=300):
            print("WARNING: Relaxation choice dialog timed out after 5 minutes")
            return "manual", []
        
        return choice_result["choice"], choice_result["selected"]
    
    def collect_config(self) -> PlanConfig:
        """Collect all GUI values into a PlanConfig object"""
        config = PlanConfig(
            stock_excel_path=self.excel_path.get(),
            plan_start_day_name=self.start_day.get(),
            plan_num_days=self.num_days.get(),
        )
        
        config.use_yazlik_front = self.use_yazlik_front.get()
        config.use_kislik_front = self.use_kislik_front.get()
        
        cekim_front = []
        if self.cekim_front_evet.get():
            cekim_front.append("EVET")
        if self.cekim_front_na.get():
            cekim_front.append("NA")
        config.allowed_cekim_front = cekim_front
        
        config.one_atilma_allow_na = self.one_atilma_allow_na.get()
        config.prioritize_never_used_first = self.one_atilma_allow_na.get()
        config.one_atilma_reference_date = self.one_atilma_date.get()
        config.one_atilma_min_days = self.one_atilma_days.get()
        config.min_total_stock_front = self.min_stock_front.get()
        config.min_nos_front = self.min_nos_front.get()
        config.min_dvm_front = self.min_dvm_front.get()
        
        for i in range(1, 9):
            y = self.front_size_y[i].get()
            z = self.front_size_z[i].get()
            config.front_size_stock_rules[i] = (y, z)
        
        config.use_yazlik_back = self.use_yazlik_back.get()
        config.use_kislik_back = self.use_kislik_back.get()
        
        cekim_back = []
        if self.cekim_back_evet.get():
            cekim_back.append("EVET")
        if self.cekim_back_na.get():
            cekim_back.append("NA")
        config.allowed_cekim_back = cekim_back
        
        config.min_total_stock_back = self.min_stock_back.get()
        
        for i in range(1, 9):
            y = self.back_size_y[i].get()
            z = self.back_size_z[i].get()
            config.back_size_stock_rules[i] = (y, z)
        
        config.max_same_uruncinsi_in_a_row_per_day = self.max_same_uruncinsi.get()
        config.min_distinct_uruncinsi_per_day = self.min_distinct_uruncinsi.get()
        config.max_same_color_in_a_row_per_day = self.max_same_color.get()
        config.min_distinct_color_per_day = self.min_distinct_color.get()
        config.same_kisakod_min_gap_days = self.same_kisakod_gap.get()
        
        config.max_black_first_per_day = self.max_black_first_per_day.get()
        config.max_first_uses_per_kisakod = self.max_first_uses_per_kisakod.get()
        config.max_distinct_kisakod_repeatable = self.max_distinct_kisakod_repeatable.get()
        
        # Global Stock Targets removed - no longer constraints
        config.global_min_first_stock_sum = 0
        config.global_min_total_stock_sum = 0
        
        config.prioritize_by_newness = self.prioritize_by_newness.get()
        config.prioritize_by_stock = self.prioritize_by_stock.get()
        
        from config import PreferredFirstProduct
        # Safely access preferred_entries
        preferred_entries = getattr(self, "preferred_entries", [])
        try:
            for entry in preferred_entries:
                try:
                    kisakodrenk = entry.get('kisakodrenk', tk.StringVar()).get().strip() if hasattr(entry.get('kisakodrenk', None), 'get') else str(entry.get('kisakodrenk', '')).strip()
                    gun = entry.get('gun', tk.StringVar()).get().strip() if hasattr(entry.get('gun', None), 'get') else str(entry.get('gun', '')).strip()
                    time = entry.get('time', tk.StringVar()).get().strip() if hasattr(entry.get('time', None), 'get') else str(entry.get('time', '')).strip()
                    force_use = entry.get('force_use', tk.BooleanVar())
                    force_use_val = force_use.get() if hasattr(force_use, 'get') else bool(entry.get('force_use', False))
                    
                    if kisakodrenk:
                        pref_product = PreferredFirstProduct(
                                kisakodrenk=kisakodrenk,
                                gun=gun if gun else None,
                                time=time if time else None
                            )
                        config.preferred_first_products.append(pref_product)
                except Exception as e:
                    print(f"WARNING: Error processing preferred entry: {e}")
                    continue
        except Exception as e:
            print(f"WARNING: Error accessing preferred_entries: {e}")
        
        # Zorla kullanılan ürünleri ayrı bir listede sakla
        # Havuza eklenen tercihli ürünler (kriterlere uygun olsun ya da olmasın)
        try:
            preferred_in_pool_list = []
            excluded_from_pool_list = []
            for entry in preferred_entries:
                try:
                    kisakodrenk_var = entry.get('kisakodrenk')
                    if kisakodrenk_var and hasattr(kisakodrenk_var, 'get'):
                        kisakodrenk = kisakodrenk_var.get().strip().upper()
                    else:
                        kisakodrenk = str(entry.get('kisakodrenk', '')).strip().upper()
                    
                    if not kisakodrenk:
                        continue
                    
                    # Check if product is in pool or explicitly excluded
                    in_pool = entry.get('in_pool', False)
                    if in_pool:
                        preferred_in_pool_list.append(kisakodrenk)
                    else:
                        # Only add to exclusion list if user has explicitly interacted with this product
                        # (i.e., it has a kisakodrenk value entered)
                        excluded_from_pool_list.append(kisakodrenk)
                except Exception as e:
                    print(f"WARNING: Error processing preferred entry for in_pool: {e}")
                    continue
            config.preferred_products_in_pool = preferred_in_pool_list
            config.excluded_first_products_from_pool = excluded_from_pool_list
            print(f"DEBUG: collect_config - preferred_products_in_pool: {config.preferred_products_in_pool}")
            print(f"DEBUG: collect_config - excluded_first_products_from_pool: {config.excluded_first_products_from_pool}")
        except Exception as e:
            print(f"WARNING: Error processing preferred_products_in_pool: {e}")
            import traceback
            traceback.print_exc()
            config.preferred_products_in_pool = []
            config.excluded_first_products_from_pool = []
        
        # Eski forced_preferred_products için backward compatibility (artık kullanılmıyor)
        try:
            config.forced_preferred_products = [
                (entry.get('kisakodrenk', tk.StringVar()).get().strip().upper() if hasattr(entry.get('kisakodrenk', None), 'get') else str(entry.get('kisakodrenk', '')).strip().upper())
                for entry in preferred_entries
                if (entry.get('force_use', tk.BooleanVar()).get() if hasattr(entry.get('force_use', None), 'get') else bool(entry.get('force_use', False))) and (entry.get('kisakodrenk', tk.StringVar()).get().strip() if hasattr(entry.get('kisakodrenk', None), 'get') else str(entry.get('kisakodrenk', '')).strip())
            ]
        except Exception as e:
            print(f"WARNING: Error processing forced_preferred_products: {e}")
            config.forced_preferred_products = []
        
        return config
    
    def run_planner(self):
        if self.is_running:
            messagebox.showwarning("Uyarı", "Plan oluşturma zaten çalışıyor!")
            return
        
        missing_fields = self.validate_required_fields()
        if missing_fields:
            messagebox.showerror(
                "Eksik Bilgiler",
                "Plan oluşturmak için aşağıdaki alanlar doldurulmalıdır:\n\n" + 
                "\n".join(f"• {field}" for field in missing_fields) +
                "\n\nLütfen bu alanları doldurup tekrar deneyin."
            )
            return
        
        self.auto_save_settings()
        
        config = self.collect_config()
        errors = config.validate()
        
        if errors:
            messagebox.showerror(
                "Eksik Bilgiler",
                "Lütfen tüm gerekli alanları doldurun:\n\n" + "\n".join(f"- {e}" for e in errors)
            )
            return
        
        if not os.path.exists(config.stock_excel_path):
            messagebox.showerror("Hata", "Seçilen dosya bulunamadı!")
            return
        
        # Strict pool validation - check if pool sizes are sufficient
        print(f"DEBUG: run_planner - self.raw_df ID: {id(self.raw_df) if self.raw_df is not None else 'None'}")
        print(f"DEBUG: run_planner - self.raw_df is None: {self.raw_df is None}")
        if self.raw_df is not None:
            print(f"DEBUG: run_planner - self.raw_df rows: {len(self.raw_df)}, columns: {list(self.raw_df.columns)}")
        
        required_first, required_back = self.calculate_required_counts()
        first_pool_size = self.calculate_first_pool_size()
        back_pool_size = self.calculate_back_pool_size()
        
        print(f"DEBUG: run_planner - Pool sizes: first={first_pool_size}, back={back_pool_size}, required_first={required_first}, required_back={required_back}")
        
        if first_pool_size is None or back_pool_size is None:
            error_detail = ""
            if self.raw_df is None:
                error_detail = "Excel dosyası yüklenmedi."
            else:
                error_detail = "Havuz boyutu hesaplanamadı (console çıktısındaki hata mesajlarına bakın)."
            messagebox.showerror(
                "Hata",
                f"{error_detail}\n"
                "Lütfen Excel dosyasını seçin ve console çıktısındaki hata mesajlarını kontrol edin."
            )
            return
        
        if first_pool_size < required_first or back_pool_size < required_back:
            error_msg = (
                "Plan oluşturulamıyor. Havuz boyutları yetersiz.\n\n"
                f"Gerekli FIRST post sayısı: {required_first}\n"
                f"Mevcut FIRST havuz boyutu: {first_pool_size}\n\n"
                f"Gerekli BACK ürün sayısı: {required_back}\n"
                f"Mevcut BACK havuz boyutu: {back_pool_size}\n\n"
                "Lütfen kriterlerinizi gevşeterek havuz boyutlarını artırın."
            )
            messagebox.showerror("Havuz Boyutu Yetersiz", error_msg)
            return
        
        self.clear_output()
        self.append_output("Plan oluşturma başlatılıyor...\n\n")
        
        self.is_running = True
        self.run_button.config(state="disabled")
        self.root.config(cursor="watch")
        
        thread = threading.Thread(target=self.run_planner_thread, args=(config,), daemon=True)
        thread.start()
    
    def run_planner_thread(self, config):
        try:
            # Lazy import to avoid best_effort_analyzer dependency at startup
            from planner import run_planner_with_best_effort
            
            cfg_dict = config.to_dict()
            
            result = run_planner_with_best_effort(
                excel_path=config.stock_excel_path,
                start_day=config.plan_start_day_name,
                num_days=config.plan_num_days,
                mode_front="Her ikisi",  # Handled by config
                mode_back="Her ikisi",   # Handled by config
                on_progress=self.on_progress,
                on_relaxation_choice=self.on_relaxation_choice,
                config_override=cfg_dict
            )
            
            self.root.after(0, self.on_planner_complete, result)
            
        except Exception as e:
            import traceback
            error_msg = f"Beklenmeyen hata:\n{str(e)}\n\n{traceback.format_exc()}"
            self.root.after(0, self.on_planner_error, error_msg)
    
    def on_planner_complete(self, result):
        self.is_running = False
        self.run_button.config(state="normal")
        self.root.config(cursor="")
        
        if result["success"]:
            messagebox.showinfo(
                "Başarılı",
                f"Plan başarıyla oluşturuldu!\n\n"
                f"Excel: {result['output_excel']}\n"
                f"Markdown: {result['output_md']}"
            )
        else:
            messagebox.showerror(
                "Hata",
                f"Plan oluşturulamadı:\n\n{result.get('error', 'Bilinmeyen hata')}"
            )
    
    def on_planner_error(self, error_msg):
        self.is_running = False
        self.run_button.config(state="normal")
        self.root.config(cursor="")
        
        self.append_output(f"\n{error_msg}\n")
        messagebox.showerror("Hata", "Plan oluşturma sırasında hata oluştu. Detaylar için çıktı alanına bakın.")
    
    def setup_auto_save_triggers(self):
        """Setup auto-save triggers on field changes"""
        def trigger_auto_save(*args):
            self.auto_save_settings()
        
        def trigger_pool_update(*args, immediate=False):
            self.update_all_pool_sizes(immediate=immediate)
        
        # Otomatik havuz hesaplama kaldırıldı - sadece auto-save yapılıyor
        # Kullanıcı "Havuz Hesapla" butonuna basarak manuel olarak hesaplayacak
        
        self.excel_path.trace_add("write", trigger_auto_save)
        self.start_day.trace_add("write", trigger_auto_save)
        self.num_days.trace_add("write", trigger_auto_save)
        
        # FIRST criteria - sadece auto-save (havuz hesaplama manuel)
        self.use_yazlik_front.trace_add("write", trigger_auto_save)
        self.use_kislik_front.trace_add("write", trigger_auto_save)
        self.cekim_front_evet.trace_add("write", trigger_auto_save)
        self.cekim_front_na.trace_add("write", trigger_auto_save)
        
        self.one_atilma_allow_na.trace_add("write", trigger_auto_save)
        self.one_atilma_date.trace_add("write", trigger_auto_save)
        self.one_atilma_days.trace_add("write", trigger_auto_save)
        self.min_stock_front.trace_add("write", trigger_auto_save)
        self.min_nos_front.trace_add("write", trigger_auto_save)  # NOS/DVM don't affect pool size
        self.min_dvm_front.trace_add("write", trigger_auto_save)  # NOS/DVM don't affect pool size
        
        # Beden stok kuralları için sadece auto-save - pool update sadece "Hesapla" butonuna basıldığında yapılacak
        for i in range(1, 9):
            self.front_size_y[i].trace_add("write", trigger_auto_save)  # Sadece auto-save
            self.front_size_z[i].trace_add("write", trigger_auto_save)  # Sadece auto-save
        
        # BACK criteria - sadece auto-save (havuz hesaplama manuel)
        self.use_yazlik_back.trace_add("write", trigger_auto_save)
        self.use_kislik_back.trace_add("write", trigger_auto_save)
        self.cekim_back_evet.trace_add("write", trigger_auto_save)
        self.cekim_back_na.trace_add("write", trigger_auto_save)
        self.min_stock_back.trace_add("write", trigger_auto_save)
        
        # Beden stok kuralları için sadece auto-save - pool update sadece "Hesapla" butonuna basıldığında yapılacak
        for i in range(1, 9):
            self.back_size_y[i].trace_add("write", trigger_auto_save)  # Sadece auto-save
            self.back_size_z[i].trace_add("write", trigger_auto_save)  # Sadece auto-save
        
        # Advanced rules - günlük kısıtlar için sadece auto-save - pool update sadece "Hesapla" butonuna basıldığında yapılacak
        self.max_same_uruncinsi.trace_add("write", trigger_auto_save)  # Assignment constraint - sadece auto-save
        self.min_distinct_uruncinsi.trace_add("write", trigger_auto_save)  # Assignment constraint - sadece auto-save
        self.max_same_color.trace_add("write", trigger_auto_save)  # Assignment constraint - sadece auto-save
        self.min_distinct_color.trace_add("write", trigger_auto_save)  # Assignment constraint - sadece auto-save
        self.same_kisakod_gap.trace_add("write", trigger_auto_save)  # Assignment constraint - sadece auto-save
        
        # Advanced FIRST constraints - sadece auto-save (havuz hesaplama manuel)
        self.max_black_first_per_day.trace_add("write", trigger_auto_save)
        self.max_first_uses_per_kisakod.trace_add("write", trigger_auto_save)
        self.max_distinct_kisakod_repeatable.trace_add("write", trigger_auto_save)
        
        # Global stock targets - will be removed later (don't affect pool size)
        self.global_first_stock.trace_add("write", trigger_auto_save)
        self.global_total_stock.trace_add("write", trigger_auto_save)
        
        # Prioritization - affects FIRST pool (will be moved to Advanced Rules)
        # Global önceliklendirme havuz sayısını değiştirmez, sadece sıralamayı değiştirir - sadece auto-save
        self.prioritize_by_newness.trace_add("write", trigger_auto_save)  # Sadece auto-save (havuz sayısını değiştirmez)
        self.prioritize_by_stock.trace_add("write", trigger_auto_save)  # Sadece auto-save (havuz sayısını değiştirmez)
    
    def get_settings_file_path(self):
        """Get path to settings file"""
        return os.path.join(os.path.expanduser("~"), ".instagram_planner_settings.json")
    
    def auto_save_settings(self):
        """Automatically save current settings to local file"""
        try:
            import json
            config = self.collect_config()
            
            # Override size/stock rules with current GUI values to preserve user input
            # This ensures values entered by user are saved even if they are 0
            for i in range(1, 9):
                y = self.front_size_y[i].get()
                z = self.front_size_z[i].get()
                config.front_size_stock_rules[i] = (y, z)
            
            for i in range(1, 9):
                y = self.back_size_y[i].get()
                z = self.back_size_z[i].get()
                config.back_size_stock_rules[i] = (y, z)
            
            settings_file = self.get_settings_file_path()
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Auto-save failed: {e}")
    
    def auto_load_settings(self):
        """Automatically load settings from local file on startup"""
        try:
            import json
            settings_file = self.get_settings_file_path()
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    cfg_dict = json.load(f)
                self.load_settings_into_gui(cfg_dict)
        except Exception as e:
            print(f"Auto-load failed: {e}")
    
    def load_settings_into_gui(self, cfg_dict):
        """Load settings dictionary into GUI fields"""
        if 'stock_excel_path' in cfg_dict:
            excel_path = cfg_dict['stock_excel_path']
            self.excel_path.set(excel_path)
            # Also load raw_df if Excel file exists
            if excel_path and os.path.exists(excel_path):
                try:
                    import pandas as pd
                    print(f"DEBUG: Auto-load: Excel dosyası yükleniyor: {excel_path}")
                    # Try with openpyxl engine first (for .xlsx files)
                    try:
                        self.raw_df = pd.read_excel(excel_path, engine="openpyxl")
                    except Exception as e1:
                        print(f"DEBUG: Auto-load: openpyxl engine ile yüklenemedi: {e1}")
                        # Try without engine (for .xls files)
                        self.raw_df = pd.read_excel(excel_path)
                    
                    print(f"DEBUG: Auto-load: Excel dosyası yüklendi. Satır sayısı: {len(self.raw_df)}")
                    # Don't update pool sizes automatically - wait for user to select criteria
                    # Pool sizes will be calculated when user changes any filter criteria
                except Exception as e:
                    print(f"DEBUG: Excel dosyası auto-load sırasında yüklenemedi: {e}")
                    import traceback
                    traceback.print_exc()
                    self.raw_df = None
        if 'plan_start_day_name' in cfg_dict:
            self.start_day.set(cfg_dict['plan_start_day_name'])
        if 'plan_num_days' in cfg_dict:
            self.num_days.set(cfg_dict['plan_num_days'])
        
        if 'use_yazlik_front' in cfg_dict:
            self.use_yazlik_front.set(cfg_dict['use_yazlik_front'])
        if 'use_kislik_front' in cfg_dict:
            self.use_kislik_front.set(cfg_dict['use_kislik_front'])
        
        if 'allowed_cekim_front' in cfg_dict:
            cekim_front = cfg_dict['allowed_cekim_front']
            self.cekim_front_evet.set('EVET' in cekim_front)
            self.cekim_front_na.set('NA' in cekim_front)
        
        if 'one_atilma_allow_na' in cfg_dict:
            self.one_atilma_allow_na.set(cfg_dict['one_atilma_allow_na'])
        if 'one_atilma_reference_date' in cfg_dict:
            self.one_atilma_date.set(cfg_dict['one_atilma_reference_date'])
        if 'one_atilma_min_days' in cfg_dict:
            self.one_atilma_days.set(cfg_dict['one_atilma_min_days'])
        if 'min_total_stock_front' in cfg_dict:
            self.min_stock_front.set(cfg_dict['min_total_stock_front'])
        if 'min_nos_front' in cfg_dict:
            self.min_nos_front.set(cfg_dict['min_nos_front'])
        if 'min_dvm_front' in cfg_dict:
            self.min_dvm_front.set(cfg_dict['min_dvm_front'])
        
        if 'front_size_stock_rules' in cfg_dict:
            rules = cfg_dict['front_size_stock_rules']
            if isinstance(rules, list):
                # First, create a set of size_counts that are in the rules
                loaded_size_counts = set()
                for item in rules:
                    # Format: (size_count, y, z) - 3 elements
                    if isinstance(item, (list, tuple)) and len(item) == 3:
                        size_count, y, z = item
                        if size_count in self.front_size_y:
                            self.front_size_y[size_count].set(y)
                            self.front_size_z[size_count].set(z)
                            loaded_size_counts.add(size_count)
                # Note: We don't reset other size_counts to 0 here
                # This preserves user input for sizes not in the saved rules
        
        if 'use_yazlik_back' in cfg_dict:
            self.use_yazlik_back.set(cfg_dict['use_yazlik_back'])
        if 'use_kislik_back' in cfg_dict:
            self.use_kislik_back.set(cfg_dict['use_kislik_back'])
        
        if 'allowed_cekim_back' in cfg_dict:
            cekim_back = cfg_dict['allowed_cekim_back']
            self.cekim_back_evet.set('EVET' in cekim_back)
            self.cekim_back_na.set('NA' in cekim_back)
        
        if 'min_total_stock_back' in cfg_dict:
            self.min_stock_back.set(cfg_dict['min_total_stock_back'])
        
        if 'back_size_stock_rules' in cfg_dict:
            rules = cfg_dict['back_size_stock_rules']
            if isinstance(rules, list):
                # First, create a set of size_counts that are in the rules
                loaded_size_counts = set()
                for item in rules:
                    # Format: (size_count, y, z) - 3 elements
                    if isinstance(item, (list, tuple)) and len(item) == 3:
                        size_count, y, z = item
                        if size_count in self.back_size_y:
                            self.back_size_y[size_count].set(y)
                            self.back_size_z[size_count].set(z)
                            loaded_size_counts.add(size_count)
                # Note: We don't reset other size_counts to 0 here
                # This preserves user input for sizes not in the saved rules
        
        if 'max_same_uruncinsi_in_a_row_per_day' in cfg_dict:
            self.max_same_uruncinsi.set(cfg_dict['max_same_uruncinsi_in_a_row_per_day'])
        if 'min_distinct_uruncinsi_per_day' in cfg_dict:
            self.min_distinct_uruncinsi.set(cfg_dict['min_distinct_uruncinsi_per_day'])
        if 'max_same_color_in_a_row_per_day' in cfg_dict:
            self.max_same_color.set(cfg_dict['max_same_color_in_a_row_per_day'])
        if 'min_distinct_color_per_day' in cfg_dict:
            self.min_distinct_color.set(cfg_dict['min_distinct_color_per_day'])
        if 'same_kisakod_min_gap_days' in cfg_dict:
            self.same_kisakod_gap.set(cfg_dict['same_kisakod_min_gap_days'])
        
        if 'max_black_first_per_day' in cfg_dict:
            self.max_black_first_per_day.set(cfg_dict['max_black_first_per_day'])
        if 'max_first_uses_per_kisakod' in cfg_dict:
            self.max_first_uses_per_kisakod.set(cfg_dict['max_first_uses_per_kisakod'])
        if 'max_distinct_kisakod_repeatable' in cfg_dict:
            self.max_distinct_kisakod_repeatable.set(cfg_dict['max_distinct_kisakod_repeatable'])
        
        if 'global_min_first_stock_sum' in cfg_dict:
            self.global_first_stock.set(cfg_dict['global_min_first_stock_sum'])
        if 'global_min_total_stock_sum' in cfg_dict:
            self.global_total_stock.set(cfg_dict['global_min_total_stock_sum'])
        
        if 'prioritize_by_newness' in cfg_dict:
            self.prioritize_by_newness.set(cfg_dict['prioritize_by_newness'])
        if 'prioritize_by_stock' in cfg_dict:
            self.prioritize_by_stock.set(cfg_dict['prioritize_by_stock'])
        
        if 'preferred_first_products' in cfg_dict:
            preferred_list = cfg_dict['preferred_first_products']
            if isinstance(preferred_list, list):
                for i, pref in enumerate(preferred_list):
                    if i < len(self.preferred_entries):
                        entry = self.preferred_entries[i]
                        
                        kisakodrenk = pref.get('kisakodrenk', '')
                        gun = pref.get('gun', '')
                        time = pref.get('time', '')
                        
                        entry['kisakodrenk'].set(kisakodrenk)
                        entry['gun'].set(gun)
                        entry['time'].set(time)
                        
                        gun_combo = entry.get('gun_combo')
                        time_combo = entry.get('time_combo')
                        
                        if gun_combo and time_combo:
                            if gun:
                                weekday_times = ["", "09:00", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:30", "17:30", "19:30", "21:00", "22:30"]
                                weekend_times = ["", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:30", "19:30", "21:00"]
                                
                                if gun in ["Cumartesi", "Pazar"]:
                                    time_combo['values'] = weekend_times
                                else:
                                    time_combo['values'] = weekday_times
                                time_combo['state'] = 'readonly'
                            else:
                                time_combo['values'] = [""]
                                time_combo['state'] = 'disabled'
    
    def reset_settings(self):
        """Reset all settings to default values and clear saved settings"""
        if self.is_running:
            messagebox.showwarning("Uyarı", "Plan oluşturma sürerken ayarları sıfırlayamazsınız.")
            return
        
        result = messagebox.askyesno(
            "Ayarları Sıfırla",
            "Tüm ayarlar silinecek ve varsayılan değerlere dönülecek.\nDevam etmek istiyor musunuz?"
        )
        if result:
            self.excel_path.set("")
            self.start_day.set("Pazartesi")
            self.num_days.set(7)
            
            self.use_yazlik_front.set(False)
            self.use_kislik_front.set(False)
            self.cekim_front_evet.set(False)
            self.cekim_front_na.set(False)
            
            self.one_atilma_allow_na.set(False)
            self.one_atilma_date.set("")
            self.one_atilma_days.set(0)
            self.min_stock_front.set(0)
            self.min_nos_front.set(0)
            self.min_dvm_front.set(0)
            
            for i in range(1, 9):
                self.front_size_y[i].set(0)
                self.front_size_z[i].set(0)
            
            self.use_yazlik_back.set(False)
            self.use_kislik_back.set(False)
            self.cekim_back_evet.set(False)
            self.cekim_back_na.set(False)
            self.min_stock_back.set(0)
            
            for i in range(1, 9):
                self.back_size_y[i].set(0)
                self.back_size_z[i].set(0)
            
            self.max_same_uruncinsi.set(0)
            self.min_distinct_uruncinsi.set(0)
            self.max_same_color.set(0)
            self.min_distinct_color.set(0)
            self.same_kisakod_gap.set(0)
            
            self.max_black_first_per_day.set(0)
            self.max_first_uses_per_kisakod.set(0)
            self.max_distinct_kisakod_repeatable.set(0)
            
            self.global_first_stock.set(0)
            self.global_total_stock.set(0)
            
            self.prioritize_by_newness.set(False)
            self.prioritize_by_stock.set(False)
            
            for entry in getattr(self, "preferred_entries", []):
                entry['kisakodrenk'].set("")
                entry['gun'].set("")
                entry['time'].set("")
                
                gun_combo = entry.get('gun_combo')
                time_combo = entry.get('time_combo')
                if gun_combo:
                    gun_combo.set("")
                if time_combo:
                    time_combo['values'] = [""]
                    time_combo.set("")
                    time_combo['state'] = 'disabled'
            
            self.clear_output()
            
            self.auto_save_settings()
            
            messagebox.showinfo("Başarılı", "Tüm ayarlar sıfırlandı.")
    
    def validate_required_fields(self):
        """Validate all required fields before plan generation"""
        missing_fields = []
        
        if not self.excel_path.get():
            missing_fields.append("Stok dosyası (Excel)")
        
        if not self.start_day.get():
            missing_fields.append("Plan başlangıç günü")
        
        if not self.num_days.get() or self.num_days.get() < 1:
            missing_fields.append("Kaç günlük plan (1-7)")
        
        if not self.use_yazlik_front.get() and not self.use_kislik_front.get():
            missing_fields.append("FIRST mevsim seçimi (Yazlık veya Kışlık)")
        
        if not self.use_yazlik_back.get() and not self.use_kislik_back.get():
            missing_fields.append("BACK mevsim seçimi (Yazlık veya Kışlık)")
        
        if not self.cekim_front_evet.get() and not self.cekim_front_na.get():
            missing_fields.append("FIRST Çekim seçimi (en az bir seçenek)")
        
        if not self.cekim_back_evet.get() and not self.cekim_back_na.get():
            missing_fields.append("BACK Çekim seçimi (en az bir seçenek)")
        
        # Prioritization is optional - no longer required
        # (removed from validation)
        
        return missing_fields


def main():
    root = tk.Tk()
    
    try:
        root.tk.call("source", "azure.tcl")
        root.tk.call("set_theme", "light")
    except:
        pass
    
    app = PlannerGUI(root)
    
    root.mainloop()


if __name__ == "__main__":
    main()
