import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

CONTROLS_TEXT = [
    "WASD / Стрелки — Передвижение героя",
    "Пробел / ЛКМ — Обычная атака / Выстрел / Магия",
    "1 / 2 — Применить активные навыки из книги",
    "F5 / F9 — Быстрое сохранение / Быстрая загрузка",
    "E — Взаимодействовать (Диалог, Лут, Торговля)",
    "I / Tab — Инвентарь и Экипировка (X — выбросить)",
    "J — Журнал заданий  |  K — Книга навыков  |  C — Статы",
    "M — Призвать случайного монстра (для теста)",
    "ESC — Закрыть окно или открыть Меню паузы"
]

AUTOSAVE_OPTIONS = [0, 1, 3, 5, 10]
FPS_OPTIONS = [60, 30]

class BaseMenu:
    def __init__(self, title, options, db=None):
        self.title = title
        self.options = options
        self.db = db
        self.cursor = 0
        self.sub_mode = None      # None, 'help', 'settings', 'save_select', 'load_select'
        self.sub_cursor = 0
        self.notice = ""

        self.font_huge = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_main = pygame.font.SysFont("consolas", 19)
        self.font_small = pygame.font.SysFont("consolas", 16)

    def get_save_rows(self, for_saving=False):
        if not self.db:
            return []
        rows = []
        if for_saving:
            rows.append(("new_slot", "+ Создать новый слот сохранения"))
            for s in self.db.get_all_saves(manual_only=True):
                label = f"Перезаписать: {s['slot_label']} — {s['player_name']} (Ур.{s['player_level']}) [{s['saved_at']}]"
                rows.append((s["slot_id"], label))
        else:
            for s in self.db.get_all_saves(manual_only=False):
                label = f"{s['slot_label']} — {s['player_name']} (Ур.{s['player_level']}) [{s['saved_at']}]"
                rows.append((s["slot_id"], label))
        return rows

    def handle_submode_event(self, event):
        box = pygame.Rect(210, 95, 860, 520)

        # --- УПРАВЛЕНИЕ МЫШЬЮ В ПОДМЕНЮ ---
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mx, my = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.sub_mode = None
                self.sub_cursor = 0
                return None

            if self.sub_mode == "help":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.sub_mode = None
                return None

            elif self.sub_mode == "settings" and self.db:
                for idx in range(4):
                    row_rect = pygame.Rect(box.x + 30, box.y + 82 + idx * 68, box.width - 60, 50)
                    if row_rect.collidepoint(mx, my):
                        self.sub_cursor = idx
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            delta = -1 if mx < box.centerx else 1
                            if idx == 0:
                                cur_val = self.db.settings["autosave_minutes"]
                                i = AUTOSAVE_OPTIONS.index(cur_val) if cur_val in AUTOSAVE_OPTIONS else 2
                                self.db.settings["autosave_minutes"] = AUTOSAVE_OPTIONS[(i + delta) % len(AUTOSAVE_OPTIONS)]
                                self.db.save_settings()
                            elif idx == 1:
                                self.db.settings["show_speech"] = not self.db.settings["show_speech"]
                                self.db.save_settings()
                            elif idx == 2:
                                cur_fps = self.db.settings["target_fps"]
                                i = FPS_OPTIONS.index(cur_fps) if cur_fps in FPS_OPTIONS else 0
                                self.db.settings["target_fps"] = FPS_OPTIONS[(i + delta) % len(FPS_OPTIONS)]
                                self.db.save_settings()
                            elif idx == 3:
                                self.sub_mode = None
                        break
                return None

            elif self.sub_mode in ("save_select", "load_select"):
                for_saving = (self.sub_mode == "save_select")
                rows = self.get_save_rows(for_saving)
                if not rows:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.sub_mode = None
                    return None
                for idx in range(min(8, len(rows))):
                    row_rect = pygame.Rect(box.x + 25, box.y + 66 + idx * 48, box.width - 50, 40)
                    if row_rect.collidepoint(mx, my):
                        self.sub_cursor = idx
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            slot_val, _ = rows[idx]
                            self.sub_mode = None
                            return ("do_save" if for_saving else "do_load", slot_val)
                        break
                return None

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            self.sub_mode = None
            self.sub_cursor = 0
            return None

        if self.sub_mode == "help":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.sub_mode = None
            return None

        elif self.sub_mode == "settings" and self.db:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.sub_cursor = (self.sub_cursor - 1) % 4
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.sub_cursor = (self.sub_cursor + 1) % 4
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN):
                delta = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                if self.sub_cursor == 0:
                    cur_val = self.db.settings["autosave_minutes"]
                    idx = AUTOSAVE_OPTIONS.index(cur_val) if cur_val in AUTOSAVE_OPTIONS else 2
                    self.db.settings["autosave_minutes"] = AUTOSAVE_OPTIONS[(idx + delta) % len(AUTOSAVE_OPTIONS)]
                    self.db.save_settings()
                elif self.sub_cursor == 1:
                    self.db.settings["show_speech"] = not self.db.settings["show_speech"]
                    self.db.save_settings()
                elif self.sub_cursor == 2:
                    cur_fps = self.db.settings["target_fps"]
                    idx = FPS_OPTIONS.index(cur_fps) if cur_fps in FPS_OPTIONS else 0
                    self.db.settings["target_fps"] = FPS_OPTIONS[(idx + delta) % len(FPS_OPTIONS)]
                    self.db.save_settings()
                elif self.sub_cursor == 3 and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.sub_mode = None
            return None

        elif self.sub_mode in ("save_select", "load_select"):
            for_saving = (self.sub_mode == "save_select")
            rows = self.get_save_rows(for_saving)
            if not rows:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.sub_mode = None
                return None

            if event.key in (pygame.K_UP, pygame.K_w):
                self.sub_cursor = (self.sub_cursor - 1) % len(rows)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.sub_cursor = (self.sub_cursor + 1) % len(rows)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                slot_val, _ = rows[self.sub_cursor]
                self.sub_mode = None
                return ("do_save" if for_saving else "do_load", slot_val)

        return None

    def handle_event(self, event):
        if self.sub_mode is not None:
            return self.handle_submode_event(event)

        # --- УПРАВЛЕНИЕ МЫШЬЮ В ОСНОВНОМ МЕНЮ ---
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mx, my = event.pos
            is_pause = isinstance(self, PauseMenu)
            if is_pause:
                box_w, box_h = 440, 505
                box_x = WINDOW_WIDTH // 2 - box_w // 2
                box_y = WINDOW_HEIGHT // 2 - box_h // 2
                btn_x, btn_w, btn_h = box_x + 25, box_w - 50, 44
                start_y, step_y = box_y + 62, 56
            else:
                menu_w = 420
                menu_x = WINDOW_WIDTH // 2 - menu_w // 2
                btn_x, btn_w, btn_h = menu_x + 25, menu_w - 50, 50
                start_y, step_y = 229, 65

            for idx in range(len(self.options)):
                btn_rect = pygame.Rect(btn_x, start_y + idx * step_y, btn_w, btn_h)
                if btn_rect.collidepoint(mx, my):
                    self.cursor = idx
                    self.notice = ""
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        action_id, _ = self.options[idx]
                        if action_id in ("help", "settings", "save_select", "load_select"):
                            self.sub_mode = action_id
                            self.sub_cursor = 0
                            return None
                        return (action_id, None)
                    break

        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self.cursor = (self.cursor - 1) % len(self.options)
            self.notice = ""
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.cursor = (self.cursor + 1) % len(self.options)
            self.notice = ""
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            action_id, _ = self.options[self.cursor]
            if action_id in ("help", "settings", "save_select", "load_select"):
                self.sub_mode = action_id
                self.sub_cursor = 0
                return None
            return (action_id, None)

        return None

    def draw_submode_overlay(self, surface):
        box = pygame.Rect(210, 95, 860, 520)
        pygame.draw.rect(surface, (20, 24, 34), box, border_radius=8)
        pygame.draw.rect(surface, (240, 195, 75), box, 2, border_radius=8)

        if self.sub_mode == "help":
            hdr = self.font_title.render("УПРАВЛЕНИЕ В ИГРЕ", True, (240, 195, 75))
            surface.blit(hdr, (box.centerx - hdr.get_width() // 2, box.y + 18))
            pygame.draw.line(surface, (240, 195, 75), (box.x + 20, box.y + 52), (box.right - 20, box.y + 52), 2)
            for i, line in enumerate(CONTROLS_TEXT):
                surface.blit(self.font_main.render(line, True, (220, 225, 235)), (box.x + 35, box.y + 72 + i * 42))
            foot = self.font_small.render("ESC / Enter — Назад", True, (150, 175, 205))
            surface.blit(foot, (box.centerx - foot.get_width() // 2, box.bottom - 35))

        elif self.sub_mode == "settings" and self.db:
            hdr = self.font_title.render("НАСТРОЙКИ ИГРЫ", True, (240, 195, 75))
            surface.blit(hdr, (box.centerx - hdr.get_width() // 2, box.y + 18))
            pygame.draw.line(surface, (240, 195, 75), (box.x + 20, box.y + 52), (box.right - 20, box.y + 52), 2)

            auto_m = self.db.settings["autosave_minutes"]
            auto_str = "Выключено" if auto_m == 0 else f"Каждые {auto_m} мин."
            speech_str = "Включены" if self.db.settings["show_speech"] else "Выключены"
            fps_str = f"{self.db.settings['target_fps']} FPS"

            rows = [
                f"Автосохранение:      ◀  {auto_str}  >",
                f"Реплики над головой: ◀  {speech_str}  >",
                f"Частота кадров:      ◀  {fps_str}  >",
                "Вернуться назад"
            ]
            for idx, txt_str in enumerate(rows):
                y = box.y + 90 + idx * 68
                is_sel = (self.sub_cursor == idx)
                if is_sel:
                    pygame.draw.rect(surface, (45, 58, 82), (box.x + 30, y - 8, box.width - 60, 50), border_radius=5)
                col = (255, 255, 255) if is_sel else (190, 200, 215)
                prefix = "> " if is_sel else "  "
                surface.blit(self.font_title.render(f"{prefix}{txt_str}", True, col), (box.x + 50, y + 6))

            foot = self.font_small.render("W/S: Выбор  |  A/D: Изменить параметр  |  ESC: Назад", True, (150, 175, 205))
            surface.blit(foot, (box.centerx - foot.get_width() // 2, box.bottom - 35))

        elif self.sub_mode in ("save_select", "load_select"):
            for_saving = (self.sub_mode == "save_select")
            title_txt = "СОХРАНИТЬ ИГРУ (ВЫБЕРИТЕ СЛОТ)" if for_saving else "ЗАГРУЗИТЬ ИГРУ (ВЫБЕРИТЕ СЛОТ)"
            hdr = self.font_title.render(title_txt, True, (240, 195, 75))
            surface.blit(hdr, (box.centerx - hdr.get_width() // 2, box.y + 18))
            pygame.draw.line(surface, (240, 195, 75), (box.x + 20, box.y + 52), (box.right - 20, box.y + 52), 2)

            rows = self.get_save_rows(for_saving)
            if not rows:
                surface.blit(self.font_main.render("Сохранений пока нет.", True, (150, 155, 170)), (box.x + 45, box.y + 100))
            else:
                for idx, (s_id, label) in enumerate(rows[:8]):
                    y = box.y + 72 + idx * 48
                    is_sel = (self.sub_cursor == idx)
                    if is_sel:
                        pygame.draw.rect(surface, (45, 58, 82), (box.x + 25, y - 6, box.width - 50, 40), border_radius=4)
                    col = (120, 235, 150) if s_id == "new_slot" else ((255, 255, 255) if is_sel else (195, 205, 220))
                    prefix = "> " if is_sel else "  "
                    surface.blit(self.font_main.render(f"{prefix}{label}", True, col), (box.x + 35, y + 4))

            foot = self.font_small.render("W/S: Выбор слота  |  Enter: Подтвердить  |  ESC: Отмена", True, (150, 175, 205))
            surface.blit(foot, (box.centerx - foot.get_width() // 2, box.bottom - 35))


class MainMenu(BaseMenu):
    def __init__(self, db):
        super().__init__(
            "8-BIT MODULAR RPG",
            [
                ("new_game", "Новая игра"),
                ("load_select", "Загрузить игру"),
                ("settings", "Настройки"),
                ("help", "Управление"),
                ("quit", "Выход из игры")
            ],
            db=db
        )

    def draw(self, surface):
        surface.fill((14, 17, 24))
        pygame.draw.rect(surface, (45, 55, 75), (30, 30, WINDOW_WIDTH - 60, WINDOW_HEIGHT - 60), 2, border_radius=10)

        title_surf = self.font_huge.render(self.title, True, (240, 195, 75))
        sub_surf = self.font_main.render("Модульная ролевая песочница", True, (130, 195, 230))
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 95))
        surface.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 145))

        if self.sub_mode is not None:
            self.draw_submode_overlay(surface)
            return

        menu_w, menu_h = 420, 365
        menu_x = WINDOW_WIDTH // 2 - menu_w // 2
        menu_y = 205
        pygame.draw.rect(surface, (20, 24, 34), (menu_x, menu_y, menu_w, menu_h), border_radius=8)
        pygame.draw.rect(surface, (85, 95, 115), (menu_x, menu_y, menu_w, menu_h), 2, border_radius=8)

        for idx, (_, label) in enumerate(self.options):
            btn_y = menu_y + 24 + idx * 65
            is_sel = (self.cursor == idx)
            btn_rect = pygame.Rect(menu_x + 25, btn_y, menu_w - 50, 50)
            if is_sel:
                pygame.draw.rect(surface, (45, 58, 82), btn_rect, border_radius=6)
                pygame.draw.rect(surface, (240, 195, 75), btn_rect, 2, border_radius=6)

            col = (255, 255, 255) if is_sel else (180, 185, 200)
            prefix = "> " if is_sel else "  "
            txt = self.font_title.render(f"{prefix}{label}", True, col)
            surface.blit(txt, (btn_rect.x + 20, btn_rect.centery - txt.get_height() // 2))

        if self.notice:
            n_surf = self.font_main.render(self.notice, True, (240, 130, 110))
            surface.blit(n_surf, (WINDOW_WIDTH // 2 - n_surf.get_width() // 2, menu_y + menu_h + 20))


class PauseMenu(BaseMenu):
    def __init__(self, db):
        super().__init__(
            "ПАУЗА",
            [
                ("resume", "Продолжить игру"),
                ("save_select", "Сохранить игру"),
                ("load_select", "Загрузить игру"),
                ("settings", "Настройки"),
                ("help", "Управление"),
                ("to_main", "В главное меню"),
                ("quit", "Выйти на рабочий стол")
            ],
            db=db
        )

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.sub_mode is None:
            return ("resume", None)
        return super().handle_event(event)

    def draw(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))

        if self.sub_mode is not None:
            self.draw_submode_overlay(surface)
            return

        box_w, box_h = 440, 505
        box_x = WINDOW_WIDTH // 2 - box_w // 2
        box_y = WINDOW_HEIGHT // 2 - box_h // 2
        box = pygame.Rect(box_x, box_y, box_w, box_h)

        pygame.draw.rect(surface, (20, 24, 34), box, border_radius=8)
        pygame.draw.rect(surface, (240, 195, 75), box, 2, border_radius=8)

        title_surf = self.font_title.render(self.title, True, (240, 195, 75))
        surface.blit(title_surf, (box.centerx - title_surf.get_width() // 2, box.y + 16))
        pygame.draw.line(surface, (240, 195, 75), (box.x + 20, box.y + 48), (box.right - 20, box.y + 48), 2)

        for idx, (_, label) in enumerate(self.options):
            btn_y = box.y + 62 + idx * 56
            is_sel = (self.cursor == idx)
            btn_rect = pygame.Rect(box.x + 25, btn_y, box.width - 50, 44)
            if is_sel:
                pygame.draw.rect(surface, (45, 58, 82), btn_rect, border_radius=6)
                pygame.draw.rect(surface, (240, 195, 75), btn_rect, 1, border_radius=6)

            col = (255, 255, 255) if is_sel else (185, 190, 205)
            prefix = "> " if is_sel else "  "
            txt = self.font_main.render(f"{prefix}{label}", True, col)
            surface.blit(txt, (btn_rect.x + 18, btn_rect.centery - txt.get_height() // 2))

        if self.notice:
            n_surf = self.font_small.render(self.notice, True, (120, 235, 150))
            surface.blit(n_surf, (box.centerx - n_surf.get_width() // 2, box.bottom - 26))
