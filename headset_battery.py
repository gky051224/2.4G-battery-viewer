"""Bluetooth headset readings with connection checks to reject cached batteries."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class HeadsetReading:
    name: str
    level: Optional[int] = None
    connected: bool = False
    detail: str = ""


def clean_name(name: str) -> str:
    return re.sub(r"\s+(?:Hands-Free\s+AG|HandsFree\s+AG|免提\s*AG)$", "", name,
                  flags=re.IGNORECASE).strip()


def address_from_instance(instance_id: str) -> str:
    # HFP PnP child nodes end with '&<12 hexadecimal digits>_C...'.
    match = re.search(r"&([0-9A-F]{12})_", instance_id.upper())
    return match.group(1) if match else ""


def combine(nodes, states: dict[str, bool], selected_name: str = "") -> list[HeadsetReading]:
    found = {}
    for node in nodes:
        if not node.is_handsfree:
            continue
        name = clean_name(node.name)
        if selected_name and name.casefold() != selected_name.casefold():
            continue
        address = address_from_instance(node.instance_id)
        key = address or name.casefold()
        connected = states.get(address, False)
        level = node.battery
        if not connected:
            result = HeadsetReading(name, detail="蓝牙未连接，请打开耳机并连接电脑")
        elif not node.has_property or level is None or not 1 <= level <= 100:
            result = HeadsetReading(name, connected=True,
                                    detail="已连接，Windows 尚未收到有效电量")
        else:
            result = HeadsetReading(name, level, True, "来自 Windows 蓝牙电量上报")
        # Prefer a valid connected value over a duplicate profile without data.
        previous = found.get(key)
        if previous is None or (previous.level is None and result.level is not None):
            found[key] = result
    readings = sorted(found.values(), key=lambda r: (not r.connected, r.name.casefold()))
    if not readings:
        return [HeadsetReading(selected_name or "蓝牙耳机", detail="未找到耳机，请先在 Windows 中配对连接")]
    return readings


def read_headsets(selected_name: str = "") -> list[HeadsetReading]:
    import bt_battery as bt
    import win_bluetooth
    try:
        return combine(bt.displayable_devices(), win_bluetooth.connection_states(), selected_name)
    except OSError as exc:
        return [HeadsetReading(selected_name or "蓝牙耳机", detail=f"无法读取蓝牙状态：{exc}")]


def selected_headsets(selection: str = "auto") -> list[HeadsetReading]:
    if selection not in ("auto", "all"):
        return read_headsets(selection)
    readings = read_headsets()
    if selection == "all":
        return readings
    connected = [r for r in readings if r.connected]
    return connected or [HeadsetReading("蓝牙耳机", detail="没有已连接的蓝牙耳机，请打开耳机并连接电脑")]
