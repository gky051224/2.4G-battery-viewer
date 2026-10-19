"""Shared semantic colors for the panel and tray; standard library only."""
from __future__ import annotations

SKINS = {
    "graphite": dict(name="石墨黑", bg="#17191D", card="#22252B", border="#343A44",
                     fg="#F4F6FA", muted="#ADB6C4", accent="#58D5B2", on_accent="#102820",
                     good="#58D5B2", warning="#F0C369", danger="#FF8790", track="#373D47",
                     icon_bg="#2C353C", hover="#303640", dark=True),
    "cloud": dict(name="云雾白", bg="#F1F4F7", card="#FFFFFF", border="#D5DDE7",
                  fg="#202B3C", muted="#596A80", accent="#137C65", on_accent="#FFFFFF",
                  good="#137C65", warning="#986000", danger="#BB344D", track="#E0E7EE",
                  icon_bg="#E9F3EF", hover="#E5EBF2", dark=False),
    "midnight": dict(name="午夜蓝", bg="#0C1526", card="#142238", border="#293D59",
                     fg="#EFF5FF", muted="#A7B8D0", accent="#83B5FF", on_accent="#0B203B",
                     good="#70DFB7", warning="#F2C674", danger="#FF8E9C", track="#2B3C56",
                     icon_bg="#1F3553", hover="#263A56", dark=True),
    "forest": dict(name="森林绿", bg="#111E1B", card="#1C2D27", border="#365044",
                   fg="#F1F8F3", muted="#B0C6B9", accent="#94D6AC", on_accent="#122C20",
                   good="#94D6AC", warning="#EFCB83", danger="#FF9299", track="#354C40",
                   icon_bg="#2B4437", hover="#2D4539", dark=True),
}


def get_skin(key: str) -> dict:
    return SKINS.get(key, SKINS["graphite"])


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def level_color(level, skin: dict) -> str:
    if level is None:
        return skin["muted"]
    return skin["good"] if level >= 60 else skin["warning"] if level >= 30 else skin["danger"]
