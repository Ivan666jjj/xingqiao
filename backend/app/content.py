import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Content:
    scenes: dict
    emotion_items: dict
    tasks: dict

    @classmethod
    def load(cls, data_dir: str | Path) -> "Content":
        base = Path(data_dir)

        def read(name):
            with open(base / name, encoding="utf-8") as fh:
                return json.load(fh)

        return cls(
            scenes={s["id"]: s for s in read("scenes.json")},
            emotion_items={i["id"]: i for i in read("emotion_items.json")},
            tasks={t["id"]: t for t in read("tasks.json")},
        )

    def public_scenes(self):
        return [
            {
                "id": s["id"],
                "title": s["title"],
                "desc": s["desc"],
                "skillTag": s.get("skillTag"),
                "level": s.get("level", 1),
                "turns": len(s["turns"]),
            }
            for s in self.scenes.values()
        ]