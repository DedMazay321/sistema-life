from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import uuid

from .game import (
    ACHIEVEMENTS, CATEGORY_LABELS, CHAINS, CustomTask, DevelopmentArc, JournalEntry,
    PlayerState, achievement_tier, all_quests, arc_progress, chain_progress, custom_due, level_progress,
    sync_achievements, toggle_quest, toggle_weekly_done, toggle_weekly_task, week_key, weekly_recommendation,
)

BG, CARD, CARD_ELEVATED, BORDER = "#05080F", "#0E1623", "#111D2E", "#1E2B3D"
TEXT, MUTED, ACCENT, ACCENT_DARK = "#F2F7FC", "#8291A6", "#6FE7FF", "#123443"
GREEN, GOLD, PURPLE, FONT = "#67D9B0", "#D8B56A", "#AE9AFF", "Segoe UI"
CATEGORY_COLORS = {"body": ACCENT, "mind": PURPLE, "discipline": "#78AFFF", "recovery": GREEN,
                   "social": "#F0A6C4", "finance": GOLD, "environment": "#8CC5B8", "creativity": "#D9A0FF"}


class ScrollFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.window, width=event.width))
        self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-event.delta / 120), "units"))

    def fraction(self):
        return self.canvas.yview()[0]

    def restore(self, fraction):
        self.after_idle(lambda: self.canvas.yview_moveto(fraction))


