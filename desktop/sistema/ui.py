from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .game import (
    ACHIEVEMENTS,
    ATTRIBUTE_LABELS,
    BALANCE_BONUS_XP,
    CATEGORY_LABELS,
    DAILY_BONUS_XP,
    DAILY_QUEST_COUNT,
    QUESTS,
    TIER_COLORS,
    TIER_NAMES,
    PlayerState,
    Quest,
    achievement_tier,
    adjusted_reward,
    category_completed,
    completed_today,
    daily_categories,
    get_daily_quests,
    is_day_complete,
    level_progress,
    metric_value,
    streak,
    sync_achievements,
    toggle_quest,
)
from .storage import PlayerStore
from .features_ui import FeaturePagesMixin

BG = "#05080F"
PANEL = "#080E18"
CARD = "#0E1623"
CARD_ELEVATED = "#111D2E"
CARD_DONE = "#0A252D"
BORDER = "#1E2B3D"
BORDER_LIGHT = "#30445C"
TEXT = "#F2F7FC"
MUTED = "#8291A6"
ACCENT = "#6FE7FF"
ACCENT_DARK = "#123443"
GOLD = "#D8B56A"
GREEN = "#67D9B0"
PURPLE = "#AE9AFF"
ORANGE = "#E8B77A"
FONT = "Segoe UI"
DISPLAY_FONT = "Segoe UI Variable Display"
CATEGORY_COLORS = {
    "body": "#6FE7FF",
    "mind": "#AE9AFF",
    "discipline": "#78AFFF",
    "recovery": "#67D9B0",
    "social": "#F0A6C4",
    "finance": "#D8B56A",
    "environment": "#8CC5B8",
    "creativity": "#D9A0FF",
}
MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
WEEKDAYS = ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def rounded_points(x1: float, y1: float, x2: float, y2: float, radius: float) -> list[float]:
    return [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2,
        x1 + radius, y2, x1, y2, x1, y2 - radius,
        x1, y1 + radius, x1, y1,
    ]


