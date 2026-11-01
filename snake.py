import json
import math
import os
import random
import tkinter as tk
import tkinter.font as tkfont

CELL = 24
HUD_H = 52

SIZES = [
    ("Small", 20, 15),
    ("Medium", 28, 22),
    ("Large", 36, 27),
]

SPEEDS = [
    ("Chill", 160, 95),
    ("Normal", 120, 60),
    ("Fast", 85, 42),
]

PALETTES = {
    "Kuromi": ("#ff9ad8", "#b45cff", "#4b1078"),
    "Purple": ("#e6c8ff", "#b366ff", "#5b1e9e"),
    "Pink": ("#ffd0ea", "#ff4dc4", "#8f1e63"),
    "Violet": ("#d8b8ff", "#8a5cff", "#3d1a8f"),
    "Blue": ("#b8c8ff", "#4d7cff", "#22308f"),
    "Cyan": ("#b8ffff", "#22e6ff", "#0a6a7a"),
    "Green": ("#b6ffcf", "#39ff88", "#0d7a3f"),
    "Ice": ("#ffffff", "#cfd8e3", "#5b6672"),
}

POINTS_PER_FOOD = 10
SPEED_STEP = 4

BG = "#07030d"
GRID = "#1b0a2e"
PHOSPHOR = "#c77dff"
PHOSPHOR_DIM = "#8b4bb8"
PINK = "#ff5cc8"
TEXT = "#f2e4ff"
DIM = "#8a6aa8"
BORDER = "#3a1a5c"
PANEL = "#0e0618"
PANEL_SEL = "#1c0b31"
FOOD = PINK
FOOD_GLOW = "#3d0a2a"
GLOW = "#2a0d45"