class FeaturePagesMixin:
    def _feature_page(self, title: str, subtitle: str):
        scroll = ScrollFrame(self.content)
        scroll.pack(fill="both", expand=True)
        self.current_scroll = scroll
        header = tk.Frame(scroll.inner, bg=BG)
        header.pack(fill="x", padx=26, pady=(26, 16))
        self._label(header, title, 24, TEXT, bold=True, font_name="Segoe UI Variable Display").pack(anchor="w")
        self._label(header, subtitle, 10, MUTED).pack(anchor="w", pady=(4, 0))
        return scroll.inner

    def _show_goals(self) -> None:
        page = self._feature_page("МОИ ЦЕЛИ", "Личные задачи и один большой результат недели")
        boss = self._card(page, CARD_ELEVATED, GOLD)
        boss.pack(fill="x", padx=26, pady=6)
        self._label(boss, "НЕДЕЛЬНЫЙ БОСС  /  +100 XP", 10, GOLD, bold=True, bg=CARD_ELEVATED).pack(anchor="w", padx=18, pady=(15, 6))
        key = week_key(self.today)
        goal = tk.StringVar(value=self.state.weekly_goals.get(key, ""))
        entry = tk.Entry(boss, textvariable=goal, font=(FONT, 11), fg=TEXT, bg=BG, insertbackground=ACCENT, relief="flat", bd=9)
        entry.pack(fill="x", padx=18)
        row = tk.Frame(boss, bg=CARD_ELEVATED)
        row.pack(fill="x", padx=18, pady=10)
        def save_goal():
            text = goal.get().strip()
            if not text:
                return
            self.state.weekly_goals[key] = text
            self.store.save(self.state)
            self.show_page("goals")
        tk.Button(row, text="СОХРАНИТЬ ЦЕЛЬ", command=save_goal, bg=ACCENT_DARK, fg=ACCENT, relief="flat", padx=14, pady=9).pack(side="left")
        if key in self.state.weekly_done:
            self._label(row, "✓  ПОБЕДА ПОЛУЧЕНА", 9, GREEN, bold=True, bg=CARD_ELEVATED).pack(side="right")
        elif self.state.weekly_goals.get(key):
            def complete_boss():
                toggle_weekly_done(self.state, self.today)
                sync_achievements(self.state, self.today)
                self.store.save(self.state)
                messagebox.showinfo("СИСТЕМА", "Недельная цель завершена. +100 XP", parent=self)
                self.show_page("goals")
            tk.Button(row, text="ЗАВЕРШИТЬ НЕДЕЛЮ", command=complete_boss, bg=GREEN, fg=BG, relief="flat", padx=14, pady=9).pack(side="right")

        steps = self._card(page, CARD, BORDER)
        steps.pack(fill="x", padx=26, pady=(0, 12))
        self._label(steps, "ШАГИ БОССА", 10, ACCENT, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(13, 3))
        self._label(steps, "Разбей большую цель на маленькие проверяемые действия.", 8, MUTED, bg=CARD).pack(anchor="w", padx=16)
        step_value = tk.StringVar()
        step_row = tk.Frame(steps, bg=CARD)
        step_row.pack(fill="x", padx=16, pady=8)
        tk.Entry(step_row, textvariable=step_value, font=(FONT, 10), fg=TEXT, bg=BG, insertbackground=ACCENT, relief="flat", bd=7).pack(side="left", fill="x", expand=True)
        def add_step():
            value = step_value.get().strip()
            if value and len(self.state.weekly_tasks.get(key, [])) < 12:
                self.state.weekly_tasks.setdefault(key, []).append(value)
                self.store.save(self.state); self.show_page("goals")
        tk.Button(step_row, text="ДОБАВИТЬ", command=add_step, bg=ACCENT_DARK, fg=ACCENT, relief="flat", padx=10, pady=7).pack(side="left", padx=(8, 0))
        for index, step in enumerate(self.state.weekly_tasks.get(key, [])):
            marker = f"{key}:{index}"; done = marker in self.state.weekly_task_done
            line = tk.Frame(steps, bg=CARD)
            line.pack(fill="x", padx=16, pady=2)
            tk.Checkbutton(line, text=step, variable=tk.BooleanVar(value=done), fg=GREEN if done else TEXT, bg=CARD,
                           selectcolor=ACCENT_DARK, activebackground=CARD,
                           command=lambda i=index: (toggle_weekly_task(self.state, self.today, i), self.store.save(self.state), self.show_page("goals"))).pack(side="left")

        create = self._card(page, CARD, BORDER)
        create.pack(fill="x", padx=26, pady=12)
        self._label(create, "НОВОЕ ЛИЧНОЕ ЗАДАНИЕ", 11, ACCENT, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 8))
        title = tk.StringVar()
        description = tk.StringVar()
        xp = tk.IntVar(value=20)
        category = tk.StringVar(value="ДИСЦИПЛИНА")
        for label, variable in (("Название", title), ("Конкретный критерий завершения", description)):
            self._label(create, label, 8, MUTED, bg=CARD).pack(anchor="w", padx=16)
            tk.Entry(create, textvariable=variable, font=(FONT, 10), fg=TEXT, bg=BG, insertbackground=ACCENT, relief="flat", bd=8).pack(fill="x", padx=16, pady=(2, 7))
        options = tk.Frame(create, bg=CARD)
        options.pack(fill="x", padx=16, pady=(0, 8))
        category_menu = tk.OptionMenu(options, category, *CATEGORY_LABELS.values())
        category_menu.configure(fg=ACCENT, bg=ACCENT_DARK, activeforeground=TEXT, activebackground=ACCENT_DARK, relief="flat", bd=0, padx=10, pady=7)
        category_menu["menu"].configure(fg=TEXT, bg=CARD_ELEVATED, activebackground=ACCENT_DARK)
        category_menu.pack(side="left")
        tk.Spinbox(options, from_=5, to=100, increment=5, textvariable=xp, width=5, fg=TEXT, bg=BG, relief="flat").pack(side="left", padx=12)
        self._label(options, "XP за выполнение · по расписанию дней ниже", 8, MUTED, bg=CARD).pack(side="left")
        weekdays = []
        days = tk.Frame(create, bg=CARD)
        days.pack(fill="x", padx=16, pady=6)
        for index, name in enumerate(("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"), 1):
            value = tk.BooleanVar(value=True)
            weekdays.append(value)
            tk.Checkbutton(days, text=name, variable=value, fg=TEXT, bg=CARD, selectcolor=ACCENT_DARK, activebackground=CARD).pack(side="left")
        def add_task():
            if not title.get().strip() or not description.get().strip() or not any(v.get() for v in weekdays):
                messagebox.showwarning("СИСТЕМА", "Заполни название, критерий и выбери хотя бы один день.", parent=self)
                return
            cat = next(key for key, value in CATEGORY_LABELS.items() if value == category.get())
            task = CustomTask(f"custom:{uuid.uuid4().hex[:12]}", title.get().strip(), description.get().strip(),
                              cat, xp.get(), tuple(i for i, value in enumerate(weekdays, 1) if value.get()))
            self.state.custom_tasks.append(task)
            self.store.save(self.state)
            self.show_page("goals")
        tk.Button(create, text="ДОБАВИТЬ В МОЮ СИСТЕМУ", command=add_task, bg=ACCENT, fg=BG, relief="flat", padx=14, pady=10).pack(anchor="w", padx=16, pady=10)

        arcs = self._card(page, CARD_ELEVATED, PURPLE)
        arcs.pack(fill="x", padx=26, pady=(0, 12))
        self._label(arcs, "АРКИ РАЗВИТИЯ", 11, PURPLE, bold=True, bg=CARD_ELEVATED).pack(anchor="w", padx=16, pady=(14, 3))
        self._label(arcs, "Длинный путь в одном направлении. Прогресс начисляется за реальные выполненные действия.", 8, MUTED, bg=CARD_ELEVATED).pack(anchor="w", padx=16)
        arc_title, arc_target, arc_category = tk.StringVar(), tk.IntVar(value=12), tk.StringVar(value="ТЕЛО")
        arc_row = tk.Frame(arcs, bg=CARD_ELEVATED); arc_row.pack(fill="x", padx=16, pady=9)
        tk.Entry(arc_row, textvariable=arc_title, font=(FONT, 10), fg=TEXT, bg=BG, insertbackground=ACCENT, relief="flat", bd=7).pack(side="left", fill="x", expand=True)
        tk.OptionMenu(arc_row, arc_category, *CATEGORY_LABELS.values()).pack(side="left", padx=6)
        tk.Spinbox(arc_row, from_=3, to=200, increment=1, textvariable=arc_target, width=4, fg=TEXT, bg=BG, relief="flat").pack(side="left")
        def add_arc():
            title = arc_title.get().strip()
            if title and len(self.state.arcs) < 6:
                category = next(key for key, value in CATEGORY_LABELS.items() if value == arc_category.get())
                self.state.arcs.append(DevelopmentArc(f"arc:{uuid.uuid4().hex[:12]}", title, category, max(3, min(200, arc_target.get()))))
                self.store.save(self.state); self.show_page("goals")
        tk.Button(arcs, text="НАЧАТЬ АРКУ", command=add_arc, bg=PURPLE, fg=BG, relief="flat", padx=12, pady=8).pack(anchor="w", padx=16, pady=(0, 9))
        for arc in self.state.arcs:
            progress = arc_progress(self.state, arc)
            line = tk.Frame(arcs, bg=CARD_ELEVATED); line.pack(fill="x", padx=16, pady=4)
            self._label(line, f"{arc.title} · {CATEGORY_LABELS[arc.category]}", 9, TEXT, bold=True, bg=CARD_ELEVATED).pack(side="left")
            self._label(line, f"{progress} / {arc.target}", 9, PURPLE, bold=True, bg=CARD_ELEVATED).pack(side="right")

        tasks = list(custom_due(self.state, self.today))
        self._label(page, f"ЛИЧНЫЕ ЗАДАНИЯ НА СЕГОДНЯ  /  {len(tasks)}", 11, TEXT, bold=True).pack(anchor="w", padx=26, pady=(12, 5))
        for task in self.state.custom_tasks:
            card = self._card(page, CARD, BORDER)
            card.pack(fill="x", padx=26, pady=5)
            done = task.id in self.state.history.get(self.today.isoformat(), set())
            due = self.today.isoweekday() in task.weekdays
            self._label(card, f"{CATEGORY_LABELS[task.category]}  ·  +{task.xp} XP  ·  {', '.join(('ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС')[d-1] for d in task.weekdays)}", 8, CATEGORY_COLORS[task.category], bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(12, 3))
            self._label(card, task.title, 14, TEXT, bold=True, bg=CARD).pack(anchor="w", padx=16)
            self._label(card, task.description, 9, MUTED, bg=CARD, wraplength=650, justify="left").pack(anchor="w", padx=16, pady=4)
            actions = tk.Frame(card, bg=CARD)
            actions.pack(fill="x", padx=16, pady=(5, 12))
            if due:
                def toggle_custom(task=task):
                    toggle_quest(self.state, task.as_quest(), self.today)
                    self.store.save(self.state)
                    self.show_page("goals")
                tk.Button(actions, text="✓ ГОТОВО" if done else "ВЫПОЛНИТЬ", command=toggle_custom, bg=ACCENT if done else ACCENT_DARK, fg=BG if done else ACCENT, relief="flat", padx=12, pady=8).pack(side="left")
            def delete_task(task=task):
                if messagebox.askyesno("СИСТЕМА", "Удалить личное задание? История выполнений сохранится.", parent=self):
                    self.state.custom_tasks.remove(task)
                    self.store.save(self.state)
                    self.show_page("goals")
            tk.Button(actions, text="УДАЛИТЬ", command=delete_task, bg=CARD, fg=MUTED, relief="flat", padx=12).pack(side="right")

    def _show_journal(self) -> None:
        page = self._feature_page("ДНЕВНИК РЕЗУЛЬТАТОВ", "Заметки и фото хранятся локально рядом с прогрессом")
        completed = sorted(self.state.history.get(self.today.isoformat(), set()))
        if not completed:
            self._label(page, "Сначала выполни любое задание — затем здесь появится запись.", 11, MUTED).pack(padx=26, pady=20)
        quests = all_quests(self.state)
        for qid in reversed(completed):
            quest = quests.get(qid)
            if not quest:
                continue
            entry = self.state.journal.get(self.today.isoformat(), {}).get(qid, JournalEntry())
            card = self._card(page, CARD, BORDER)
            card.pack(fill="x", padx=26, pady=5)
            self._label(card, quest.title, 13, TEXT, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(13, 4))
            self._label(card, entry.note or "Запись пока не добавлена", 9, MUTED, bg=CARD, wraplength=650, justify="left").pack(anchor="w", padx=16)
            if entry.photo:
                self._label(card, f"Фото: {Path(entry.photo).name}", 8, GREEN, bg=CARD).pack(anchor="w", padx=16, pady=3)
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=16, pady=10)
            tk.Button(row, text="ЗАПИСАТЬ РЕЗУЛЬТАТ", command=lambda q=qid: self._edit_journal(q), bg=ACCENT_DARK, fg=ACCENT, relief="flat", padx=12, pady=8).pack(side="left")
            tk.Button(row, text="ДОБАВИТЬ ФОТО", command=lambda q=qid: self._attach_photo(q), bg=CARD_ELEVATED, fg=TEXT, relief="flat", padx=12, pady=8).pack(side="left", padx=8)
        self._show_history(page)

    def _journal_entry(self, qid: str) -> JournalEntry:
        return self.state.journal.get(self.today.isoformat(), {}).get(qid, JournalEntry())

    def _save_journal(self, qid: str, entry: JournalEntry) -> None:
        self.state.journal.setdefault(self.today.isoformat(), {})[qid] = entry
        sync_achievements(self.state, self.today)
        self.store.save(self.state)
        self.show_page("journal")

    def _edit_journal(self, qid: str) -> None:
        old = self._journal_entry(qid)
        note = simpledialog.askstring("Результат", "Что именно получилось? Запиши измеримый результат:", initialvalue=old.note, parent=self)
        if note is not None and note.strip():
            self._save_journal(qid, JournalEntry(note.strip(), old.photo))

    def _attach_photo(self, qid: str) -> None:
        source = filedialog.askopenfilename(parent=self, filetypes=(("Изображения", "*.jpg *.jpeg *.png *.webp"),))
        if not source:
            return
        folder = self.store.data_dir / "journal"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{self.today.isoformat()}-{uuid.uuid4().hex[:8]}{Path(source).suffix.lower()}"
        shutil.copy2(source, target)
        old = self._journal_entry(qid)
        self._save_journal(qid, JournalEntry(old.note, str(target)))

    def _show_history(self, page) -> None:
        self._label(page, "ИСТОРИЯ ВОСХОЖДЕНИЯ", 12, TEXT, bold=True).pack(anchor="w", padx=26, pady=(22, 8))
        quests = all_quests(self.state)
        for day in sorted(self.state.history, reverse=True)[:30]:
            ids = self.state.history[day]
            titles = ", ".join(quests[qid].title for qid in sorted(ids) if qid in quests)
            card = self._card(page, CARD, BORDER)
            card.pack(fill="x", padx=26, pady=3)
            self._label(card, f"{day}  /  {len(ids)} действий", 9, ACCENT, bold=True, bg=CARD).pack(anchor="w", padx=14, pady=(10, 3))
            self._label(card, titles or "Планируемый день восстановления", 8, MUTED, bg=CARD, wraplength=700, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

    def _show_chains(self) -> None:
        page = self._feature_page("ЦЕПОЧКИ ЗАДАНИЙ", "Выполняй направление несколько дней подряд и получи бонус один раз")
        for chain in CHAINS:
            value = chain_progress(self.state, chain, self.today)
            done = chain.id in self.state.completed_chains
            card = self._card(page, CARD, GREEN if done else BORDER)
            card.pack(fill="x", padx=26, pady=6)
            self._label(card, f"{CATEGORY_LABELS[chain.category]}  /  +{chain.reward} XP", 8, CATEGORY_COLORS[chain.category], bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 4))
            self._label(card, chain.title, 15, TEXT, bold=True, bg=CARD).pack(anchor="w", padx=16)
            self._progress_bar(card, value, chain.days, color=GREEN if done else ACCENT).pack(fill="x", padx=16, pady=10)
            self._label(card, "ЦЕПОЧКА ЗАВЕРШЕНА" if done else f"{value} / {chain.days} дней", 9, GREEN if done else MUTED, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(0, 13))

    def _show_settings(self) -> None:
        page = self._feature_page("НАСТРОЙКИ СИСТЕМЫ", "Нагрузка, восстановление, напоминания, копии и приватность")
        difficulty = self._card(page, CARD, BORDER)
        difficulty.pack(fill="x", padx=26, pady=6)
        self._label(difficulty, "АДАПТИВНАЯ СЛОЖНОСТЬ", 11, ACCENT, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 4))
        self._label(difficulty, "Лёгкая: 75% цели и 80% XP · Стандарт · Вызов: 125% цели и XP", 9, MUTED, bg=CARD).pack(anchor="w", padx=16)
        row = tk.Frame(difficulty, bg=CARD)
        row.pack(anchor="w", padx=16, pady=12)
        for key, title in (("light", "ЛЁГКИЙ ДЕНЬ"), ("standard", "СТАНДАРТ"), ("challenge", "ВЫЗОВ")):
            def set_difficulty(key=key):
                self.state.difficulty = key
                self.store.save(self.state)
                self.show_page("settings")
            tk.Button(row, text=("✓ " if self.state.difficulty == key else "") + title, command=set_difficulty,
                      bg=ACCENT if self.state.difficulty == key else ACCENT_DARK, fg=BG if self.state.difficulty == key else ACCENT,
                      relief="flat", padx=12, pady=9).pack(side="left", padx=(0, 7))
        recovery = self._card(page, CARD, BORDER)
        recovery.pack(fill="x", padx=26, pady=6)
        self._label(recovery, "ПЛАНИРУЕМЫЙ ДЕНЬ ВОССТАНОВЛЕНИЯ", 11, GREEN, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 3))
        self._label(recovery, "Серия не обрывается, но день не считается безупречным.", 9, MUTED, bg=CARD).pack(anchor="w", padx=16)
        def toggle_rest():
            key = self.today.isoformat()
            if key in self.state.rest_days:
                self.state.rest_days.remove(key)
            else:
                self.state.rest_days.add(key)
            self.store.save(self.state)
            self.show_page("settings")
        tk.Button(recovery, text="ОТМЕНИТЬ ОТДЫХ" if self.today.isoformat() in self.state.rest_days else "СЕГОДНЯ — ДЕНЬ ОТДЫХА",
                  command=toggle_rest, bg=ACCENT_DARK, fg=GREEN, relief="flat", padx=12, pady=9).pack(anchor="w", padx=16, pady=12)

        reminders = self._card(page, CARD, BORDER)
        reminders.pack(fill="x", padx=26, pady=6)
        self._label(reminders, "НАПОМИНАНИЯ", 11, GOLD, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 4))
        self._label(reminders, "Windows: пока приложение открыто · Android: системное уведомление", 9, MUTED, bg=CARD).pack(anchor="w", padx=16)
        enabled = tk.BooleanVar(value=self.state.reminder_enabled)
        minute = tk.StringVar(value=f"{self.state.reminder_minute // 60:02d}:{self.state.reminder_minute % 60:02d}")
        row = tk.Frame(reminders, bg=CARD)
        row.pack(anchor="w", padx=16, pady=10)
        tk.Checkbutton(row, text="Напоминать", variable=enabled, fg=TEXT, bg=CARD, selectcolor=ACCENT_DARK).pack(side="left")
        tk.Entry(row, textvariable=minute, width=7, fg=TEXT, bg=BG, relief="flat").pack(side="left", padx=12)
        def save_reminder():
            try:
                hour, mins = map(int, minute.get().split(":"))
                if not (0 <= hour < 24 and 0 <= mins < 60):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("СИСТЕМА", "Введите время в формате ЧЧ:ММ", parent=self)
                return
            self.state.reminder_enabled = enabled.get()
            self.state.reminder_minute = hour * 60 + mins
            self.store.save(self.state)
            self.show_page("settings")
        tk.Button(row, text="СОХРАНИТЬ", command=save_reminder, bg=ACCENT_DARK, fg=ACCENT, relief="flat", padx=12, pady=7).pack(side="left")

        security = self._card(page, CARD, BORDER)
        security.pack(fill="x", padx=26, pady=6)
        self._label(security, "ПРИВАТНОСТЬ И РЕЗЕРВНЫЕ КОПИИ", 11, PURPLE, bold=True, bg=CARD).pack(anchor="w", padx=16, pady=(14, 8))
        row = tk.Frame(security, bg=CARD)
        row.pack(anchor="w", padx=16, pady=(0, 14))
        for text, command in (("УСТАНОВИТЬ PIN", self._set_pin), ("ЭКСПОРТ", self._export_backup), ("ИМПОРТ", self._import_backup)):
            tk.Button(row, text=text, command=command, bg=ACCENT_DARK, fg=ACCENT, relief="flat", padx=12, pady=9).pack(side="left", padx=(0, 7))
        self._label(page, weekly_recommendation(self.state, self.today), 10, GOLD, wraplength=700, justify="left").pack(anchor="w", padx=26, pady=20)

    def _set_pin(self) -> None:
        pin = simpledialog.askstring("PIN", "Введи новый PIN (4–8 цифр). Пустой ответ снимает защиту:", show="*", parent=self)
        if pin is None:
            return
        if pin and (not pin.isdigit() or not 4 <= len(pin) <= 8):
            messagebox.showwarning("СИСТЕМА", "PIN должен содержать 4–8 цифр.", parent=self)
            return
        self.state.pin_hash = hashlib.sha256(pin.encode()).hexdigest() if pin else ""
        self.store.save(self.state)

    def _verify_pin(self) -> bool:
        if not self.state.pin_hash:
            return True
        for _ in range(3):
            pin = simpledialog.askstring("СИСТЕМА ЗАБЛОКИРОВАНА", "Введи PIN:", show="*", parent=self)
            if pin is not None and hashlib.sha256(pin.encode()).hexdigest() == self.state.pin_hash:
                return True
        return False

    def _export_backup(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", initialfile=f"sistema-backup-{date.today()}.json")
        if path:
            Path(path).write_text(json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("СИСТЕМА", "Резервная копия сохранена.", parent=self)

    def _import_backup(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=(("Sistema backup", "*.json"),))
        if not path or not messagebox.askyesno("СИСТЕМА", "Заменить текущий прогресс данными из копии?", parent=self):
            return
        try:
            imported = PlayerState.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("СИСТЕМА", f"Не удалось прочитать копию: {error}", parent=self)
            return
        self.state = imported
        self.store.save(self.state)
        self.show_page("today")