class ScrollFrame(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def fraction(self) -> float:
        return self.canvas.yview()[0]

    def restore(self, fraction: float) -> None:
        self.after_idle(lambda: self.canvas.yview_moveto(fraction))


class PremiumButton(tk.Canvas):
    def __init__(self, master: tk.Misc, text: str, command, done: bool = False, width: int = 154) -> None:
        super().__init__(
            master,
            width=width,
            height=44,
            bg=master.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.text = text
        self.command = command
        self.done = done
        self.hovered = False
        self.focused = False
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)
        self.bind("<Button-1>", self._click)
        self.bind("<Return>", self._click)
        self.bind("<space>", self._click)
        self.bind("<FocusIn>", self._focus_on)
        self.bind("<FocusOut>", self._focus_off)
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def _hover_on(self, _event: tk.Event) -> None:
        self.hovered = True
        self._draw()

    def _hover_off(self, _event: tk.Event) -> None:
        self.hovered = False
        self._draw()

    def _focus_on(self, _event: tk.Event) -> None:
        self.focused = True
        self._draw()

    def _focus_off(self, _event: tk.Event) -> None:
        self.focused = False
        self._draw()

    def _click(self, _event: tk.Event | None = None) -> None:
        self.command()

    def _draw(self) -> None:
        self.delete("all")
        width = max(120, self.winfo_width())
        fill = ACCENT if self.done else ("#1B4A5C" if self.hovered else ACCENT_DARK)
        if self.done and self.hovered:
            fill = "#9AEFFF"
        outline = "#FFFFFF" if self.focused else ("#A6F0FF" if self.hovered else ("#348397" if self.done else "#285568"))
        self.create_polygon(
            rounded_points(1, 1, width - 2, 43, 9),
            smooth=True,
            fill=fill,
            outline=outline,
            width=2 if self.focused else 1,
        )
        self.create_text(
            width / 2,
            22,
            text=self.text,
            fill=BG if self.done else ACCENT,
            font=(FONT, 9, "bold"),
        )


class HeroPanel(tk.Canvas):
    def __init__(self, master: tk.Misc, progress, total_xp: int) -> None:
        super().__init__(master, height=176, bg=BG, highlightthickness=0, bd=0)
        self.progress = progress
        self.total_xp = total_xp
        self.bind("<Configure>", lambda _event: self._draw())

    def _draw(self) -> None:
        self.delete("all")
        width = max(700, self.winfo_width())
        height = 176
        start = (17, 31, 50)
        end = (7, 14, 25)
        for y in range(height):
            ratio = y / height
            color = "#%02x%02x%02x" % tuple(int(start[i] * (1 - ratio) + end[i] * ratio) for i in range(3))
            self.create_line(0, y, width, y, fill=color)
        self.create_line(22, 0, width - 22, 0, fill=ACCENT, width=2)
        self.create_text(24, 22, text="ПРОФИЛЬ ИГРОКА  /  АКТИВЕН", anchor="w", fill=ACCENT, font=(FONT, 8, "bold"))
        self.create_text(24, 52, text="УРОВЕНЬ", anchor="w", fill=MUTED, font=(FONT, 9, "bold"))
        self.create_text(22, 106, text=str(self.progress.level), anchor="w", fill=TEXT, font=(DISPLAY_FONT, 48, "normal"))
        left = 176
        right = width - 168
        self.create_text(left, 48, text=f"{self.total_xp:,} XP".replace(",", " "), anchor="w", fill=TEXT, font=(FONT, 15, "bold"))
        self.create_text(left, 70, text="ОБЩИЙ ОПЫТ", anchor="w", fill=MUTED, font=(FONT, 8, "bold"))
        self.create_rectangle(left, 101, right, 106, fill="#223248", outline="")
        ratio = self.progress.current_xp / self.progress.needed_xp
        if ratio > 0:
            self.create_rectangle(left, 101, left + (right - left) * ratio, 106, fill=ACCENT, outline="")
        self.create_text(
            left,
            126,
            text=f"{self.progress.current_xp} / {self.progress.needed_xp} XP  ·  следующий уровень",
            anchor="w",
            fill=MUTED,
            font=(FONT, 9),
        )
        cx, cy = width - 82, 86
        self.create_oval(cx - 55, cy - 55, cx + 55, cy + 55, outline="#1D4257", width=1)
        self.create_oval(cx - 44, cy - 44, cx + 44, cy + 44, outline="#28637D", width=2)
        self.create_polygon(cx, cy - 39, cx + 34, cy, cx, cy + 39, cx - 34, cy, outline=ACCENT, width=2, fill="#102838")
        self.create_text(cx, cy - 2, text=self.progress.rank, fill=ACCENT, font=(DISPLAY_FONT, 27, "bold"))
        self.create_text(cx, 148, text="ТЕКУЩИЙ РАНГ", fill=MUTED, font=(FONT, 7, "bold"))


class TierEmblem(tk.Canvas):
    def __init__(self, master: tk.Misc, tier: int) -> None:
        super().__init__(master, width=48, height=52, bg=master.cget("bg"), highlightthickness=0, bd=0)
        color = TIER_COLORS[tier - 1] if tier else "#536177"
        points = (24, 2, 44, 13, 44, 37, 24, 50, 4, 37, 4, 13)
        self.create_polygon(points, fill="#111E2D", outline=color, width=2)
        self.create_text(24, 25, text=("I", "II", "III", "IV")[tier - 1] if tier else "—", fill=color, font=(FONT, 10, "bold"))


class SistemaApp(FeaturePagesMixin, tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("СИСТЕМА  /  Personal Ascension Protocol")
        self.geometry("1240x840")
        self.minsize(1100, 740)
        self.configure(bg=BG)
        try:
            self.iconbitmap(str(resource_path("assets/icon.ico")))
        except tk.TclError:
            pass
        self.store = PlayerStore()
        self.state: PlayerState = self.store.load()
        self.today = date.today()
        get_daily_quests(self.state, self.today)
        sync_achievements(self.state, self.today)
        self.store.save(self.state)
        self.current_page = "today"
        self.current_scroll: ScrollFrame | None = None
        self.nav_buttons: dict[str, tk.Button] = {}
        self.library_items: tk.Frame | None = None
        self._last_reminder_date: str | None = None
        self.withdraw()
        if not self._verify_pin():
            self.destroy()
            return
        self.deiconify()
        self._configure_styles()
        self._build_shell()
        self.show_page("today")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30000, self._check_date)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Vertical.TScrollbar",
            background=ACCENT_DARK,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            darkcolor=BG,
            lightcolor=BG,
        )

    def _build_shell(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar = tk.Frame(self, bg=PANEL, width=236, highlightbackground=BORDER, highlightthickness=1)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self.content = tk.Frame(self, bg=BG)
        self.content.grid(row=0, column=1, sticky="nsew")

        logo = tk.Canvas(sidebar, width=70, height=70, bg=PANEL, highlightthickness=0)
        logo.pack(pady=(26, 8))
        logo.create_oval(9, 9, 61, 61, outline="#17394C", width=1)
        logo.create_polygon(35, 5, 65, 35, 35, 65, 5, 35, outline=ACCENT, width=2)
        logo.create_polygon(35, 17, 53, 35, 35, 53, 17, 35, outline="#388CB4", width=2)
        logo.create_polygon(35, 27, 43, 35, 35, 43, 27, 35, fill=ACCENT, outline=ACCENT)
        self._label(sidebar, "СИСТЕМА", 22, TEXT, bold=True, bg=PANEL, font_name=DISPLAY_FONT).pack()
        self._label(sidebar, "PERSONAL ASCENSION PROTOCOL", 7, ACCENT, bold=True, bg=PANEL).pack(pady=(3, 20))

        profile = tk.Frame(sidebar, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        profile.pack(fill="x", padx=16, pady=(0, 22))
        self.side_level = self._label(profile, "УРОВЕНЬ 1  ·  РАНГ E", 10, TEXT, bold=True, bg=CARD)
        self.side_level.pack(anchor="w", padx=14, pady=(12, 2))
        self.side_xp = self._label(profile, "0 XP  ·  ПРОГРЕСС СОХРАНЁН", 7, MUTED, bold=True, bg=CARD)
        self.side_xp.pack(anchor="w", padx=14, pady=(0, 12))
        self._label(sidebar, "РАБОЧАЯ ОБЛАСТЬ", 7, MUTED, bold=True, bg=PANEL).pack(anchor="w", padx=24, pady=(0, 7))
        navigation = (
            ("today", "01   СЕГОДНЯ"),
            ("goals", "02   МОИ ЦЕЛИ"),
            ("library", "03   БИБЛИОТЕКА"),
            ("achievements", "04   ДОСТИЖЕНИЯ"),
            ("stats", "05   СТАТИСТИКА"),
            ("journal", "06   ДНЕВНИК"),
            ("chains", "07   ЦЕПОЧКИ"),
            ("settings", "08   НАСТРОЙКИ"),
        )
        for key, title in navigation:
            button = tk.Button(
                sidebar,
                text=title,
                anchor="w",
                padx=20,
                pady=13,
                bd=0,
                relief="flat",
                font=(FONT, 9, "bold"),
                fg=MUTED,
                bg=PANEL,
                activeforeground=TEXT,
                activebackground=CARD_ELEVATED,
                cursor="hand2",
                command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = button

        self._label(sidebar, "Локальные данные  ·  без облака\nПрогресс принадлежит только тебе", 8, MUTED, justify="center", bg=PANEL).pack(
            side="bottom", pady=20
        )
        self._label(sidebar, "●  ДАННЫЕ СОХРАНЕНЫ", 7, GREEN, bold=True, bg=PANEL).pack(side="bottom")

    def show_page(self, page: str) -> None:
        self.unbind_all("<MouseWheel>")
        self.current_page = page
        self.current_scroll = None
        for child in self.content.winfo_children():
            child.destroy()
        for key, button in self.nav_buttons.items():
            selected = key == page
            button.configure(
                bg=ACCENT_DARK if selected else PANEL,
                fg=ACCENT if selected else MUTED,
            )
        progress = level_progress(self.state.total_xp)
        self.side_level.configure(text=f"УРОВЕНЬ {progress.level}  ·  РАНГ {progress.rank}")
        self.side_xp.configure(text=f"{self.state.total_xp} XP  ·  {progress.current_xp} / {progress.needed_xp} ДО ЦЕЛИ")
        if page == "library":
            self._show_library()
        elif page == "achievements":
            self._show_achievements()
        elif page == "stats":
            self._show_stats()
        elif page == "goals":
            self._show_goals()
        elif page == "journal":
            self._show_journal()
        elif page == "chains":
            self._show_chains()
        elif page == "settings":
            self._show_settings()
        else:
            self.show_today()

    def show_today(self, scroll_fraction: float | None = None) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        scroll = ScrollFrame(self.content)
        scroll.pack(fill="both", expand=True)
        self.current_scroll = scroll
        page = scroll.inner
        progress = level_progress(self.state.total_xp)
        daily = get_daily_quests(self.state, self.today)
        done = completed_today(self.state, self.today)

        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", padx=28, pady=(28, 18))
        header.columnconfigure(0, weight=1)
        heading = tk.Frame(header, bg=BG)
        heading.grid(row=0, column=0, sticky="w")
        self._label(heading, "ЕЖЕДНЕВНЫЙ ПРОТОКОЛ", 24, TEXT, bold=True, font_name=DISPLAY_FONT).pack(anchor="w")
        self._label(
            heading,
            f"{self.today.day} {MONTHS[self.today.month - 1]}  /  персональный набор целей",
            10,
            MUTED,
        ).pack(anchor="w", pady=(5, 0))
        self._label(header, "DAILY  /  06", 9, GOLD, bold=True).grid(row=0, column=1, sticky="e")

        status = HeroPanel(page, progress, self.state.total_xp)
        status.pack(fill="x", padx=28, pady=(0, 14))

        metrics = tk.Frame(page, bg=BG)
        metrics.pack(fill="x", padx=26, pady=(0, 20))
        metrics.columnconfigure((0, 1, 2), weight=1, uniform="metrics")
        unlocked_count = len(self.state.unlocked_achievements)
        self._metric(metrics, 0, "ЗАДАНИЙ СЕГОДНЯ", f"{len(done)} / {DAILY_QUEST_COUNT}", ACCENT)
        self._metric(metrics, 1, "СЕРИЯ ПОЛНЫХ ДНЕЙ", str(streak(self.state, self.today)), GREEN)
        self._metric(metrics, 2, "СТУПЕНЕЙ ОТКРЫТО", f"{unlocked_count} / {len(ACHIEVEMENTS) * 4}", PURPLE)

        next_quest = next((quest for quest in daily if quest.id not in done), None)
        if next_quest is not None:
            focus = self._card(page, CARD_ELEVATED, ACCENT_DARK)
            focus.pack(fill="x", padx=26, pady=(0, 14))
            row = tk.Frame(focus, bg=CARD_ELEVATED); row.pack(fill="x", padx=16, pady=12)
            text = tk.Frame(row, bg=CARD_ELEVATED); text.pack(side="left", fill="x", expand=True)
            self._label(text, "СЛЕДУЮЩЕЕ ДЕЙСТВИЕ", 8, ACCENT, bold=True, bg=CARD_ELEVATED).pack(anchor="w")
            self._label(text, next_quest.title, 13, TEXT, bold=True, bg=CARD_ELEVATED, font_name=DISPLAY_FONT).pack(anchor="w", pady=(3, 0))
            PremiumButton(row, "НАЧАТЬ", command=lambda q=next_quest: self._toggle(q), width=112).pack(side="right", padx=(12, 0))

        title_row = tk.Frame(page, bg=BG)
        title_row.pack(fill="x", padx=26, pady=(2, 8))
        self._label(title_row, "ЗАДАНИЯ НА СЕГОДНЯ", 12, TEXT, bold=True).pack(side="left")
        directions = len(daily_categories(self.state, self.today))
        balance = f" · {directions}/4 НАПРАВЛЕНИЯ" if directions else " · БАЛАНС 0/4"
        self._label(title_row, f"+{DAILY_BONUS_XP} XP ЗА ПОЛНЫЙ ДЕНЬ · +{BALANCE_BONUS_XP} XP ЗА БАЛАНС{balance}", 8, ACCENT, bold=True).pack(side="right")

        for index, quest in enumerate(daily, start=1):
            self._quest_card(page, quest, quest.id in done, index).pack(fill="x", padx=28, pady=6)

        if is_day_complete(self.state, self.today):
            banner = self._card(page, CARD_DONE, "#287F98")
            banner.pack(fill="x", padx=26, pady=12)
            self._label(
                banner,
                f"ПОЛНЫЙ ДЕНЬ ЗАВЕРШЁН  ·  БОНУС +{DAILY_BONUS_XP} XP ПОЛУЧЕН",
                11,
                ACCENT,
                bold=True,
                bg=CARD_DONE,
            ).pack(padx=18, pady=15)
        else:
            self._label(
                page,
                "Выполняй действия в реальной жизни и отмечай их честно.\nСложность растёт постепенно — без резких скачков нагрузки.",
                10,
                MUTED,
                justify="center",
            ).pack(pady=18)
        if scroll_fraction is not None:
            scroll.restore(scroll_fraction)

    def _quest_card(self, master: tk.Misc, quest: Quest, done: bool, index: int) -> tk.Frame:
        bg = CARD_DONE if done else CARD
        border = "#2D8190" if done else BORDER
        category_color = CATEGORY_COLORS[quest.category]
        card = self._card(master, bg, border)
        body = tk.Frame(card, bg=bg)
        body.pack(fill="x", padx=18, pady=16)
        body.columnconfigure(1, weight=1)
        marker = tk.Canvas(body, width=46, height=48, bg=bg, highlightthickness=0, bd=0)
        marker.grid(row=0, column=0, sticky="n", padx=(0, 14))
        marker.create_polygon(23, 3, 43, 24, 23, 45, 3, 24, fill="#111F2D", outline=category_color, width=1)
        marker.create_text(23, 24, text=f"{index:02d}", fill=category_color, font=(FONT, 9, "bold"))
        text = tk.Frame(body, bg=bg)
        text.grid(row=0, column=1, sticky="nsew")
        self._label(
            text,
            f"{CATEGORY_LABELS[quest.category]}  /  ИЗМЕРИМЫЙ РЕЗУЛЬТАТ",
            7,
            category_color,
            bold=True,
            bg=bg,
        ).pack(anchor="w")
        self._label(text, quest.title, 14, TEXT, bold=True, bg=bg, font_name=DISPLAY_FONT).pack(anchor="w", pady=(4, 5))
        self._label(
            text,
            quest.scaled_description(level_progress(self.state.total_xp).level, self.state.difficulty),
            10,
            "#A3B1C4",
            bg=bg,
            wraplength=650,
            justify="left",
        ).pack(anchor="w")
        reward = adjusted_reward(self.state, quest)
        self._label(
            text,
            f"+{reward} XP   /   +1 {ATTRIBUTE_LABELS[quest.attribute].upper()}",
            8,
            category_color,
            bold=True,
            bg=bg,
        ).pack(anchor="w", pady=(9, 0))
        action = PremiumButton(
            body,
            text="ВЫПОЛНЕНО" if done else "ЗАВЕРШИТЬ",
            done=done,
            command=lambda: self._toggle(quest),
        )
        action.grid(row=0, column=2, padx=(18, 0))
        self._add_card_hover(card, border)
        return card

    def _toggle(self, quest: Quest) -> None:
        fraction = self.current_scroll.fraction() if self.current_scroll else 0.0
        _completed, leveled_up, unlocks = toggle_quest(self.state, quest, self.today)
        self.store.save(self.state)
        self.show_today(fraction)
        progress = level_progress(self.state.total_xp)
        self.side_level.configure(text=f"УРОВЕНЬ {progress.level}  ·  РАНГ {progress.rank}")
        self.side_xp.configure(text=f"{self.state.total_xp} XP  ·  {progress.current_xp} / {progress.needed_xp} ДО ЦЕЛИ")
        messages = []
        if leveled_up:
            messages.append(f"Новый уровень: {progress.level}. Сложность и награды выросли.")
        if unlocks:
            achievement_lines = [f"{item.title} — {TIER_NAMES[tier - 1]}" for item, tier in unlocks]
            messages.append("Новые достижения:\n" + "\n".join(achievement_lines))
        if messages:
            messagebox.showinfo("СИСТЕМА", "\n\n".join(messages), parent=self)

    def _show_library(self) -> None:
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=26, pady=(26, 14))
        self._label(header, "БИБЛИОТЕКА ЗАДАНИЙ", 24, TEXT, bold=True, font_name=DISPLAY_FONT).pack(anchor="w")
        self._label(
            header,
            f"{len(QUESTS)} реальных действий · 8 направлений · новые цели открываются с уровнем",
            10,
            MUTED,
        ).pack(anchor="w", pady=(4, 0))
        controls = tk.Frame(self.content, bg=BG)
        controls.pack(fill="x", padx=26, pady=(0, 12))
        self.library_query = tk.StringVar()
        entry = tk.Entry(
            controls,
            textvariable=self.library_query,
            font=(FONT, 11),
            fg=TEXT,
            bg=CARD,
            insertbackground=ACCENT,
            selectbackground=ACCENT_DARK,
            relief="flat",
            bd=8,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        entry.insert(0, "")
        self.library_category = tk.StringVar(value="ВСЕ НАПРАВЛЕНИЯ")
        option = tk.OptionMenu(
            controls,
            self.library_category,
            "ВСЕ НАПРАВЛЕНИЯ",
            *CATEGORY_LABELS.values(),
        )
        option.configure(
            font=(FONT, 9, "bold"),
            fg=ACCENT,
            bg=ACCENT_DARK,
            activeforeground=TEXT,
            activebackground=ACCENT_DARK,
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
        )
        option["menu"].configure(bg=CARD, fg=TEXT, activebackground=ACCENT_DARK, activeforeground=TEXT)
        option.pack(side="right")
        scroll = ScrollFrame(self.content)
        scroll.pack(fill="both", expand=True)
        self.current_scroll = scroll
        self.library_items = scroll.inner
        self.library_query.trace_add("write", lambda *_: self._refresh_library())
        self.library_category.trace_add("write", lambda *_: self._refresh_library())
        self._refresh_library()

    def _refresh_library(self) -> None:
        if self.library_items is None or not self.library_items.winfo_exists():
            return
        for child in self.library_items.winfo_children():
            child.destroy()
        query = self.library_query.get().strip().lower()
        selected_label = self.library_category.get()
        level = level_progress(self.state.total_xp).level
        filtered = [
            quest for quest in QUESTS
            if (selected_label == "ВСЕ НАПРАВЛЕНИЯ" or CATEGORY_LABELS[quest.category] == selected_label)
            and (not query or query in quest.title.lower() or query in quest.description.lower())
        ]
        if not filtered:
            self._label(self.library_items, "Ничего не найдено. Измени запрос или фильтр.", 11, MUTED).pack(pady=40)
            return
        for quest in filtered:
            locked = quest.min_level > level
            card = self._card(self.library_items, CARD, BORDER)
            card.pack(fill="x", padx=26, pady=4)
            inner = tk.Frame(card, bg=CARD)
            inner.pack(fill="x", padx=16, pady=12)
            top = tk.Frame(inner, bg=CARD)
            top.pack(fill="x")
            self._label(top, CATEGORY_LABELS[quest.category], 8, CATEGORY_COLORS[quest.category], bold=True, bg=CARD).pack(side="left")
            status = f"ОТКРОЕТСЯ НА {quest.min_level} УРОВНЕ" if locked else f"+{quest.reward(level)} XP"
            self._label(top, status, 8, GOLD if locked else MUTED, bold=True, bg=CARD).pack(side="right")
            self._label(inner, quest.title, 13, TEXT, bold=True, bg=CARD, font_name=DISPLAY_FONT).pack(anchor="w", pady=(4, 4))
            description = "Продолжай повышать уровень, чтобы открыть это задание." if locked else quest.scaled_description(level)
            self._label(inner, description, 9, MUTED, bg=CARD, wraplength=700, justify="left").pack(anchor="w")
            count = category_completed(self.state, quest.category)
            self._label(inner, f"Выполнено в направлении: {count}", 8, MUTED, bg=CARD).pack(anchor="w", pady=(5, 0))

    def _show_achievements(self) -> None:
        scroll = ScrollFrame(self.content)
        scroll.pack(fill="both", expand=True)
        self.current_scroll = scroll
        page = scroll.inner
        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", padx=26, pady=(26, 16))
        self._label(header, "ДОСТИЖЕНИЯ", 24, TEXT, bold=True, font_name=DISPLAY_FONT).pack(anchor="w")
        self._label(
            header,
            "Бронза → серебро → золото → платина. Открытые ступени остаются навсегда.",
            10,
            MUTED,
        ).pack(anchor="w", pady=(4, 0))
        grid = tk.Frame(page, bg=BG)
        grid.pack(fill="both", expand=True, padx=20, pady=(0, 24))
        grid.columnconfigure((0, 1), weight=1, uniform="achievement")
        for index, achievement in enumerate(ACHIEVEMENTS):
            card = self._achievement_card(grid, achievement)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)

    def _achievement_card(self, master: tk.Misc, achievement) -> tk.Frame:
        tier = achievement_tier(self.state, achievement)
        value = metric_value(self.state, achievement.metric, self.today)
        accent = TIER_COLORS[tier - 1] if tier else "#536177"
        border = accent if tier else BORDER
        card = self._card(master, CARD, border)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True, padx=17, pady=15)
        top = tk.Frame(inner, bg=CARD)
        top.pack(fill="x")
        TierEmblem(top, tier).pack(side="left")
        title = tk.Frame(top, bg=CARD)
        title.pack(side="left", fill="x", expand=True, padx=11)
        hidden = achievement.secret and tier == 0
        self._label(title, "СЕКРЕТНАЯ НАГРАДА" if hidden else achievement.title, 13, TEXT, bold=True, bg=CARD, font_name=DISPLAY_FONT).pack(anchor="w")
        self._label(title, "Открой, чтобы узнать условие" if hidden else achievement.description, 8, MUTED, bg=CARD).pack(anchor="w", pady=(3, 0))
        tier_label = f"СТУПЕНЬ {tier} / 4" if tier else "ЗАПЕЧАТАНО"
        self._label(top, tier_label, 7, accent, bold=True, bg=CARD).pack(side="right", anchor="n", pady=4)
        pips = tk.Frame(inner, bg=CARD)
        pips.pack(fill="x", pady=(12, 10))
        for index in range(4):
            color = TIER_COLORS[index] if index < tier else BORDER
            tk.Frame(pips, bg=color, height=3).pack(side="left", fill="x", expand=True, padx=(0, 6))
        if tier == 4:
            self._label(inner, "ПЛАТИНА  /  АБСОЛЮТНЫЙ РЕЗУЛЬТАТ", 9, accent, bold=True, bg=CARD).pack(anchor="w")
            self._label(inner, f"Всего накоплено: {value}", 9, MUTED, bg=CARD).pack(anchor="w", pady=(6, 0))
        else:
            threshold = achievement.thresholds[tier]
            tier_name = "НЕ ОТКРЫТО" if tier == 0 else TIER_NAMES[tier - 1]
            self._label(inner, f"{tier_name}  /  СЛЕДУЕТ {TIER_NAMES[tier]}", 8, accent, bold=True, bg=CARD).pack(anchor="w")
            self._progress_bar(inner, min(value, threshold), threshold, color=accent, height=4).pack(fill="x", pady=9)
            remaining = max(0, threshold - value)
            self._label(inner, f"{value} / {threshold}   ·   осталось {remaining}", 8, MUTED, bg=CARD).pack(anchor="w")
        self._add_card_hover(card, border)
        return card

    def _show_stats(self) -> None:
        scroll = ScrollFrame(self.content)
        scroll.pack(fill="both", expand=True)
        self.current_scroll = scroll
        page = scroll.inner
        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", padx=26, pady=(26, 16))
        self._label(header, "СТАТИСТИКА ИГРОКА", 24, TEXT, bold=True, font_name=DISPLAY_FONT).pack(anchor="w")
        self._label(header, "Каждая отметка отражает реальное действие", 10, MUTED).pack(anchor="w", pady=(4, 0))
        grid = tk.Frame(page, bg=BG)
        grid.pack(fill="x", padx=20)
        grid.columnconfigure((0, 1, 2), weight=1, uniform="stats")
        for index, (key, label) in enumerate(ATTRIBUTE_LABELS.items()):
            value = self.state.attributes.get(key, 0)
            card = self._card(grid, CARD, BORDER)
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=6, pady=6)
            self._label(card, label.upper(), 9, MUTED, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 2))
            self._label(card, f"{value:02d}", 27, TEXT, font_name="Segoe UI Light", bg=CARD).pack(anchor="w", padx=16)
            next_goal = ((value // 10) + 1) * 10
            self._progress_bar(card, value % 10 if value % 10 else (10 if value else 0), 10, height=4).pack(
                fill="x", padx=16, pady=(7, 4)
            )
            self._label(card, f"До отметки {next_goal}", 8, MUTED, bg=CARD).pack(anchor="w", padx=16, pady=(0, 13))

        activity = self._card(page, CARD, BORDER)
        activity.pack(fill="x", padx=26, pady=18)
        self._label(activity, "АКТИВНОСТЬ ЗА 7 ДНЕЙ", 10, TEXT, bold=True, bg=CARD).pack(anchor="w", padx=18, pady=(16, 0))
        chart = tk.Canvas(activity, height=190, bg=CARD, highlightthickness=0)
        chart.pack(fill="x", padx=18, pady=12)
        chart.bind("<Configure>", lambda event: self._draw_activity(chart))
        self._draw_activity(chart)
        calendar = self._card(page, CARD, BORDER)
        calendar.pack(fill="x", padx=26, pady=(0, 18))
        self._label(calendar, "КАЛЕНДАРЬ ВОСХОЖДЕНИЯ · 28 ДНЕЙ", 10, TEXT, bold=True, bg=CARD).pack(anchor="w", padx=18, pady=(16, 8))
        grid = tk.Frame(calendar, bg=CARD)
        grid.pack(fill="x", padx=18, pady=(0, 16))
        for column, label in enumerate(WEEKDAYS):
            self._label(grid, label, 7, MUTED, bold=True, bg=CARD, width=5).grid(row=0, column=column, padx=2, pady=(0, 5))
        for offset in range(27, -1, -1):
            day = self.today - timedelta(days=offset)
            count = len(completed_today(self.state, day))
            complete = is_day_complete(self.state, day)
            fill = GREEN if complete else ACCENT_DARK if count else "#101926"
            text = BG if complete else (ACCENT if count else MUTED)
            cell = tk.Label(grid, text=f"{day.day:02d}\n{count}", width=5, height=2, font=(FONT, 8, "bold"), fg=text, bg=fill)
            index = 27 - offset
            cell.grid(row=index // 7 + 1, column=index % 7, padx=2, pady=2)
        total = sum(len(ids) for ids in self.state.history.values())
        self._label(
            page,
            f"Всего выполнено: {total}   ·   Полных дней: {metric_value(self.state, 'perfect', self.today)}   ·   Всего XP: {self.state.total_xp}",
            10,
            ACCENT,
            bold=True,
        ).pack(pady=(0, 26))

    def _draw_activity(self, canvas: tk.Canvas) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 500)
        height = 160
        days = [self.today - timedelta(days=6 - index) for index in range(7)]
        values = [len(self.state.history.get(day.isoformat(), set())) for day in days]
        slot = width / 7
        for level in (0, 3, 6):
            y = 125 - level * 18
            canvas.create_line(12, y, width - 12, y, fill="#172434", width=1)
            canvas.create_text(width - 12, y - 8, text=str(level), fill="#536177", font=(FONT, 7), anchor="e")
        for index, (day, value) in enumerate(zip(days, values)):
            x = slot * index + slot * 0.30
            bar_width = slot * 0.36
            bar_height = min(108, value * 18)
            canvas.create_rectangle(x, 125 - bar_height, x + bar_width, 125, fill=ACCENT if value else BORDER, width=0)
            canvas.create_text(x + bar_width / 2, 144, text=f"{WEEKDAYS[day.weekday()]}  {day.day:02d}", fill=MUTED, font=(FONT, 8, "bold"))
            canvas.create_text(x + bar_width / 2, 113 - bar_height, text=str(value), fill=TEXT, font=(FONT, 9, "bold"))

    def _metric(self, master: tk.Misc, column: int, title: str, value: str, color: str) -> None:
        card = self._card(master, CARD, BORDER)
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        self._label(card, title, 8, MUTED, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(13, 2))
        self._label(card, value, 22, color, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(0, 12))

    def _progress_bar(self, master: tk.Misc, value: int, maximum: int, color: str = ACCENT, height: int = 7) -> tk.Canvas:
        canvas = tk.Canvas(master, height=height, bg=master.cget("bg"), highlightthickness=0, bd=0)

        def draw(_event: tk.Event | None = None) -> None:
            canvas.delete("all")
            width = max(1, canvas.winfo_width())
            canvas.create_rectangle(0, 0, width, height, fill=BORDER, width=0)
            ratio = 0 if maximum <= 0 else min(1.0, max(0.0, value / maximum))
            if ratio > 0:
                canvas.create_rectangle(0, 0, int(width * ratio), height, fill=color, width=0)

        canvas.bind("<Configure>", draw)
        canvas.after_idle(draw)
        return canvas

    def _card(self, master: tk.Misc, bg: str, border: str) -> tk.Frame:
        return tk.Frame(master, bg=bg, highlightbackground=border, highlightcolor=border, highlightthickness=1, bd=0)

    def _add_card_hover(self, card: tk.Frame, border: str) -> None:
        def enter(_event: tk.Event) -> None:
            card.configure(highlightbackground=BORDER_LIGHT, highlightcolor=BORDER_LIGHT)

        def leave(_event: tk.Event) -> None:
            card.configure(highlightbackground=border, highlightcolor=border)

        def bind_recursive(widget: tk.Widget) -> None:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(card)

    def _label(
        self,
        master: tk.Misc,
        text: str,
        size: int,
        color: str,
        bold: bool = False,
        bg: str = BG,
        font_name: str = FONT,
        **kwargs,
    ) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(master, text=text, font=(font_name, size, weight), fg=color, bg=bg, **kwargs)

    def _check_date(self) -> None:
        current = date.today()
        if current != self.today:
            self.today = current
            get_daily_quests(self.state, self.today)
            self.store.save(self.state)
            self.show_page(self.current_page)
        now = datetime.now()
        if (self.state.reminder_enabled and now.hour * 60 + now.minute >= self.state.reminder_minute
                and self._last_reminder_date != self.today.isoformat() and not is_day_complete(self.state, self.today)):
            self._last_reminder_date = self.today.isoformat()
            messagebox.showinfo("СИСТЕМА", "Ежедневный протокол ещё не завершён. Выбери следующее реальное действие.", parent=self)
        self.after(30000, self._check_date)

    def _on_close(self) -> None:
        self.store.save(self.state)
        self.destroy()
