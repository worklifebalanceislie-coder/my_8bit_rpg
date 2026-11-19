import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import pygame
from database import DatabaseManager
from sprites import PALETTE

VALID_PALETTE = {k: v for k, v in PALETTE.items() if v is not None}
VALID_PALETTE["M"] = (100, 190, 90)   # Основной цвет тела монстра (перекрашивается в игре)
VALID_PALETTE["m"] = (60, 130, 55)    # Тень тела монстра (перекрашивается в игре)
VALID_PALETTE["E"] = (240, 60, 60)    # Глаза монстра (перекрашиваются в игре)


def closest_palette_char(r, g, b, a=255):
    if a < 128:
        return "."
    best_k, best_dist = ".", 999999
    for k, (pr, pg, pb) in VALID_PALETTE.items():
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < best_dist:
            best_dist, best_k = dist, k
    return best_k

def rgb_to_hex(rgb):
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


class RPGContentStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("8-Bit RPG Studio — Редактор базы данных (rpg.db)")
        self.root.geometry("1280x780")

        pygame.init()
        self.db = DatabaseManager("rpg.db")
        self.db.sync_all_catalogs()
        from sprites import load_sprites
        self.db.sync_all_catalogs()

        self.build_top_bar()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.build_sprites_tab()
        self.build_items_tab()
        self.build_skills_tab()
        self.build_races_tab()
        self.build_classes_tab()
        self.build_factions_tab()
        self.build_monsters_tab()
        self.build_professions_tab()
        self.build_npcs_tab()

        self.status_var = tk.StringVar(value="База данных rpg.db подключена и готова к работе.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

    def set_status(self, text):
        self.status_var.set(text)

    def build_top_bar(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="8-BIT RPG CONTENT STUDIO", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Экспорт всей БД в JSON...", command=self.export_json).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bar, text="Импорт из JSON...", command=self.import_json).pack(side=tk.RIGHT, padx=4)

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON файлы", "*.json")], initialfile="rpg_content.json")
        if not path:
            return
        cur = self.db.conn.cursor()
        tables = [
            "sprites_catalog", "items_catalog", "skills_catalog", "effects_catalog",
            "races_catalog", "classes_catalog", "factions_catalog", "npc_templates",
            "monster_archetypes", "monster_parts", "professions_catalog", "recipes_catalog"
        ]

        dump = {}
        for t in tables:
            cur.execute(f"SELECT * FROM {t}")
            dump[t] = [dict(r) for r in cur.fetchall()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2)
        self.set_status(f"Экспортировано в {path}")
        messagebox.showinfo("Экспорт завершен", "Все каталоги успешно выгружены в JSON!")

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON файлы", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                dump = json.load(f)
            cur = self.db.conn.cursor()
            for table, rows in dump.items():
                if not rows:
                    continue
                first_row, *_ = rows; cols = list(first_row.keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                for row in rows:
                    cur.execute(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", [row[c] for c in cols])
            self.db.conn.commit()
            self.refresh_all_tables()
            self.set_status(f"Импортировано из {path}")
            messagebox.showinfo("Импорт завершен", "Данные из JSON успешно загружены в rpg.db!")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    def refresh_all_tables(self):
        self.refresh_sprite_list()
        self.refresh_items_table()
        self.refresh_skills_table()
        self.refresh_races_table()
        self.refresh_classes_table()
        self.refresh_factions_table()
        self.refresh_monsters_tables()
        self.refresh_professions_tables()
        self.refresh_npcs_table()
    
    def build_sprites_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="1. Спрайты (16x16)")

        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(left, text="Холст 16x16 (ЛКМ — рисовать, ПКМ — стереть)", font=("Segoe UI", 10, "bold")).pack(pady=4)

        self.cell_size = 26
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(left, text="Холст 16x16 (ЛКМ — рисовать, ПКМ — стереть)", font=("Segoe UI", 10, "bold")).pack(pady=4)

        guide_bar = ttk.Frame(left)
        guide_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(guide_bar, text="Ориентир:").pack(side=tk.LEFT)
        self.guide_var = tk.StringVar(value="Нет")
        guide_cb = ttk.Combobox(
            guide_bar, textvariable=self.guide_var, state="readonly", width=28,
            values=[
                "Нет",
                "Персонаж (голова / торс / ноги)",
                "Оружие (угол клинка и рукоять)",
                "Броня (зона нагрудника)",
                "Монстр: Голова (верх 0..6)",
                "Монстр: Туловище (низ 5..14)"
            ]
        )
        guide_cb.pack(side=tk.LEFT, padx=6)
        guide_cb.bind("<<ComboboxSelected>>", lambda *_: self.redraw_sprite_canvas())

        self.canvas = tk.Canvas(left, width=16 * self.cell_size, height=16 * self.cell_size, bg="#1e222d", highlightthickness=1)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.paint_cell(e, erase=False))
        self.canvas.bind("<B1-Motion>", lambda e: self.paint_cell(e, erase=False))
        self.canvas.bind("<Button-3>", lambda e: self.paint_cell(e, erase=True))
        self.canvas.bind("<B3-Motion>", lambda e: self.paint_cell(e, erase=True))

        self.grid_data = [["." for _ in range(16)] for _ in range(16)]
        self.selected_char = "R"

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, pady=8)
        ttk.Button(btn_row, text="Очистить холст", command=self.clear_sprite_canvas).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Загрузить PNG (можно несколько)...", command=self.import_png_sprites).pack(side=tk.LEFT, padx=4)

        mid = ttk.Frame(tab)
        mid.pack(side=tk.LEFT, fill=tk.Y, padx=15)
        ttk.Label(mid, text="Палитра цветов:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=4)

        pal_frame = ttk.Frame(mid)
        pal_frame.pack(anchor=tk.W)
        for idx, (ch, rgb) in enumerate(VALID_PALETTE.items()):
            b = tk.Button(pal_frame, bg=rgb_to_hex(rgb), width=3, height=1, relief=tk.RAISED,
                          command=lambda c=ch: self.select_palette_color(c))
            b.grid(row=idx // 6, column=idx % 6, padx=2, pady=2)

        self.cur_color_lbl = ttk.Label(mid, text=f"Выбран цвет: {self.selected_char}", font=("Segoe UI", 9, "bold"))
        self.cur_color_lbl.pack(anchor=tk.W, pady=6)

        ttk.Label(mid, text="Предпросмотр (4x):", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(10, 4))
        self.preview_canvas = tk.Canvas(mid, width=64, height=64, bg="#2b303e", highlightthickness=1)
        self.preview_canvas.pack(anchor=tk.W)

        ttk.Label(mid, text="Ключ спрайта в БД:", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(14, 2))
        self.sprite_key_var = tk.StringVar(value="custom_sprite")
        ttk.Entry(mid, textvariable=self.sprite_key_var, width=28).pack(anchor=tk.W, pady=2)

        ttk.Button(mid, text="Сохранить спрайт в БД", command=self.save_sprite).pack(anchor=tk.W, pady=8, fill=tk.X)
        ttk.Button(mid, text="Удалить выбранный из БД", command=self.delete_sprite).pack(anchor=tk.W, pady=2, fill=tk.X)

        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        ttk.Label(right, text="Спрайты в базе данных:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        self.sprite_search_var = tk.StringVar()
        self.sprite_search_var.trace_add("write", lambda *_: self.refresh_sprite_list())
        ttk.Entry(right, textvariable=self.sprite_search_var).pack(fill=tk.X, pady=4)

        self.sprite_listbox = tk.Listbox(right, font=("Consolas", 10))
        self.sprite_listbox.pack(fill=tk.BOTH, expand=True)
        self.sprite_listbox.bind("<<ListboxSelect>>", self.on_sprite_select)

        self.redraw_sprite_canvas()
        self.refresh_sprite_list()

    def select_palette_color(self, ch):
        self.selected_char = ch
        self.cur_color_lbl.config(text=f"Выбран цвет: {ch}")

    def paint_cell(self, event, erase=False):
        c = event.x // self.cell_size
        r = event.y // self.cell_size
        if 0 <= r < 16 and 0 <= c < 16:
            self.grid_data[r][c] = "." if erase else self.selected_char
            self.redraw_sprite_canvas()

    def clear_sprite_canvas(self):
        self.grid_data = [["." for _ in range(16)] for _ in range(16)]
        self.redraw_sprite_canvas()

    def redraw_sprite_canvas(self):
        self.canvas.delete("all")
        self.preview_canvas.delete("all")
        for r in range(16):
            for c in range(16):
                ch = self.grid_data[r][c]
                rgb = PALETTE.get(ch)
                fill = rgb_to_hex(rgb) if rgb else ("#232734" if (r + c) % 2 == 0 else "#2c3140")
                x1, y1 = c * self.cell_size, r * self.cell_size
                self.canvas.create_rectangle(x1, y1, x1 + self.cell_size, y1 + self.cell_size, fill=fill, outline="#3c4254")
                if rgb:
                    self.preview_canvas.create_rectangle(c * 4, r * 4, c * 4 + 4, r * 4 + 4, fill=fill, outline="")
        self.draw_guide_overlay()

    def draw_guide_overlay(self):
        mode = getattr(self, "guide_var", None)
        if not mode:
            return
        g = mode.get()
        cs = self.cell_size

        def box(c1, r1, c2, r2, color, label=""):
            self.canvas.create_rectangle(c1 * cs + 2, r1 * cs + 2, (c2 + 1) * cs - 2, (r2 + 1) * cs - 2, outline=color, width=2, dash=(4, 2))
            if label:
                self.canvas.create_text(c1 * cs + 6, r1 * cs + 10, text=label, fill=color, anchor=tk.W, font=("Consolas", 8, "bold"))

        if g.startswith("Персонаж"):
            box(4, 1, 11, 6, "#66d9ef", "Голова")
            box(3, 7, 12, 11, "#a6e22e", "Торс/Руки")
            box(4, 12, 11, 15, "#fd971f", "Ноги")
        elif g.startswith("Оружие"):
            # Диагональная ось клинка/посоха
            self.canvas.create_line(7 * cs + cs // 2, 11 * cs + cs // 2, 15 * cs + cs // 2, 2 * cs + cs // 2, fill="#f92672", width=2, dash=(5, 3))
            box(7, 9, 10, 11, "#e6db74", "Рукоять")
            box(10, 2, 15, 8, "#66d9ef", "Лезвие")
        elif g.startswith("Броня"):
            box(4, 1, 11, 6, "#555e70", "Голова (фон)")
            box(3, 7, 12, 11, "#a6e22e", "Зона брони")
        elif g.startswith("Монстр: Голова"):
            box(3, 0, 12, 6, "#66d9ef", "Зона головы")
            self.canvas.create_line(0, 6 * cs, 16 * cs, 6 * cs, fill="#fd971f", width=2, dash=(4, 2))
        elif g.startswith("Монстр: Туловище"):
            self.canvas.create_line(0, 6 * cs, 16 * cs, 6 * cs, fill="#66d9ef", width=2, dash=(4, 2))
            box(3, 6, 12, 14, "#a6e22e", "Тело и ноги")

    def import_png_sprites(self):
        paths = filedialog.askopenfilenames(title="Выберите изображения (PNG/JPG/BMP)", filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp")])
        if not paths:
            return
        cur = self.db.conn.cursor()
        count = 0
        for p in paths:
            try:
                surf = pygame.image.load(p)
                scaled = pygame.transform.scale(surf, (16, 16))
                matrix = []
                for y in range(16):
                    row_chars = []
                    for x in range(16):
                        r, g, b, a = scaled.get_at((x, y))
                        row_chars.append(closest_palette_char(r, g, b, a))
                    matrix.append("".join(row_chars))
                base_name, _ = os.path.splitext(os.path.basename(p))
                key = base_name.lower().replace(" ", "_")
                cur.execute("INSERT OR REPLACE INTO sprites_catalog VALUES (?, ?)", (key, json.dumps(matrix)))
                count += 1
            except Exception as e:
                messagebox.showwarning("Ошибка файла", f"Не удалось загрузить {p}: {e}")
        self.db.conn.commit()
        self.refresh_sprite_list()
        self.set_status(f"Импортировано спрайтов из файлов: {count}")

    def refresh_sprite_list(self):
        query = self.sprite_search_var.get().lower()
        self.sprite_listbox.delete(0, tk.END)
        cur = self.db.conn.cursor()

        # 1. Обычные спрайты и тайлы окружения (трава, вода, песок, стены, предметы)
        cur.execute("SELECT sprite_key FROM sprites_catalog ORDER BY sprite_key")
        for r in cur.fetchall():
            k = r["sprite_key"]
            if query in k.lower():
                self.sprite_listbox.insert(tk.END, k)

        # 2. Детали генератора монстров (головы и туловища)
        cur.execute("SELECT id FROM monster_parts ORDER BY id")
        for r in cur.fetchall():
            label = f"[МОНСТР] {r['id']}"
            if query in label.lower():
                self.sprite_listbox.insert(tk.END, label)

    def on_sprite_select(self, _):
        sel = self.sprite_listbox.curselection()
        if not sel:
            return
        idx, *_ = sel
        raw_label = self.sprite_listbox.get(idx)
        cur = self.db.conn.cursor()

        if raw_label.startswith("[МОНСТР] "):
            part_id = raw_label.replace("[МОНСТР] ", "")
            cur.execute("SELECT art_matrix FROM monster_parts WHERE id = ?", (part_id,))
            row = cur.fetchone()
            if row:
                self.sprite_key_var.set(raw_label)
                mat = json.loads(row["art_matrix"])
                self.grid_data = [list(line.ljust(16, ".")) for line in mat[:16]]
                self.redraw_sprite_canvas()
        else:
            cur.execute("SELECT art_matrix FROM sprites_catalog WHERE sprite_key = ?", (raw_label,))
            row = cur.fetchone()
            if row:
                self.sprite_key_var.set(raw_label)
                mat = json.loads(row["art_matrix"])
                self.grid_data = [list(line.ljust(16, ".")) for line in mat[:16]]
                self.redraw_sprite_canvas()

    def save_sprite(self):
        key = self.sprite_key_var.get().strip()
        if not key:
            return
        matrix = ["".join(r) for r in self.grid_data]
        cur = self.db.conn.cursor()

        if key.startswith("[МОНСТР] "):
            part_id = key.replace("[МОНСТР] ", "")
            cur.execute("UPDATE monster_parts SET art_matrix = ? WHERE id = ?", (json.dumps(matrix), part_id))
            self.db.conn.commit()
            self.set_status(f"Деталь монстра '{part_id}' обновлена в БД!")
        else:
            cur.execute("INSERT OR REPLACE INTO sprites_catalog VALUES (?, ?)", (key, json.dumps(matrix)))
            self.db.conn.commit()
            self.set_status(f"Спрайт '{key}' сохранен в БД.")
        self.refresh_sprite_list()

    def delete_sprite(self):
        key = self.sprite_key_var.get().strip()
        if not key:
            return
        cur = self.db.conn.cursor()
        if key.startswith("[МОНСТР] "):
            part_id = key.replace("[МОНСТР] ", "")
            cur.execute("DELETE FROM monster_parts WHERE id = ?", (part_id,))
            self.refresh_monsters_tables()
        else:
            cur.execute("DELETE FROM sprites_catalog WHERE sprite_key = ?", (key,))
        self.db.conn.commit()
        self.refresh_sprite_list()
        self.set_status(f"Запись '{key}' удалена из БД.")

    def build_items_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="2. Предметы")

        form = ttk.LabelFrame(tab, text="Параметры предмета", padding=10)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.it_id = tk.StringVar()
        self.it_name = tk.StringVar()
        self.it_type = tk.StringVar(value="weapon")
        self.it_value = tk.StringVar(value="50")
        self.it_style = tk.StringVar(value="melee")
        self.it_skill = tk.StringVar(value="")
        self.it_sprite = tk.StringVar(value="")
        self.it_desc = tk.StringVar()

        fields = [
            ("ID (англ):", ttk.Entry(form, textvariable=self.it_id, width=30)),
            ("Название:", ttk.Entry(form, textvariable=self.it_name, width=30)),
            ("Тип предмета:", ttk.Combobox(form, textvariable=self.it_type, state="readonly", width=27,
                                           values=["weapon", "armor", "pants", "boots", "ring", "amulet", "backpack", "consumable", "book", "misc"])),
            ("Цена (золото):", ttk.Entry(form, textvariable=self.it_value, width=30)),
            ("Стиль боя:", ttk.Combobox(form, textvariable=self.it_style, state="readonly", width=27,
                                        values=["melee", "bow", "staff"])),
            ("Навык (для книг):", ttk.Combobox(form, textvariable=self.it_skill, width=27, values=self.get_skill_ids())),
            ("Спрайт (экипировка):", ttk.Combobox(form, textvariable=self.it_sprite, width=27, values=self.get_sprite_keys())),
            ("Описание:", ttk.Entry(form, textvariable=self.it_desc, width=30)),
        ]
        for idx, (lbl, widget) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            widget.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        b_frame = ttk.LabelFrame(form, text="Бонусы и свойства (0 = не давать)", padding=8)
        b_frame.grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=8)

        self.bonus_vars = {}
        bonus_keys = [
            ("atk", "Атака (+):"), ("def", "Защита (+):"),
            ("hp", "Макс. HP (+):"), ("mp", "Макс. MP (+):"),
            ("heal", "Лечение HP:"), ("mana", "Восст. MP:"),
            ("capacity", "Слоты сумки:")
        ]
        for idx, (bk, blbl) in enumerate(bonus_keys):
            var = tk.IntVar(value=0)
            self.bonus_vars[bk] = var
            ttk.Label(b_frame, text=blbl).grid(row=idx // 2, column=(idx % 2) * 2, sticky=tk.W, padx=4, pady=2)
            ttk.Spinbox(b_frame, from_=0, to=999, textvariable=var, width=6).grid(row=idx // 2, column=(idx % 2) * 2 + 1, padx=4, pady=2)

        self.it_effect_var = tk.StringVar(value="")
        ttk.Label(b_frame, text="Эффект зелья:").grid(row=4, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Combobox(b_frame, textvariable=self.it_effect_var, state="readonly", width=14,
                     values=["", "haste", "shield", "burn", "poison", "slow", "cure"]).grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=4)

        btns = ttk.Frame(form)
        btns.grid(row=9, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Сохранить / Обновить", command=self.save_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Очистить", command=self.clear_item_form).pack(side=tk.LEFT, padx=4)

        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        filter_bar = ttk.Frame(right)
        filter_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(filter_bar, text="Поиск:").pack(side=tk.LEFT)
        self.it_search = tk.StringVar()
        self.it_search.trace_add("write", lambda *_: self.refresh_items_table())
        ttk.Entry(filter_bar, textvariable=self.it_search, width=25).pack(side=tk.LEFT, padx=6)

        ttk.Label(filter_bar, text="Фильтр по типу:").pack(side=tk.LEFT, padx=(10, 4))
        self.it_filter_type = tk.StringVar(value="Все")
        cb = ttk.Combobox(filter_bar, textvariable=self.it_filter_type, state="readonly", width=15,
                          values=["Все", "weapon", "armor", "pants", "boots", "ring", "amulet", "backpack", "consumable", "book", "misc"])
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda *_: self.refresh_items_table())

        cols = ("id", "name", "type", "value", "bonus")
        self.items_tree = ttk.Treeview(right, columns=cols, show="headings")
        for c, title, w in [("id", "ID", 130), ("name", "Название", 180), ("type", "Тип", 95), ("value", "Цена", 65), ("bonus", "Свойства", 240)]:
            self.items_tree.heading(c, text=title)
            self.items_tree.column(c, width=w)
        self.items_tree.pack(fill=tk.BOTH, expand=True)
        self.items_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        self.refresh_items_table()

    def get_skill_ids(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM skills_catalog ORDER BY id")
        return [""] + [r["id"] for r in cur.fetchall()]

    def get_sprite_keys(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT sprite_key FROM sprites_catalog ORDER BY sprite_key")
        return [""] + [r["sprite_key"] for r in cur.fetchall()]

    def refresh_items_table(self):
        for row in self.items_tree.get_children():
            self.items_tree.delete(row)
        q = self.it_search.get().lower()
        ftype = self.it_filter_type.get()
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM items_catalog ORDER BY item_type, name")
        for r in cur.fetchall():
            if ftype != "Все" and r["item_type"] != ftype:
                continue
            if q and q not in r["name"].lower() and q not in r["id"].lower():
                continue
            self.items_tree.insert("", tk.END, values=(r["id"], r["name"], r["item_type"], r["value"], r["stats_bonus"]))

    def on_item_select(self, _):
        sel = self.items_tree.selection()
        if not sel:
            return
        iid, *_ = self.items_tree.item(sel)["values"]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM items_catalog WHERE id = ?", (iid,))
        r = cur.fetchone()
        if not r:
            return
        self.it_id.set(r["id"])
        self.it_name.set(r["name"])
        self.it_type.set(r["item_type"])
        self.it_value.set(str(r["value"]))
        self.it_style.set(r["combat_style"])
        self.it_skill.set(r["skill_id"] or "")
        self.it_sprite.set(r["sprite_key"] or "")
        self.it_desc.set(r["description"])

        bonus = json.loads(r["stats_bonus"])
        for k, var in self.bonus_vars.items():
            var.set(bonus.get(k, 0))
        if "effect" in bonus:
            self.it_effect_var.set(bonus["effect"])
        elif bonus.get("cure"):
            self.it_effect_var.set("cure")
        else:
            self.it_effect_var.set("")

    def clear_item_form(self):
        self.it_id.set("")
        self.it_name.set("")
        self.it_value.set("50")
        self.it_skill.set("")
        self.it_sprite.set("")
        self.it_desc.set("")
        for var in self.bonus_vars.values():
            var.set(0)
        self.it_effect_var.set("")

    def save_item(self):
        iid = self.it_id.get().strip()
        name = self.it_name.get().strip()
        if not iid or not name:
            messagebox.showwarning("Внимание", "Укажите ID и Название предмета!")
            return
        bonus = {}
        for k, var in self.bonus_vars.items():
            if var.get() > 0:
                bonus[k] = var.get()
        eff = self.it_effect_var.get()
        if eff == "cure":
            bonus["cure"] = True
        elif eff:
            bonus["effect"] = eff

        cur = self.db.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO items_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (iid, name, self.it_type.get(), int(self.it_value.get() or 0),
                     json.dumps(bonus, ensure_ascii=False), self.it_desc.get(),
                     self.it_style.get(), self.it_skill.get() or None, self.it_sprite.get() or None))
        self.db.conn.commit()
        self.refresh_items_table()
        self.set_status(f"Предмет '{name}' сохранен в БД.")

    def delete_item(self):
        iid = self.it_id.get().strip()
        if not iid:
            return
        cur = self.db.conn.cursor()
        cur.execute("DELETE FROM items_catalog WHERE id = ?", (iid,))
        self.db.conn.commit()
        self.refresh_items_table()
        self.set_status(f"Предмет '{iid}' удален.")
    
    def build_skills_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="3. Навыки")

        form = ttk.LabelFrame(tab, text="Редактор навыка", padding=10)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.sk_id = tk.StringVar()
        self.sk_name = tk.StringVar()
        self.sk_kind = tk.StringVar(value="active")
        self.sk_mana = tk.IntVar(value=10)
        self.sk_cd = tk.DoubleVar(value=3.0)
        self.sk_desc = tk.StringVar()

        rows = [
            ("ID навыка:", ttk.Entry(form, textvariable=self.sk_id, width=28)),
            ("Название:", ttk.Entry(form, textvariable=self.sk_name, width=28)),
            ("Тип:", ttk.Combobox(form, textvariable=self.sk_kind, state="readonly", width=25, values=["active", "passive"])),
            ("Расход MP:", ttk.Spinbox(form, from_=0, to=500, textvariable=self.sk_mana, width=10)),
            ("Откат (сек):", ttk.Spinbox(form, from_=0.0, to=60.0, increment=0.5, textvariable=self.sk_cd, width=10)),
            ("Описание:", ttk.Entry(form, textvariable=self.sk_desc, width=28)),
        ]
        for idx, (lbl, w) in enumerate(rows):
            ttk.Label(form, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=4)
            w.grid(row=idx, column=1, sticky=tk.W, pady=4, padx=5)

        btns = ttk.Frame(form)
        btns.grid(row=6, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Сохранить", command=self.save_skill).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_skill).pack(side=tk.LEFT, padx=4)

        self.skills_tree = ttk.Treeview(tab, columns=("id", "name", "kind", "mana", "cd", "desc"), show="headings")
        for c, t, w in [("id", "ID", 120), ("name", "Название", 160), ("kind", "Тип", 80), ("mana", "MP", 50), ("cd", "Откат", 60), ("desc", "Описание", 300)]:
            self.skills_tree.heading(c, text=t)
            self.skills_tree.column(c, width=w)
        self.skills_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.skills_tree.bind("<<TreeviewSelect>>", self.on_skill_select)
        self.refresh_skills_table()

    def refresh_skills_table(self):
        for r in self.skills_tree.get_children():
            self.skills_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM skills_catalog ORDER BY kind, name")
        for r in cur.fetchall():
            self.skills_tree.insert("", tk.END, values=(r["id"], r["name"], r["kind"], r["mana_cost"], r["cooldown"], r["desc"]))

    def on_skill_select(self, _):
        sel = self.skills_tree.selection()
        if not sel:
            return
        sid, sname, skind, smana, scd, sdesc = self.skills_tree.item(sel)["values"]
        self.sk_id.set(sid)
        self.sk_name.set(sname)
        self.sk_kind.set(skind)
        self.sk_mana.set(smana)
        self.sk_cd.set(scd)
        self.sk_desc.set(sdesc)

    def save_skill(self):
        if not self.sk_id.get().strip():
            return
        cur = self.db.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO skills_catalog VALUES (?, ?, ?, ?, ?, ?)",
                    (self.sk_id.get().strip(), self.sk_name.get().strip(), self.sk_kind.get(),
                     self.sk_mana.get(), self.sk_cd.get(), self.sk_desc.get()))
        self.db.conn.commit()
        self.refresh_skills_table()
        self.set_status("Навык сохранен в БД.")

    def delete_skill(self):
        sid = self.sk_id.get().strip()
        if sid:
            self.db.conn.execute("DELETE FROM skills_catalog WHERE id = ?", (sid,))
            self.db.conn.commit()
            self.refresh_skills_table()
    
    def build_races_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="4. Расы")

        form = ttk.LabelFrame(tab, text="Редактор расы", padding=10)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.rc_id = tk.StringVar()
        self.rc_name = tk.StringVar()
        self.rc_faction = tk.StringVar(value="player")
        self.rc_speed = tk.IntVar(value=80)
        self.rc_gold = tk.IntVar(value=10)
        self.rc_skill = tk.StringVar(value="race_human")
        self.rc_sprite = tk.StringVar(value="player")
        self.rc_desc = tk.StringVar()
        self.rc_rel = tk.StringVar()

        fields = [
            ("ID расы:", ttk.Entry(form, textvariable=self.rc_id, width=28)),
            ("Название:", ttk.Entry(form, textvariable=self.rc_name, width=28)),
            ("Фракция:", ttk.Combobox(form, textvariable=self.rc_faction, width=25, values=self.get_faction_ids())),
            ("Скорость бега:", ttk.Spinbox(form, from_=30, to=200, textvariable=self.rc_speed, width=10)),
            ("Бонус золота:", ttk.Spinbox(form, from_=0, to=1000, textvariable=self.rc_gold, width=10)),
            ("Расовый навык:", ttk.Combobox(form, textvariable=self.rc_skill, width=25, values=self.get_skill_ids())),
            ("Спрайт расы:", ttk.Combobox(form, textvariable=self.rc_sprite, width=25, values=self.get_sprite_keys())),
            ("Описание:", ttk.Entry(form, textvariable=self.rc_desc, width=28)),
            ("Текст дипломатии:", ttk.Entry(form, textvariable=self.rc_rel, width=28)),
        ]
        for idx, (lbl, w) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        bf = ttk.LabelFrame(form, text="Модификаторы статов", padding=6)
        bf.grid(row=9, column=0, columnspan=2, sticky=tk.EW, pady=6)
        self.rc_bonuses = {}
        for idx, st in enumerate(["str", "agi", "int", "vit", "end"]):
            v = tk.IntVar(value=0)
            self.rc_bonuses[st] = v
            ttk.Label(bf, text=st.upper()).grid(row=0, column=idx * 2, padx=2)
            ttk.Spinbox(bf, from_=-5, to=20, textvariable=v, width=4).grid(row=0, column=idx * 2 + 1, padx=2)

        btns = ttk.Frame(form)
        btns.grid(row=10, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Сохранить", command=self.save_race).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_race).pack(side=tk.LEFT, padx=4)

        self.races_tree = ttk.Treeview(tab, columns=("id", "name", "faction", "speed", "bonuses"), show="headings")
        for c, t, w in [("id", "ID", 100), ("name", "Раса", 140), ("faction", "Фракция", 110), ("speed", "Скорость", 80), ("bonuses", "Бонусы", 260)]:
            self.races_tree.heading(c, text=t)
            self.races_tree.column(c, width=w)
        self.races_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.races_tree.bind("<<TreeviewSelect>>", self.on_race_select)
        self.refresh_races_table()

    def get_faction_ids(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM factions_catalog ORDER BY id")
        return [r["id"] for r in cur.fetchall()]

    def refresh_races_table(self):
        for r in self.races_tree.get_children():
            self.races_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM races_catalog")
        for r in cur.fetchall():
            self.races_tree.insert("", tk.END, values=(r["id"], r["name"], r["faction"], r["speed"], r["bonuses"]))

    def on_race_select(self, _):
        sel = self.races_tree.selection()
        if not sel:
            return
        rid, *_ = self.races_tree.item(sel)["values"]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM races_catalog WHERE id = ?", (rid,))
        r = cur.fetchone()
        if r:
            self.rc_id.set(r["id"])
            self.rc_name.set(r["name"])
            self.rc_faction.set(r["faction"])
            self.rc_speed.set(r["speed"])
            self.rc_gold.set(r["gold_bonus"])
            self.rc_skill.set(r["racial_skill"] or "")
            self.rc_sprite.set(r["sprite_key"] or "")
            self.rc_desc.set(r["desc"])
            self.rc_rel.set(r["relations"])
            bon = json.loads(r["bonuses"])
            for k, v in self.rc_bonuses.items():
                v.set(bon.get(k, 0))

    def save_race(self):
        rid = self.rc_id.get().strip()
        if not rid:
            return
        bon = {k: v.get() for k, v in self.rc_bonuses.items()}
        self.db.conn.execute("INSERT OR REPLACE INTO races_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (rid, self.rc_name.get().strip(), self.rc_faction.get(), self.rc_speed.get(),
                              json.dumps(bon), self.rc_gold.get(), self.rc_skill.get() or None,
                              self.rc_desc.get(), self.rc_rel.get(), self.rc_sprite.get() or None))
        self.db.conn.commit()
        self.refresh_races_table()
        self.set_status("Раса сохранена в БД.")

        rid = self.rc_id.get().strip()
        if not rid:
            return
        bon = {k: v.get() for k, v in self.rc_bonuses.items()}
        self.db.conn.execute("INSERT OR REPLACE INTO races_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (rid, self.rc_name.get().strip(), self.rc_faction.get(), self.rc_speed.get(),
                              json.dumps(bon), self.rc_gold.get(), self.rc_skill.get() or None,
                              self.rc_desc.get(), self.rc_rel.get()))
        self.db.conn.commit()
        self.refresh_races_table()
        self.set_status("Раса сохранена в БД.")

    def delete_race(self):
        rid = self.rc_id.get().strip()
        if rid:
            self.db.conn.execute("DELETE FROM races_catalog WHERE id = ?", (rid,))
            self.db.conn.commit()
            self.refresh_races_table()

    def build_classes_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="5. Классы")

        form = ttk.LabelFrame(tab, text="Редактор класса", padding=10)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.cl_id = tk.StringVar()
        self.cl_name = tk.StringVar()
        self.cl_gold = tk.IntVar(value=50)
        self.cl_skill = tk.StringVar(value="whirlwind")
        self.cl_items = tk.StringVar(value="rusty_sword, potion")
        self.cl_desc = tk.StringVar()

        fields = [
            ("ID класса:", ttk.Entry(form, textvariable=self.cl_id, width=28)),
            ("Название:", ttk.Entry(form, textvariable=self.cl_name, width=28)),
            ("Стартовое золото:", ttk.Spinbox(form, from_=0, to=5000, textvariable=self.cl_gold, width=10)),
            ("Стартовый навык:", ttk.Combobox(form, textvariable=self.cl_skill, width=25, values=self.get_skill_ids())),
            ("Предметы (ID через запятую):", ttk.Entry(form, textvariable=self.cl_items, width=28)),
            ("Описание:", ttk.Entry(form, textvariable=self.cl_desc, width=28)),
        ]
        for idx, (lbl, w) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        sf = ttk.LabelFrame(form, text="Стартовые характеристики", padding=6)
        sf.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=6)
        self.cl_stats = {}
        for idx, st in enumerate(["hp", "mp", "str", "agi", "int", "vit", "end"]):
            v = tk.IntVar(value=50 if st == "hp" else (30 if st == "mp" else 2))
            self.cl_stats[st] = v
            ttk.Label(sf, text=st.upper()).grid(row=idx // 4, column=(idx % 4) * 2, padx=2, pady=2)
            ttk.Spinbox(sf, from_=0, to=500, textvariable=v, width=5).grid(row=idx // 4, column=(idx % 4) * 2 + 1, padx=2, pady=2)

        btns = ttk.Frame(form)
        btns.grid(row=7, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Сохранить", command=self.save_class).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_class).pack(side=tk.LEFT, padx=4)

        self.classes_tree = ttk.Treeview(tab, columns=("id", "name", "gold", "skill", "items"), show="headings")
        for c, t, w in [("id", "ID", 100), ("name", "Класс", 130), ("gold", "Золото", 65), ("skill", "Навык", 110), ("items", "Снаряжение", 280)]:
            self.classes_tree.heading(c, text=t)
            self.classes_tree.column(c, width=w)
        self.classes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.classes_tree.bind("<<TreeviewSelect>>", self.on_class_select)
        self.refresh_classes_table()

    def refresh_classes_table(self):
        for r in self.classes_tree.get_children():
            self.classes_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM classes_catalog")
        for r in cur.fetchall():
            self.classes_tree.insert("", tk.END, values=(r["id"], r["name"], r["gold"], r["skill"], r["items"]))

    def on_class_select(self, _):
        sel = self.classes_tree.selection()
        if not sel:
            return
        cid, *_ = self.classes_tree.item(sel)["values"]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM classes_catalog WHERE id = ?", (cid,))
        r = cur.fetchone()
        if r:
            self.cl_id.set(r["id"])
            self.cl_name.set(r["name"])
            self.cl_gold.set(r["gold"])
            self.cl_skill.set(r["skill"] or "")
            self.cl_items.set(", ".join(json.loads(r["items"])))
            self.cl_desc.set(r["desc"])
            st = json.loads(r["stats"])
            for k, v in self.cl_stats.items():
                v.set(st.get(k, 0))

    def save_class(self):
        cid = self.cl_id.get().strip()
        if not cid:
            return
        st = {k: v.get() for k, v in self.cl_stats.items()}
        items_list = [i.strip() for i in self.cl_items.get().split(",") if i.strip()]
        self.db.conn.execute("INSERT OR REPLACE INTO classes_catalog VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (cid, self.cl_name.get().strip(), self.cl_desc.get(),
                              json.dumps(st), self.cl_gold.get(), json.dumps(items_list), self.cl_skill.get() or None))
        self.db.conn.commit()
        self.refresh_classes_table()
        self.set_status("Класс сохранен в БД.")

    def delete_class(self):
        cid = self.cl_id.get().strip()
        if cid:
            self.db.conn.execute("DELETE FROM classes_catalog WHERE id = ?", (cid,))
            self.db.conn.commit()
            self.refresh_classes_table()

    def build_factions_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="6. Фракции и Дипломатия")

        form = ttk.LabelFrame(tab, text="Редактор фракции", padding=10)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.fac_id = tk.StringVar()
        self.fac_name = tk.StringVar()
        ttk.Label(form, text="ID фракции (англ):").pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.fac_id, width=30).pack(anchor=tk.W, pady=(2, 8))
        ttk.Label(form, text="Название фракции:").pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.fac_name, width=30).pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(form, text="Враждебна к фракциям:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(6, 4))
        self.hostile_checks_frame = ttk.Frame(form)
        self.hostile_checks_frame.pack(fill=tk.X)
        self.hostile_vars = {}

        btns = ttk.Frame(form)
        btns.pack(pady=12)
        ttk.Button(btns, text="Сохранить фракцию", command=self.save_faction).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_faction).pack(side=tk.LEFT, padx=4)

        self.fac_tree = ttk.Treeview(tab, columns=("id", "name", "hostile"), show="headings")
        for c, t, w in [("id", "ID", 130), ("name", "Название", 220), ("hostile", "Враждебны к", 340)]:
            self.fac_tree.heading(c, text=t)
            self.fac_tree.column(c, width=w)
        self.fac_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fac_tree.bind("<<TreeviewSelect>>", self.on_faction_select)
        self.refresh_factions_table()

    def refresh_factions_table(self):
        for r in self.fac_tree.get_children():
            self.fac_tree.delete(r)
        for w in self.hostile_checks_frame.winfo_children():
            w.destroy()
        self.hostile_vars.clear()

        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM factions_catalog ORDER BY id")
        rows = cur.fetchall()
        for r in rows:
            fid = r["id"]
            self.fac_tree.insert("", tk.END, values=(fid, r["name_ru"], r["hostile_to"]))
            var = tk.BooleanVar(value=False)
            self.hostile_vars[fid] = var
            ttk.Checkbutton(self.hostile_checks_frame, text=f"{r['name_ru']} ({fid})", variable=var).pack(anchor=tk.W)

    def on_faction_select(self, _):
        sel = self.fac_tree.selection()
        if not sel:
            return
        fid, fname, hostile_json = self.fac_tree.item(sel[0])["values"]
        self.fac_id.set(fid)
        self.fac_name.set(fname)
        enemies = set(json.loads(hostile_json))
        for f_key, var in self.hostile_vars.items():
            var.set(f_key in enemies)

    def save_faction(self):
        fid = self.fac_id.get().strip()
        fname = self.fac_name.get().strip()
        if not fid or not fname:
            return
        enemies = [k for k, v in self.hostile_vars.items() if v.get() and k != fid]
        self.db.conn.execute("INSERT OR REPLACE INTO factions_catalog VALUES (?, ?, ?)", (fid, fname, json.dumps(enemies)))
        self.db.conn.commit()
        self.refresh_factions_table()
        self.set_status(f"Фракция '{fname}' сохранена.")

    def delete_faction(self):
        fid = self.fac_id.get().strip()
        if fid:
            self.db.conn.execute("DELETE FROM factions_catalog WHERE id = ?", (fid,))
            self.db.conn.commit()
            self.refresh_factions_table()

    # =========================================================================
    # 7. ВКЛАДКА ГЕНЕРАТОРА МОНСТРОВ (АРХЕТИПЫ И ЗАПЧАСТИ)
    # =========================================================================
    def build_monsters_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="7. Монстры")

        # Левая половина: Архетипы монстров
        left = ttk.LabelFrame(tab, text="Архетипы монстров (Виды)", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.m_id = tk.StringVar()
        self.m_name = tk.StringVar()
        self.m_hp = tk.IntVar(value=35)
        self.m_atk = tk.IntVar(value=4)
        self.m_spd = tk.IntVar(value=45)
        self.m_fac = tk.StringVar(value="monster")
        self.m_skills = tk.StringVar(value="whirlwind, passive_blade")

        rows = [
            ("ID архетипа (англ):", ttk.Entry(left, textvariable=self.m_id, width=25)),
            ("Название (напр. Орк):", ttk.Entry(left, textvariable=self.m_name, width=25)),
            ("Базовое HP:", ttk.Spinbox(left, from_=5, to=2000, textvariable=self.m_hp, width=10)),
            ("Базовая атака:", ttk.Spinbox(left, from_=1, to=500, textvariable=self.m_atk, width=10)),
            ("Скорость бега:", ttk.Spinbox(left, from_=10, to=200, textvariable=self.m_spd, width=10)),
            ("Фракция:", ttk.Combobox(left, textvariable=self.m_fac, width=22, values=self.get_faction_ids())),
            ("Навыки (через запятую):", ttk.Entry(left, textvariable=self.m_skills, width=25)),
        ]
        for idx, (lbl, w) in enumerate(rows):
            ttk.Label(left, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        btns = ttk.Frame(left)
        btns.grid(row=7, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Сохранить вид", command=self.save_monster_arch).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить вид", command=self.delete_monster_arch).pack(side=tk.LEFT, padx=4)

        self.m_arch_tree = ttk.Treeview(left, columns=("id", "name", "hp", "atk", "fac"), show="headings", height=10)
        for c, t, w in [("id", "ID", 90), ("name", "Вид", 120), ("hp", "HP", 50), ("atk", "АТК", 50), ("fac", "Фракция", 95)]:
            self.m_arch_tree.heading(c, text=t)
            self.m_arch_tree.column(c, width=w)
        self.m_arch_tree.grid(row=8, column=0, columnspan=2, sticky=tk.NSEW, pady=6)
        self.m_arch_tree.bind("<<TreeviewSelect>>", self.on_m_arch_select)

        # Правая половина: Части тела (Головы и Туловища)
        right = ttk.LabelFrame(tab, text="Части тела для сборки (Туловища и Головы)", padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.p_id = tk.StringVar()
        self.p_type = tk.StringVar(value="body")
        self.p_arch = tk.StringVar(value="goblin")
        self.p_sprite_src = tk.StringVar(value="")

        self.p_arch_combo = ttk.Combobox(right, textvariable=self.p_arch, width=23, values=self.get_archetype_ids())
        self.p_src_combo = ttk.Combobox(right, textvariable=self.p_sprite_src, width=23, values=self.get_part_sources())

        p_rows = [
            ("ID новой детали:", ttk.Entry(right, textvariable=self.p_id, width=26)),
            ("Тип детали:", ttk.Combobox(right, textvariable=self.p_type, state="readonly", width=23, values=["body", "head"])),
            ("Для какого архетипа:", self.p_arch_combo),
            ("Скопировать пиксели из:", self.p_src_combo),
        ]
        for idx, (lbl, w) in enumerate(p_rows):
            ttk.Label(right, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        p_btns = ttk.Frame(right)
        p_btns.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(p_btns, text="Сохранить деталь", command=self.save_monster_part).pack(side=tk.LEFT, padx=3)
        ttk.Button(p_btns, text="Удалить", command=self.delete_monster_part).pack(side=tk.LEFT, padx=3)
        ttk.Button(p_btns, text="Рисовать на холсте ➔", command=self.edit_part_on_canvas).pack(side=tk.LEFT, padx=3)

        self.m_parts_tree = ttk.Treeview(right, columns=("id", "type", "arch"), show="headings", height=13)
        for c, t, w in [("id", "ID детали", 160), ("type", "Тип", 70), ("arch", "Архетип", 120)]:
            self.m_parts_tree.heading(c, text=t)
            self.m_parts_tree.column(c, width=w)
        self.m_parts_tree.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=6)
        self.m_parts_tree.bind("<<TreeviewSelect>>", self.on_m_part_select)

        self.refresh_monsters_tables()

    def get_archetype_ids(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM monster_archetypes ORDER BY id")
        return [r["id"] for r in cur.fetchall()]

    def get_part_sources(self):
        cur = self.db.conn.cursor()
        sources = []
        cur.execute("SELECT id FROM monster_parts ORDER BY id")
        for r in cur.fetchall():
            sources.append(f"[Деталь] {r['id']}")
        cur.execute("SELECT sprite_key FROM sprites_catalog ORDER BY sprite_key")
        for r in cur.fetchall():
            sources.append(r["sprite_key"])
        return sources

    def refresh_monsters_tables(self):
        for r in self.m_arch_tree.get_children():
            self.m_arch_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM monster_archetypes")
        for r in cur.fetchall():
            self.m_arch_tree.insert("", tk.END, values=(r["id"], r["name_ru"], r["base_hp"], r["base_atk"], r["faction"]))

        for r in self.m_parts_tree.get_children():
            self.m_parts_tree.delete(r)
        cur.execute("SELECT id, part_type, archetype FROM monster_parts ORDER BY archetype, part_type")
        for r in cur.fetchall():
            self.m_parts_tree.insert("", tk.END, values=(r["id"], r["part_type"], r["archetype"]))

        if hasattr(self, "p_arch_combo"):
            self.p_arch_combo["values"] = self.get_archetype_ids()
        if hasattr(self, "p_src_combo"):
            self.p_src_combo["values"] = self.get_part_sources()

    def on_m_arch_select(self, _):
        sel = self.m_arch_tree.selection()
        if not sel:
            return
        aid, *_ = self.m_arch_tree.item(sel)["values"]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM monster_archetypes WHERE id = ?", (aid,))
        r = cur.fetchone()
        if r:
            self.m_id.set(r["id"])
            self.m_name.set(r["name_ru"])
            self.m_hp.set(r["base_hp"])
            self.m_atk.set(r["base_atk"])
            self.m_spd.set(r["speed"])
            self.m_fac.set(r["faction"])
            self.m_skills.set(", ".join(json.loads(r["possible_skills"])))
            self.p_arch.set(r["id"])

    def save_monster_arch(self):
        aid = self.m_id.get().strip()
        if not aid:
            return
        sks = [s.strip() for s in self.m_skills.get().split(",") if s.strip()]
        self.db.conn.execute("INSERT OR REPLACE INTO monster_archetypes VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (aid, self.m_name.get().strip(), self.m_hp.get(), self.m_atk.get(),
                              self.m_spd.get(), self.m_fac.get(), json.dumps(sks)))
        self.db.conn.commit()
        self.refresh_monsters_tables()
        self.set_status(f"Архетип монстра '{aid}' сохранен.")

    def delete_monster_arch(self):
        aid = self.m_id.get().strip()
        if aid:
            self.db.conn.execute("DELETE FROM monster_archetypes WHERE id = ?", (aid,))
            self.db.conn.commit()
            self.refresh_monsters_tables()

    def on_m_part_select(self, _):
        sel = self.m_parts_tree.selection()
        if not sel:
            return
        pid, ptype, parch = self.m_parts_tree.item(sel)["values"]
        self.p_id.set(pid)
        self.p_type.set(ptype)
        self.p_arch.set(parch)
        self.p_sprite_src.set(f"[Деталь] {pid}")

    def edit_part_on_canvas(self):
        pid = self.p_id.get().strip()
        if not pid:
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT art_matrix FROM monster_parts WHERE id = ?", (pid,))
        row = cur.fetchone()
        if row:
            self.sprite_key_var.set(f"[МОНСТР] {pid}")
            mat = json.loads(row["art_matrix"])
            self.grid_data = [list(line.ljust(16, ".")) for line in mat[:16]]
            self.redraw_sprite_canvas()
            self.notebook.select(0)
            self.set_status(f"Редактирование детали '{pid}' на холсте 16x16")

    def save_monster_part(self):
        pid = self.p_id.get().strip()
        src = self.p_sprite_src.get().strip()
        if not pid or not src:
            messagebox.showwarning("Внимание", "Укажите ID детали и выберите источник пикселей!")
            return
        cur = self.db.conn.cursor()
        if src.startswith("[Деталь] "):
            src_id = src.replace("[Деталь] ", "")
            cur.execute("SELECT art_matrix FROM monster_parts WHERE id = ?", (src_id,))
        else:
            cur.execute("SELECT art_matrix FROM sprites_catalog WHERE sprite_key = ?", (src,))

        row = cur.fetchone()
        if not row:
            messagebox.showerror("Ошибка", "Выбранный источник графики не найден!")
            return
        cur.execute("INSERT OR REPLACE INTO monster_parts VALUES (?, ?, ?, ?)",
                    (pid, self.p_type.get(), self.p_arch.get().strip(), row["art_matrix"]))
        self.db.conn.commit()
        self.refresh_monsters_tables()
        self.refresh_sprite_list()
        self.set_status(f"Деталь '{pid}' сохранена для архетипа '{self.p_arch.get()}'.")

    def delete_monster_part(self):
        pid = self.p_id.get().strip()
        if pid:
            self.db.conn.execute("DELETE FROM monster_parts WHERE id = ?", (pid,))
            self.db.conn.commit()
            self.refresh_monsters_tables()
            self.refresh_sprite_list()

    # =========================================================================
    # 8. ВКЛАДКА ПРОФЕССИЙ И РЕЦЕПТОВ КРАФТА
    # =========================================================================
    def build_professions_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="8. Профессии и Крафт")

        # Левая половина: Профессии
        left = ttk.LabelFrame(tab, text="Профессии", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.pr_id = tk.StringVar()
        self.pr_name = tk.StringVar()
        self.pr_btype = tk.StringVar(value="craft")
        self.pr_desc = tk.StringVar()

        p_rows = [
            ("ID профессии:", ttk.Entry(left, textvariable=self.pr_id, width=25)),
            ("Название:", ttk.Entry(left, textvariable=self.pr_name, width=25)),
            ("Тип бонуса:", ttk.Combobox(left, textvariable=self.pr_btype, state="readonly", width=22, values=["craft", "trade", "gather"])),
            ("Описание:", ttk.Entry(left, textvariable=self.pr_desc, width=25)),
        ]
        for idx, (lbl, w) in enumerate(p_rows):
            ttk.Label(left, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        btns = ttk.Frame(left)
        btns.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Сохранить профессию", command=self.save_profession).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить", command=self.delete_profession).pack(side=tk.LEFT, padx=4)

        self.prof_tree = ttk.Treeview(left, columns=("id", "name", "type", "desc"), show="headings", height=12)
        for c, t, w in [("id", "ID", 90), ("name", "Название", 110), ("type", "Тип", 65), ("desc", "Описание", 210)]:
            self.prof_tree.heading(c, text=t)
            self.prof_tree.column(c, width=w)
        self.prof_tree.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=6)
        self.prof_tree.bind("<<TreeviewSelect>>", self.on_prof_select)

        # Правая половина: Рецепты крафта
        right = ttk.LabelFrame(tab, text="Рецепты создания предметов", padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.rec_id = tk.StringVar()
        self.rec_prof = tk.StringVar(value="blacksmith")
        self.rec_res = tk.StringVar()
        self.rec_lvl = tk.IntVar(value=1)
        self.rec_xp = tk.IntVar(value=25)
        self.rec_mats = tk.StringVar(value='{"iron_ore": 2, "wood_log": 1}')

        r_rows = [
            ("ID рецепта:", ttk.Entry(right, textvariable=self.rec_id, width=26)),
            ("Профессия:", ttk.Combobox(right, textvariable=self.rec_prof, width=23, values=self.get_prof_ids())),
            ("Результат (ID предмета):", ttk.Entry(right, textvariable=self.rec_res, width=26)),
            ("Требуемый уровень:", ttk.Spinbox(right, from_=1, to=50, textvariable=self.rec_lvl, width=8)),
            ("Опыт за создание:", ttk.Spinbox(right, from_=5, to=1000, textvariable=self.rec_xp, width=8)),
            ("Материалы (JSON):", ttk.Entry(right, textvariable=self.rec_mats, width=26)),
        ]
        for idx, (lbl, w) in enumerate(r_rows):
            ttk.Label(right, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=3)
            w.grid(row=idx, column=1, sticky=tk.W, pady=3, padx=5)

        r_btns = ttk.Frame(right)
        r_btns.grid(row=6, column=0, columnspan=2, pady=8)
        ttk.Button(r_btns, text="Сохранить рецепт", command=self.save_recipe).pack(side=tk.LEFT, padx=4)
        ttk.Button(r_btns, text="Удалить", command=self.delete_recipe).pack(side=tk.LEFT, padx=4)

        self.rec_tree = ttk.Treeview(right, columns=("id", "prof", "res", "lvl", "mats"), show="headings", height=10)
        for c, t, w in [("id", "ID", 95), ("prof", "Профессия", 85), ("res", "Результат", 105), ("lvl", "Ур.", 40), ("mats", "Ресурсы", 160)]:
            self.rec_tree.heading(c, text=t)
            self.rec_tree.column(c, width=w)
        self.rec_tree.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW, pady=6)
        self.rec_tree.bind("<<TreeviewSelect>>", self.on_rec_select)

        self.refresh_professions_tables()

    def get_prof_ids(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM professions_catalog ORDER BY id")
        return [r["id"] for r in cur.fetchall()]

    def refresh_professions_tables(self):
        for r in self.prof_tree.get_children():
            self.prof_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM professions_catalog")
        for r in cur.fetchall():
            self.prof_tree.insert("", tk.END, values=(r["id"], r["name"], r["bonus_type"], r["desc"]))

        for r in self.rec_tree.get_children():
            self.rec_tree.delete(r)
        cur.execute("SELECT * FROM recipes_catalog")
        for r in cur.fetchall():
            self.rec_tree.insert("", tk.END, values=(r["id"], r["prof_id"], r["result_item_id"], r["req_level"], r["materials_json"]))

    def on_prof_select(self, _):
        sel = self.prof_tree.selection()
        if not sel:
            return
        pid, pname, ptype, pdesc = self.prof_tree.item(sel)["values"]
        self.pr_id.set(pid)
        self.pr_name.set(pname)
        self.pr_btype.set(ptype)
        self.pr_desc.set(pdesc)

    def save_profession(self):
        pid = self.pr_id.get().strip()
        if not pid:
            return
        self.db.conn.execute("INSERT OR REPLACE INTO professions_catalog VALUES (?, ?, ?, ?)",
                             (pid, self.pr_name.get().strip(), self.pr_desc.get(), self.pr_btype.get()))
        self.db.conn.commit()
        self.refresh_professions_tables()
        self.set_status(f"Профессия '{pid}' сохранена.")

    def delete_profession(self):
        pid = self.pr_id.get().strip()
        if pid:
            self.db.conn.execute("DELETE FROM professions_catalog WHERE id = ?", (pid,))
            self.db.conn.commit()
            self.refresh_professions_tables()

    def on_rec_select(self, _):
        sel = self.rec_tree.selection()
        if not sel:
            return
        rid, rprof, rres, rlvl, rmats = self.rec_tree.item(sel)["values"]
        self.rec_id.set(rid)
        self.rec_prof.set(rprof)
        self.rec_res.set(rres)
        self.rec_lvl.set(rlvl)
        self.rec_mats.set(rmats)
        cur = self.db.conn.cursor()
        cur.execute("SELECT xp_gain FROM recipes_catalog WHERE id = ?", (rid,))
        row = cur.fetchone()
        if row:
            self.rec_xp.set(row["xp_gain"])

    def save_recipe(self):
        rid = self.rec_id.get().strip()
        if not rid:
            return
        try:
            json.loads(self.rec_mats.get())
        except Exception:
            messagebox.showerror("Ошибка", 'Материалы должны быть в формате JSON, например: {"iron_ore": 2}')
            return
        self.db.conn.execute("INSERT OR REPLACE INTO recipes_catalog VALUES (?, ?, ?, ?, ?, ?)",
                             (rid, self.rec_prof.get().strip(), self.rec_res.get().strip(),
                              self.rec_lvl.get(), self.rec_mats.get(), self.rec_xp.get()))
        self.db.conn.commit()
        self.refresh_professions_tables()
        self.set_status(f"Рецепт '{rid}' сохранен.")

    def delete_recipe(self):
        rid = self.rec_id.get().strip()
        if rid:
            self.db.conn.execute("DELETE FROM recipes_catalog WHERE id = ?", (rid,))
            self.db.conn.commit()
            self.refresh_professions_tables()

    # =========================================================================
    # 9. ВКЛАДКА НПС И КОНСТРУКТОРА ВНЕШНОСТИ
    # =========================================================================
    def build_npcs_tab(self):
        from appearance import BODY_LAYERS, HEAD_LAYERS, HAIR_LAYERS, SKIN_COLORS, HAIR_COLORS, EYE_COLORS, CLOTH_COLORS

        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="9. НПС и Внешность")

        # Левая колонка: Основные параметры НПС
        left = ttk.LabelFrame(tab, text="Параметры НПС / Объекта", padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self.npc_id = tk.StringVar()
        self.npc_loc = tk.StringVar(value="town_square")
        self.npc_name = tk.StringVar()
        self.npc_x = tk.IntVar(value=250)
        self.npc_y = tk.IntVar(value=180)
        self.npc_faction = tk.StringVar(value="town")
        self.npc_role = tk.StringVar(value="merchant")
        self.npc_sprite = tk.StringVar(value="npc")
        self.npc_speed = tk.IntVar(value=35)
        self.npc_gold = tk.IntVar(value=100)
        self.npc_hp = tk.IntVar(value=60)
        self.npc_str = tk.IntVar(value=3)
        self.npc_items = tk.StringVar(value="potion, mana_potion")
        self.npc_greet = tk.StringVar(value="Приветствую, путник!")
        self.npc_teach = tk.StringVar(value="")

        rows = [
            ("ID шаблона:", ttk.Entry(left, textvariable=self.npc_id, width=24)),
            ("Локация:", ttk.Entry(left, textvariable=self.npc_loc, width=24)),
            ("Имя в игре:", ttk.Entry(left, textvariable=self.npc_name, width=24)),
            ("Координата X:", ttk.Spinbox(left, from_=16, to=2000, textvariable=self.npc_x, width=10)),
            ("Координата Y:", ttk.Spinbox(left, from_=16, to=2000, textvariable=self.npc_y, width=10)),
            ("Фракция:", ttk.Combobox(left, textvariable=self.npc_faction, width=21, values=self.get_faction_ids())),
            ("Роль ИИ:", ttk.Combobox(left, textvariable=self.npc_role, state="readonly", width=21, values=["", "merchant", "guard", "adventurer", "monster"])),
            ("Запасной спрайт:", ttk.Combobox(left, textvariable=self.npc_sprite, width=21, values=self.get_sprite_keys())),
            ("Скорость / Золото:", self.make_dual_spin(left, self.npc_speed, self.npc_gold)),
            ("HP / Сила:", self.make_dual_spin(left, self.npc_hp, self.npc_str)),
            ("Предметы (ID):", ttk.Entry(left, textvariable=self.npc_items, width=24)),
            ("Приветствие:", ttk.Entry(left, textvariable=self.npc_greet, width=24)),
            ("Обучает профессии:", ttk.Combobox(left, textvariable=self.npc_teach, width=21, values=[""] + self.get_prof_ids())),
        ]
        for idx, (lbl, w) in enumerate(rows):
            ttk.Label(left, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=2)
            w.grid(row=idx, column=1, sticky=tk.W, pady=2, padx=4)

        # Средняя колонка: Конструктор внешности из запчастей
        mid = ttk.LabelFrame(tab, text="Внешность (Запчасти)", padding=8)
        mid.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self.npc_app_mode = tk.StringVar(value="custom")
        ttk.Radiobutton(mid, text="Обычный спрайт (без сборки)", variable=self.npc_app_mode, value="sprite", command=self.update_npc_preview).pack(anchor=tk.W)
        ttk.Radiobutton(mid, text="Случайная при старте", variable=self.npc_app_mode, value="random", command=self.update_npc_preview).pack(anchor=tk.W)
        ttk.Radiobutton(mid, text="Собрать из запчастей:", variable=self.npc_app_mode, value="custom", command=self.update_npc_preview).pack(anchor=tk.W, pady=(0, 6))

        self.npc_preview_cv = tk.Canvas(mid, width=64, height=64, bg="#232734", highlightthickness=1)
        self.npc_preview_cv.pack(pady=4)

        self.app_body_var = tk.StringVar(value="tunic")
        self.app_head_var = tk.StringVar(value="human")
        self.app_hair_var = tk.StringVar(value="short")
        self.app_skin_var = tk.IntVar(value=0)
        self.app_hair_col_var = tk.IntVar(value=0)
        self.app_eye_col_var = tk.IntVar(value=0)
        self.app_cloth_col_var = tk.IntVar(value=0)

        app_controls = [
            ("Одежда:", ttk.Combobox(mid, textvariable=self.app_body_var, state="readonly", width=18, values=list(BODY_LAYERS.keys()))),
            ("Голова:", ttk.Combobox(mid, textvariable=self.app_head_var, state="readonly", width=18, values=list(HEAD_LAYERS.keys()))),
            ("Прическа:", ttk.Combobox(mid, textvariable=self.app_hair_var, state="readonly", width=18, values=list(HAIR_LAYERS.keys()))),
            ("Кожа (индекс):", ttk.Spinbox(mid, from_=0, to=len(SKIN_COLORS)-1, textvariable=self.app_skin_var, width=6, command=self.update_npc_preview)),
            ("Цвет волос:", ttk.Spinbox(mid, from_=0, to=len(HAIR_COLORS)-1, textvariable=self.app_hair_col_var, width=6, command=self.update_npc_preview)),
            ("Цвет глаз:", ttk.Spinbox(mid, from_=0, to=len(EYE_COLORS)-1, textvariable=self.app_eye_col_var, width=6, command=self.update_npc_preview)),
            ("Цвет одежды:", ttk.Spinbox(mid, from_=0, to=len(CLOTH_COLORS)-1, textvariable=self.app_cloth_col_var, width=6, command=self.update_npc_preview)),
        ]
        app_grid = ttk.Frame(mid)
        app_grid.pack(fill=tk.X, pady=4)

        app_controls = [
            ("Одежда:", ttk.Combobox(app_grid, textvariable=self.app_body_var, state="readonly", width=18, values=list(BODY_LAYERS.keys()))),
            ("Голова:", ttk.Combobox(app_grid, textvariable=self.app_head_var, state="readonly", width=18, values=list(HEAD_LAYERS.keys()))),
            ("Прическа:", ttk.Combobox(app_grid, textvariable=self.app_hair_var, state="readonly", width=18, values=list(HAIR_LAYERS.keys()))),
            ("Кожа (индекс):", ttk.Spinbox(app_grid, from_=0, to=len(SKIN_COLORS)-1, textvariable=self.app_skin_var, width=6, command=self.update_npc_preview)),
            ("Цвет волос:", ttk.Spinbox(app_grid, from_=0, to=len(HAIR_COLORS)-1, textvariable=self.app_hair_col_var, width=6, command=self.update_npc_preview)),
            ("Цвет глаз:", ttk.Spinbox(app_grid, from_=0, to=len(EYE_COLORS)-1, textvariable=self.app_eye_col_var, width=6, command=self.update_npc_preview)),
            ("Цвет одежды:", ttk.Spinbox(app_grid, from_=0, to=len(CLOTH_COLORS)-1, textvariable=self.app_cloth_col_var, width=6, command=self.update_npc_preview)),
        ]
        for idx, (lbl, widget) in enumerate(app_controls):
            ttk.Label(app_grid, text=lbl).grid(row=idx, column=0, sticky=tk.W, pady=2)
            widget.grid(row=idx, column=1, sticky=tk.W, pady=2, padx=4)
            if isinstance(widget, ttk.Combobox):
                widget.bind("<<ComboboxSelected>>", lambda *_: self.update_npc_preview())

        btns = ttk.Frame(mid)
        btns.pack(pady=10)
        ttk.Button(btns, text="Сохранить НПС", command=self.save_npc).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Удалить", command=self.delete_npc).pack(side=tk.LEFT, padx=3)

        # Правая колонка: Таблица всех НПС в базе
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.npc_tree = ttk.Treeview(right, columns=("id", "loc", "name", "role", "pos"), show="headings")
        for c, t, w in [("id", "ID", 110), ("loc", "Локация", 100), ("name", "Имя", 130), ("role", "Роль", 85), ("pos", "X, Y", 80)]:
            self.npc_tree.heading(c, text=t)
            self.npc_tree.column(c, width=w)
        self.npc_tree.pack(fill=tk.BOTH, expand=True)
        self.npc_tree.bind("<<TreeviewSelect>>", self.on_npc_select)

        self.update_npc_preview()
        self.refresh_npcs_table()

    def make_dual_spin(self, parent, var1, var2):
        f = ttk.Frame(parent)
        ttk.Spinbox(f, from_=0, to=2000, textvariable=var1, width=7).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(f, from_=0, to=5000, textvariable=var2, width=7).pack(side=tk.LEFT)
        return f

    def get_current_npc_app_dict(self):
        return {
            "body": self.app_body_var.get(),
            "head": self.app_head_var.get(),
            "hair": self.app_hair_var.get(),
            "skin": self.app_skin_var.get(),
            "hair_color": self.app_hair_col_var.get(),
            "eye_color": self.app_eye_col_var.get(),
            "cloth_color": self.app_cloth_col_var.get(),
        }

    def update_npc_preview(self):
        from appearance import build_character_sprite
        self.npc_preview_cv.delete("all")
        if self.npc_app_mode.get() == "custom":
            surf = build_character_sprite(self.get_current_npc_app_dict())
            for y in range(16):
                for x in range(16):
                    r, g, b, a = surf.get_at((x, y))
                    if a > 0:
                        self.npc_preview_cv.create_rectangle(x * 4, y * 4, x * 4 + 4, y * 4 + 4, fill=rgb_to_hex((r, g, b)), outline="")

    def refresh_npcs_table(self):
        for r in self.npc_tree.get_children():
            self.npc_tree.delete(r)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM npc_templates ORDER BY location_id, name")
        for r in cur.fetchall():
            self.npc_tree.insert("", tk.END, values=(r["id"], r["location_id"], r["name"], r["role"] or "chest", f"{r['x']}, {r['y']}"))

    def on_npc_select(self, _):
        sel = self.npc_tree.selection()
        if not sel:
            return
        nid, *_ = self.npc_tree.item(sel)["values"]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM npc_templates WHERE id = ?", (nid,))
        r = cur.fetchone()
        if not r:
            return

        self.npc_id.set(r["id"])
        self.npc_loc.set(r["location_id"])
        self.npc_name.set(r["name"])
        self.npc_x.set(r["x"])
        self.npc_y.set(r["y"])
        self.npc_faction.set(r["faction"])
        self.npc_role.set(r["role"] or "")
        self.npc_sprite.set(r["sprite_key"])
        self.npc_speed.set(r["speed"])
        self.npc_gold.set(r["gold"])
        self.npc_items.set(", ".join(json.loads(r["items_json"])))

        st = json.loads(r["stats_json"])
        self.npc_hp.set(st.get("hp", 50))
        self.npc_str.set(st.get("str", 2))

        app_val = st.get("appearance")
        if app_val == "random":
            self.npc_app_mode.set("random")
        elif isinstance(app_val, dict):
            self.npc_app_mode.set("custom")
            self.app_body_var.set(app_val.get("body", "tunic"))
            self.app_head_var.set(app_val.get("head", "human"))
            self.app_hair_var.set(app_val.get("hair", "short"))
            self.app_skin_var.set(app_val.get("skin", 0))
            self.app_hair_col_var.set(app_val.get("hair_color", 0))
            self.app_eye_col_var.set(app_val.get("eye_color", 0))
            self.app_cloth_col_var.set(app_val.get("cloth_color", 0))
        else:
            self.npc_app_mode.set("sprite")

        dlg = json.loads(r["dialogue_json"]) if r["dialogue_json"] else {}
        self.npc_greet.set(dlg.get("greeting", ""))
        teach = dlg.get("teach_profession", {})
        self.npc_teach.set(teach.get("id", "") if isinstance(teach, dict) else "")
        self.update_npc_preview()

    def save_npc(self):
        nid = self.npc_id.get().strip()
        if not nid:
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT dialogue_json, is_container FROM npc_templates WHERE id = ?", (nid,))
        old = cur.fetchone()

        dlg = json.loads(old["dialogue_json"]) if (old and old["dialogue_json"]) else {}
        if self.npc_greet.get().strip():
            dlg["greeting"] = self.npc_greet.get().strip()
        teach_id = self.npc_teach.get().strip()
        if teach_id:
            dlg["teach_profession"] = {"id": teach_id, "cost": 40, "text": "Я научил тебя основам этого ремесла! Нажми [P], чтобы открыть верстак."}
        elif "teach_profession" in dlg:
            del dlg["teach_profession"]

        st = {"hp": self.npc_hp.get(), "mp": 20, "str": self.npc_str.get(), "end": 1}
        mode = self.npc_app_mode.get()
        if mode == "random":
            st["appearance"] = "random"
        elif mode == "custom":
            st["appearance"] = self.get_current_npc_app_dict()

        items_list = [i.strip() for i in self.npc_items.get().split(",") if i.strip()]
        is_cont = old["is_container"] if old else (1 if not self.npc_role.get() else 0)

        cur.execute("INSERT OR REPLACE INTO npc_templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (nid, self.npc_loc.get().strip(), self.npc_name.get().strip(), self.npc_x.get(), self.npc_y.get(),
                     "[210, 175, 65]", self.npc_sprite.get().strip() or "npc", self.npc_faction.get(), is_cont,
                     self.npc_role.get() or None, self.npc_speed.get(), 105, 16, self.npc_gold.get(),
                     json.dumps(st), json.dumps(items_list), json.dumps(dlg, ensure_ascii=False) if dlg else None))
        self.db.conn.commit()
        self.refresh_npcs_table()
        self.set_status(f"НПС '{self.npc_name.get()}' сохранен в БД!")

    def delete_npc(self):
        nid = self.npc_id.get().strip()
        if nid:
            self.db.conn.execute("DELETE FROM npc_templates WHERE id = ?", (nid,))
            self.db.conn.commit()
            self.refresh_npcs_table()

if __name__ == "__main__":
    root = tk.Tk()
    app = RPGContentStudio(root)
    root.mainloop()