_LETTERS = {
    "K": ["██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
}
BANNER = [" ".join(_LETTERS[ch][i] for ch in "KUROMI") for i in range(6)]

DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
KEYMAP = {
    "Up": "up", "w": "up", "W": "up",
    "Down": "down", "s": "down", "S": "down",
    "Left": "left", "a": "left", "A": "left",
    "Right": "right", "d": "right", "D": "right",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_FILE = os.path.join(BASE_DIR, ".snake_highscore")
SETTINGS_FILE = os.path.join(BASE_DIR, ".snake_settings.json")
DEFAULT_SETTINGS = {
    "color": "Kuromi",
    "size": "Medium",
    "speed": "Normal",
    "custom_color": "#b45cff",
}
COLOR_NAMES = list(PALETTES) + ["Custom"]


def lerp_color(start, end, t):
    t = max(0.0, min(1.0, t))
    a = [int(start[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(end[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def is_hex_color(value):
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return False
    try:
        int(value[1:], 16)
    except ValueError:
        return False
    return True


class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("kuromi // snake")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.settings = self.load_settings()
        self.high_score = self.load_high_score()

        self.cols, self.rows = self.size_dims()
        self.width = self.cols * CELL
        self.height = HUD_H + self.rows * CELL

        self.canvas = tk.Canvas(
            root, width=self.width, height=self.height, bg=BG, highlightthickness=0
        )
        self.canvas.pack()

        base = tkfont.nametofont("TkFixedFont")
        self.font_hud = base.copy()
        self.font_hud.configure(size=14, weight="bold")
        self.font_small = base.copy()
        self.font_small.configure(size=11, weight="bold")
        self.font_tiny = base.copy()
        self.font_tiny.configure(size=9)
        self.font_banner = base.copy()
        self.font_banner.configure(size=9)
        self.font_title = base.copy()
        self.font_title.configure(size=20, weight="bold")
        self.font_sub = base.copy()
        self.font_sub.configure(size=12)

        self.mode = "menu"
        self.sel = 0
        self.menu_sel = 0
        self.hitboxes = []
        self.tick_job = None
        self.blink_job = None
        self.blink = True

        self.reset_game("ready")
        self.apply_geometry()
        self.root.bind("<Key>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.draw()
        self.start_blink()

    def load_settings(self):
        settings = dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
        except (OSError, ValueError):
            saved = {}
        if isinstance(saved, dict):
            if saved.get("color") in COLOR_NAMES:
                settings["color"] = saved["color"]
            if saved.get("size") in [s[0] for s in SIZES]:
                settings["size"] = saved["size"]
            if saved.get("speed") in [s[0] for s in SPEEDS]:
                settings["speed"] = saved["speed"]
            custom = saved.get("custom_color")
            if is_hex_color(custom):
                settings["custom_color"] = custom
        return settings

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(self.settings, fh, indent=2)
        except OSError:
            pass

    def load_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as fh:
                return int(fh.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as fh:
                fh.write(str(self.high_score))
        except OSError:
            pass

    def palette(self):
        name = self.settings["color"]
        if name in PALETTES:
            return PALETTES[name]
        base = self.settings.get("custom_color", "#b45cff")
        if not is_hex_color(base):
            base = "#b45cff"
        return (lerp_color(base, "#ffffff", 0.45), base, lerp_color(base, "#000000", 0.55))

    def size_dims(self):
        for name, cols, rows in SIZES:
            if name == self.settings["size"]:
                return cols, rows
        return SIZES[1][1], SIZES[1][2]

    def speed_cfg(self):
        for name, start, fastest in SPEEDS:
            if name == self.settings["speed"]:
                return start, fastest
        return SPEEDS[1][1], SPEEDS[1][2]

    def apply_geometry(self):
        self.canvas.config(width=self.width, height=self.height)
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() - self.width) // 2)
        y = max(0, (self.root.winfo_screenheight() - self.height) // 2 - 20)
        self.root.geometry("%dx%d+%d+%d" % (self.width, self.height, x, y))
        self.root.update_idletasks()

    def apply_size(self):
        self.cols, self.rows = self.size_dims()
        self.width = self.cols * CELL
        self.height = HUD_H + self.rows * CELL
        self.reset_game("ready")
        self.apply_geometry()

    def reset_game(self, state):
        mid = self.rows // 2
        start = self.cols // 2
        self.snake = [(start, mid), (start - 1, mid), (start - 2, mid)]
        self.direction = "right"
        self.pending = []
        self.food_eaten = 0
        self.score = 0
        self.base_tick, self.min_tick = self.speed_cfg()
        self.tick_ms = self.base_tick
        self.food = self.spawn_food()
        self.state = state
        self.cancel_tick()

    def spawn_food(self):
        free = [(x, y) for y in range(self.rows) for x in range(self.cols)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def schedule(self):
        self.cancel_tick()
        self.tick_job = self.root.after(self.tick_ms, self.tick)

    def cancel_tick(self):
        if self.tick_job is not None:
            self.root.after_cancel(self.tick_job)
            self.tick_job = None

    def start_blink(self):
        self.blink_job = self.root.after(600, self.on_blink)

    def on_blink(self):
        self.blink = not self.blink
        if self.mode in ("menu", "settings"):
            self.draw()
        self.blink_job = self.root.after(600, self.on_blink)

    def cancel_blink(self):
        if self.blink_job is not None:
            self.root.after_cancel(self.blink_job)
            self.blink_job = None

    def tick(self):
        self.tick_job = None
        if self.mode != "game" or self.state != "running":
            return
        self.step()
        self.draw()
        if self.mode == "game" and self.state == "running":
            self.schedule()

    def step(self):
        if self.pending:
            candidate = self.pending.pop(0)
            if candidate != OPPOSITE[self.direction]:
                self.direction = candidate

        dx, dy = DIRECTIONS[self.direction]
        hx, hy = self.snake[0]
        nx, ny = hx + dx, hy + dy

        if not (0 <= nx < self.cols and 0 <= ny < self.rows):
            self.game_over()
            return

        eating = (nx, ny) == self.food
        body = self.snake if eating else self.snake[:-1]
        if (nx, ny) in body:
            self.game_over()
            return

        self.snake.insert(0, (nx, ny))
        if eating:
            self.food_eaten += 1
            self.score += POINTS_PER_FOOD
            self.tick_ms = max(self.min_tick, self.base_tick - SPEED_STEP * self.food_eaten)
            self.food = self.spawn_food()
            if self.food is None:
                self.win()
                return
        else:
            self.snake.pop()

    def game_over(self):
        self.state = "over"
        self.cancel_tick()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def win(self):
        self.state = "won"
        self.cancel_tick()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def on_key(self, event):
        key = event.keysym
        if self.mode == "settings":
            self.on_key_settings(key)
        elif self.mode == "menu":
            self.on_key_menu(key)
        else:
            self.on_key_game(key)

    def on_key_menu(self, key):
        if key == "Escape":
            self.quit()
        elif key in ("Up", "w", "W"):
            self.menu_sel = (self.menu_sel - 1) % 3
            self.draw()
        elif key in ("Down", "s", "S"):
            self.menu_sel = (self.menu_sel + 1) % 3
            self.draw()
        elif key in ("space", "Return", "KP_Enter"):
            self.activate_menu_item(self.menu_sel)
        elif key in ("c", "C"):
            self.open_settings()

    def activate_menu_item(self, index):
        if index == 0:
            self.start_game()
        elif index == 1:
            self.open_settings()
        else:
            self.quit()

    def on_key_settings(self, key):
        if key == "Escape":
            self.mode = "menu"
            self.draw()
        elif key in ("Up", "w", "W"):
            self.sel = (self.sel - 1) % 3
            self.draw()
        elif key in ("Down", "s", "S"):
            self.sel = (self.sel + 1) % 3
            self.draw()
        elif key in ("Left", "a", "A"):
            self.change_setting(-1)
        elif key in ("Right", "d", "D"):
            self.change_setting(1)
        elif key in ("space", "Return", "KP_Enter"):
            self.start_game()

    def on_key_game(self, key):
        if key == "Escape":
            self.cancel_tick()
            self.mode = "menu"
            self.draw()
            return
        if key in ("space", "Return", "KP_Enter"):
            self.toggle()
            return
        if key in ("r", "R"):
            self.reset_game("running")
            self.draw()
            self.schedule()
            return
        if key in KEYMAP and self.state in ("running", "ready"):
            self.turn(KEYMAP[key])

    def on_click(self, event):
        for x0, y0, x1, y1, callback in reversed(self.hitboxes):
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                callback()
                return

    def add_hitbox(self, x0, y0, x1, y1, callback):
        self.hitboxes.append((x0, y0, x1, y1, callback))

    def turn(self, new_dir):
        reference = self.pending[-1] if self.pending else self.direction
        if new_dir == reference or new_dir == OPPOSITE[reference]:
            return
        if len(self.pending) < 2:
            self.pending.append(new_dir)

    def toggle(self):
        if self.state == "ready":
            self.state = "running"
            self.draw()
            self.schedule()
        elif self.state == "running":
            self.state = "paused"
            self.cancel_tick()
            self.draw()
        elif self.state == "paused":
            self.state = "running"
            self.draw()
            self.schedule()
        else:
            self.reset_game("running")
            self.draw()
            self.schedule()

    def start_game(self):
        self.save_settings()
        if self.mode == "settings":
            self.apply_size()
        self.mode = "game"
        self.reset_game("running")
        self.draw()
        self.schedule()

    def change_setting(self, delta):
        key = ("color", "size", "speed")[self.sel]
        if key == "color":
            names = COLOR_NAMES
        elif key == "size":
            names = [s[0] for s in SIZES]
        else:
            names = [s[0] for s in SPEEDS]
        index = (names.index(self.settings[key]) + delta) % len(names)
        self.settings[key] = names[index]
        self.save_settings()
        if key == "size":
            self.apply_size()
        if key == "color" and self.settings["color"] == "Custom":
            self.open_color_picker()
        self.draw()

    def open_color_picker(self):
        from tkinter import colorchooser
        current = self.settings.get("custom_color", "#b45cff")
        if not is_hex_color(current):
            current = "#b45cff"
        _rgb, chosen = colorchooser.askcolor(
            color=current, parent=self.root, title="Pick a snake color"
        )
        if chosen:
            self.settings["custom_color"] = chosen
            self.settings["color"] = "Custom"
        self.save_settings()
        self.draw()

    def quit(self):
        self.cancel_tick()
        self.cancel_blink()
        self.root.destroy()

    def rounded(self, x0, y0, x1, y1, radius, **kwargs):
        r = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        pts = [
            x0 + r, y0, x1 - r, y0, x1, y0,
            x1, y0 + r, x1, y1 - r, x1, y1,
            x1 - r, y1, x0 + r, y1, x0, y1,
            x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kwargs)

    def draw(self):
        self.hitboxes = []
        if self.mode == "menu":
            self.draw_menu()
        elif self.mode == "settings":
            self.draw_settings()
        else:
            self.draw_game()
        self.draw_crt()

    def draw_crt(self):
        c = self.canvas
        for y in range(0, self.height, 3):
            c.create_line(0, y, self.width, y, fill="#000000", stipple="gray50",
                          tags="crt")

    def cursor(self):
        return "\u2588" if self.blink else " "

    def draw_banner(self, top):
        c = self.canvas
        char_w = self.font_banner.measure("M")
        widest = max(self.font_banner.measure(line) for line in BANNER)
        left = (self.width - widest) / 2
        line_h = self.font_banner.metrics("linespace")
        for i, line in enumerate(BANNER):
            c.create_text(left, top + i * line_h, anchor="nw", text=line,
                          fill=PHOSPHOR, font=self.font_banner)
        return top + len(BANNER) * line_h

    def draw_menu(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, self.width, self.height, fill=BG, outline="")

        c.create_text(16, 16, anchor="nw", text="kuromi@nightmare:~$ ./play " + self.cursor(),
                      fill=PHOSPHOR_DIM, font=self.font_tiny)

        banner_bottom = self.draw_banner(36)
        self.draw_decor_snake(self.width / 2, banner_bottom + 26)

        items = ["PLAY", "CUSTOMIZE", "QUIT"]
        top = banner_bottom + 56
        for i, label in enumerate(items):
            y = top + i * 32
            selected = i == self.menu_sel
            w = 240
            x0 = (self.width - w) / 2
            if selected:
                self.rounded(x0, y - 13, x0 + w, y + 13, 4, fill=PANEL_SEL, outline="")
            prefix = "> " if selected else "  "
            c.create_text(self.width / 2, y,
                          text="%s[ %s ]" % (prefix, label),
                          fill=PINK if selected else DIM,
                          font=self.font_sub)
            self.add_hitbox(x0, y - 14, x0 + w, y + 14,
                            lambda i=i: self.activate_menu_item(i))

        summary = "COLOR %s  //  SIZE %s  //  SPEED %s" % (
            self.settings["color"].upper(), self.settings["size"].upper(),
            self.settings["speed"].upper()
        )
        c.create_text(self.width / 2, top + 3 * 32 + 8, text=summary,
                      fill=DIM, font=self.font_tiny)
        c.create_text(self.width / 2, self.height - 38,
                      text="[ENTER] run   [UP/DOWN] select   [C] customize   [ESC] quit",
                      fill=DIM, font=self.font_tiny)
        c.create_text(self.width / 2, self.height - 20,
                      text="\u2665 BEST %06d \u2665" % self.high_score, fill=PINK,
                      font=self.font_tiny)

    def open_settings(self):
        self.mode = "settings"
        self.sel = 0
        self.draw()

    def draw_decor_snake(self, cx, cy):
        head, body, tail = self.palette()
        n = 11
        x = cx - (n * CELL * 0.8) / 2 + CELL / 2
        last_px = x
        last_py = cy
        for i in range(n):
            px = x + i * CELL * 0.8
            py = cy + math.sin(i * 0.62) * CELL * 0.8
            last_px, last_py = px, py
            color = head if i == 0 else lerp_color(body, tail, i / (n - 1))
            self.rounded(px - CELL * 0.34, py - CELL * 0.34,
                         px + CELL * 0.34, py + CELL * 0.34,
                         CELL * 0.3, fill=color, outline="")
        self.canvas.create_text(last_px + CELL * 0.62, last_py, text="\u2665",
                                fill=PINK, font=self.font_tiny)

    def draw_settings(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, self.width, self.height, fill=BG, outline="")

        c.create_text(16, 16, anchor="nw", text="kuromi@nightmare:~$ ./config " + self.cursor(),
                      fill=PHOSPHOR_DIM, font=self.font_tiny)
        c.create_text(self.width / 2, 62, text="// CUSTOMIZE", fill=PHOSPHOR,
                      font=self.font_title)
        self.draw_decor_snake(self.width / 2, 92)

        color_value = self.settings["color"]
        if color_value == "Custom":
            color_value = "Custom %s" % self.settings.get("custom_color", "")
        rows = [
            ("SNAKE_COLOR", color_value),
            ("MAP_SIZE", self.settings["size"]),
            ("SPEED", self.settings["speed"]),
        ]

        panel_w = min(self.width - 40, 460)
        left = (self.width - panel_w) / 2
        row_h = 38
        gap = 10
        block_h = len(rows) * row_h + (len(rows) - 1) * gap
        top = max(120, (self.height - block_h) / 2 + 14)

        for i, (label, value) in enumerate(rows):
            y = top + i * (row_h + gap)
            selected = i == self.sel
            self.rounded(left, y, left + panel_w, y + row_h, 4,
                         fill=PANEL_SEL if selected else PANEL, outline="")
            if selected:
                c.create_rectangle(left, y, left + 3, y + row_h,
                                   fill=PINK, outline="")
            c.create_text(left + 20, y + row_h / 2, anchor="w",
                          text=("> " if selected else "  ") + label,
                          fill=PHOSPHOR if selected else DIM, font=self.font_small)

            mid = left + panel_w - 92
            c.create_text(mid, y + row_h / 2, text="[ %s ]" % value,
                          fill=TEXT if selected else DIM, font=self.font_small)
            if selected:
                c.create_text(mid - 62, y + row_h / 2, text="<",
                              fill=PINK, font=self.font_small)
                c.create_text(mid + 62, y + row_h / 2, text=">",
                              fill=PINK, font=self.font_small)

            self.add_hitbox(left, y, left + panel_w, y + row_h,
                            lambda i=i: self.select_row(i))
            value_action = self.open_color_picker if i == 0 else (lambda i=i: self.cycle_row(i))
            self.add_hitbox(mid - 58, y + 4, mid + 58, y + row_h - 4, value_action)
            self.add_hitbox(mid - 74, y + 4, mid - 46, y + row_h - 4,
                            lambda i=i: self.step_row(i, -1))
            self.add_hitbox(mid + 46, y + 4, mid + 74, y + row_h - 4,
                            lambda i=i: self.step_row(i, 1))

        footer = self.height - 56
        c.create_text(self.width / 2, footer,
                      text="[ENTER] play   [ESC] back   [UP/DOWN] select   [LEFT/RIGHT] change",
                      fill=PHOSPHOR_DIM, font=self.font_tiny)
        c.create_text(self.width / 2, footer + 20,
                      text="click a value (or the selected row again) to change it",
                      fill=DIM, font=self.font_tiny)

    def select_row(self, index):
        if self.sel == index:
            self.cycle_row(index)
        else:
            self.sel = index
            self.draw()

    def step_row(self, index, delta):
        self.sel = index
        self.change_setting(delta)

    def cycle_row(self, index):
        self.sel = index
        self.change_setting(1)

    def cell_box(self, col, row, inset=2.0):
        x0 = col * CELL + inset
        y0 = HUD_H + row * CELL + inset
        return x0, y0, x0 + CELL - 2 * inset, y0 + CELL - 2 * inset

    def draw_game(self):
        c = self.canvas
        c.delete("all")
        self.draw_board()
        self.draw_food()
        self.draw_snake()
        self.draw_hud()

        if self.state == "ready":
            self.overlay("READY", ["PRESS SPACE TO START", "ESC RETURNS TO MENU"])
        elif self.state == "paused":
            self.overlay("PAUSED", ["PRESS SPACE TO RESUME"])
        elif self.state == "over":
            self.overlay("GAME OVER", [
                "SCORE %06d   BEST %06d" % (self.score, self.high_score),
                "ENTER RETRY    ESC MENU",
            ])
        elif self.state == "won":
            self.overlay("YOU WIN", [
                "SCORE %06d   BEST %06d" % (self.score, self.high_score),
                "ENTER RETRY    ESC MENU",
            ])

    def draw_board(self):
        c = self.canvas
        c.create_rectangle(0, HUD_H, self.width, self.height, fill=BG, outline=BORDER)
        for col in range(self.cols + 1):
            x = col * CELL
            c.create_line(x, HUD_H, x, self.height, fill=GRID)
        for row in range(self.rows + 1):
            y = HUD_H + row * CELL
            c.create_line(0, y, self.width, y, fill=GRID)

    def draw_food(self):
        if self.food is None:
            return
        col, row = self.food
        x0, y0, x1, y1 = self.cell_box(col, row, inset=2)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        c = self.canvas

        self.rounded(x0 - 3, y0 - 3, x1 + 3, y1 + 3, 6, fill=FOOD_GLOW, outline="")

        head_w = CELL * 0.6
        head_h = CELL * 0.5
        hx0 = cx - head_w / 2
        hy0 = cy - head_h / 2 - CELL * 0.06
        self.rounded(hx0, hy0, hx0 + head_w, hy0 + head_h, 4, fill=FOOD, outline="")

        jaw_w = head_w * 0.5
        jaw_top = hy0 + head_h - 1
        jaw_bottom = hy0 + head_h + CELL * 0.16
        self.rounded(cx - jaw_w / 2, jaw_top, cx + jaw_w / 2, jaw_bottom,
                     1.5, fill=FOOD, outline="")

        eye_dx = head_w * 0.21
        eye_r = CELL * 0.08
        eye_y = hy0 + head_h * 0.44
        for dx in (-eye_dx, eye_dx):
            c.create_oval(cx + dx - eye_r, eye_y - eye_r,
                          cx + dx + eye_r, eye_y + eye_r, fill=BG, outline="")

        tooth_y0 = jaw_top + CELL * 0.02
        for dx in (-jaw_w * 0.18, jaw_w * 0.18):
            c.create_line(cx + dx, tooth_y0, cx + dx, jaw_bottom - 1.5,
                          fill=BG, width=1.4)

    def draw_snake(self):
        c = self.canvas
        head, body, tail = self.palette()
        total = max(1, len(self.snake) - 1)
        for i in range(len(self.snake) - 1, -1, -1):
            col, row = self.snake[i]
            x0, y0, x1, y1 = self.cell_box(col, row, 1.5)
            color = head if i == 0 else lerp_color(body, tail, i / total)
            self.rounded(x0 - 2, y0 - 2, x1 + 2, y1 + 2, CELL * 0.32,
                         fill=GLOW, outline="")
            self.rounded(x0, y0, x1, y1, CELL * 0.28, fill=color, outline="")

        col, row = self.snake[0]
        cx = col * CELL + CELL / 2
        cy = HUD_H + row * CELL + CELL / 2
        if self.direction in ("left", "right"):
            ex = cx + (CELL * 0.16 if self.direction == "right" else -CELL * 0.16)
            for dy in (-CELL * 0.19, CELL * 0.19):
                c.create_oval(ex - 2.2, cy + dy - 2.2, ex + 2.2, cy + dy + 2.2,
                              fill=BG, outline="")
        else:
            ey = cy + (CELL * 0.16 if self.direction == "down" else -CELL * 0.16)
            for dx in (-CELL * 0.19, CELL * 0.19):
                c.create_oval(cx + dx - 2.2, ey - 2.2, cx + dx + 2.2, ey + 2.2,
                              fill=BG, outline="")

    def draw_hud(self):
        c = self.canvas
        c.create_rectangle(0, 0, self.width, HUD_H, fill=BG, outline="")
        c.create_text(16, HUD_H / 2, anchor="w",
                      text="SCORE %06d" % self.score, fill=PHOSPHOR, font=self.font_hud)
        c.create_text(self.width / 2, HUD_H / 2, anchor="center",
                      text="LEN %03d" % len(self.snake), fill=DIM, font=self.font_small)
        c.create_text(self.width - 16, HUD_H / 2, anchor="e",
                      text="BEST %06d" % self.high_score, fill=PINK,
                      font=self.font_small)
        c.create_line(0, HUD_H - 1, self.width, HUD_H - 1, fill=BORDER)

    def overlay(self, title, lines):
        c = self.canvas
        c.create_rectangle(0, HUD_H, self.width, self.height, fill="#000000",
                           stipple="gray50", outline="")
        panel_w = min(self.width - 48, 400)
        panel_h = 52 + len(lines) * 24 + 18
        x0 = (self.width - panel_w) / 2
        y0 = HUD_H + (self.height - HUD_H - panel_h) / 2
        self.rounded(x0, y0, x0 + panel_w, y0 + panel_h, 4,
                     fill=PANEL, outline=PHOSPHOR_DIM)
        c.create_text(self.width / 2, y0 + 26, text="[ %s ]" % title,
                      fill=PINK, font=self.font_title)
        for i, line in enumerate(lines):
            c.create_text(self.width / 2, y0 + 54 + i * 24, text=line,
                          fill=TEXT if i == 0 else DIM, font=self.font_small)


def main():
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
