from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))
from sistema.game import QUESTS  # noqa: E402


def main() -> None:
    output = ROOT / "web/src/game/quests.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "id": quest.id,
            "title": quest.title,
            "category": quest.category,
            "description": quest.description,
            "xp": quest.xp,
            "minLevel": quest.min_level,
            "base": quest.base,
            "step": quest.step,
            "maxTarget": quest.max_target,
        }
        for quest in QUESTS
    ]
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(data)} quests: {output}")


if __name__ == "__main__":
    main()
