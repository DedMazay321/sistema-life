from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "test-data-ui"
if DATA.exists():
    shutil.rmtree(DATA)
SHOTS = ROOT / "screenshots"
SHOTS.mkdir(exist_ok=True)
os.environ["SISTEMA_DATA_DIR"] = str(DATA)

from PIL import ImageGrab
from sistema.game import get_daily_quests
from sistema.storage import PlayerStore
from sistema.ui import SistemaApp
from tkinter import messagebox


def capture(app: SistemaApp, name: str) -> None:
    app.update_idletasks()
    app.update()
    app.lift()
    app.attributes("-topmost", True)
    app.update()
    time.sleep(0.35)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    width, height = app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + width, y + height)).save(SHOTS / name)


messagebox.showinfo = lambda *args, **kwargs: None
app = SistemaApp()
app.update()
assert len(get_daily_quests(app.state, app.today)) == 6
capture(app, "today.png")
quest = get_daily_quests(app.state, app.today)[0]
app._toggle(quest)
assert app.state.total_xp > 0
app.show_page("achievements")
app.update()
assert len(app.state.unlocked_achievements) >= 1
capture(app, "achievements.png")
app.show_page("library")
app.library_query.set("тренировка")
app.update()
app.show_page("stats")
app.update()
app.show_page("goals")
app.update()
capture(app, "goals.png")
app.show_page("journal")
app.update()
app.show_page("chains")
app.update()
app.show_page("settings")
app.update()
capture(app, "settings.png")
app._on_close()
loaded = PlayerStore().load()
assert loaded.total_xp > 0
print("UI_SMOKE_OK: navigation, quest completion, filtering, achievements, persistence, screenshots")
