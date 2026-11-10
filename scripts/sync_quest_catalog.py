from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))
from sistema.game import QUESTS  # noqa: E402


def text(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    assert len(QUESTS) == 248
    lines = [
        "package ru.sistema.player",
        "",
        "/** Generated from desktop/sistema/game.py by scripts/sync_quest_catalog.py. */",
        "object QuestCatalog {",
        "    val items = listOf(",
    ]
    for quest in QUESTS:
        lines.append(
            "        Quest(" + ", ".join((
                text(quest.id), text(quest.title), text(quest.category),
                text(quest.description), str(quest.xp), str(quest.min_level),
                str(quest.base), str(quest.step), str(quest.max_target),
            )) + "),"
        )
    lines.extend(("    )", "}", ""))
    output = ROOT / "app/src/main/java/ru/sistema/player/QuestCatalog.kt"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {len(QUESTS)} quests: {output}")


if __name__ == "__main__":
    main()
