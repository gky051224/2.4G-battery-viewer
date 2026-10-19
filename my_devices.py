# -*- coding: utf-8 -*-
"""我的设备电量 —— GM3323D 与蓝牙耳机简洁面板

用法：
    python my_devices.py            打开界面（默认自动刷新）
    python my_devices.py --once     命令行读一次就退出

显示 GM3323D 和蓝牙耳机电量，可自动刷新。
"""

from __future__ import annotations

import argparse
import traceback
from dataclasses import dataclass
from typing import Optional

import gm3323d_proto as gm
import headset_battery as hb
import tray_common as tc
import win_link


# ==========================================================================
# 读取层
# ==========================================================================
@dataclass
class Reading:
    title: str
    subtitle: str
    level: Optional[int] = None
    status: str = ""
    detail: str = ""
    error: str = ""
    extra: str = ""

    @property
    def ok(self) -> bool:
        return self.level is not None


def read_gm3323d() -> Reading:
    result = gm.read_battery()
    return Reading(
        title="GM3323D 鼠标", subtitle="2.4G 无线连接",
        level=result.level,
        status=("电量充足" if result.level >= 60 else
                "电量中等" if result.level >= 30 else "电量偏低") if result.ok else "",
        detail=result.detail if result.ok else "",
        error=result.detail if not result.ok else "",
        extra="鼠标每档上报 10%，显示值不是逐 1% 测量。" if result.ok else "",
    )


def read_all() -> list[Reading]:
    selection = tc.load_config()["headset"]
    # Check headset connection after waiting for the mouse, so its state is fresh.
    mouse = read_gm3323d()
    headsets = [Reading(
        title=result.name, subtitle="蓝牙耳机 · 已连接" if result.connected else "蓝牙耳机 · 未连接",
        level=result.level, detail=result.detail if result.level is not None else "",
        error=result.detail if result.level is None else "",
        extra=("每次刷新直接向耳机查询，已校验回复。" if result.direct else
               "系统参考值，可能存在延迟；不代表刚刚从耳机读到。") if result.level is not None else "",
    ) for result in hb.selected_headsets(selection)]
    return [mouse, *headsets]


# ==========================================================================
# 命令行模式
# ==========================================================================
def cli_once() -> None:
    for r in read_all():
        if r.ok:
            print(f"{r.title}: {r.level}%   {r.detail}")
            if r.extra:
                print(f"    {r.extra}")
        else:
            print(f"{r.title}: 读取失败 —— {r.error}")


# ==========================================================================
# 界面
# ==========================================================================
def build_ui():
    try:
        import ctypes
        ctypes.WinDLL("user32").SetProcessDPIAware()
    except (OSError, AttributeError):
        pass
    from battery_ui import BatteryWindow
    return BatteryWindow(read_all).root


def main() -> None:
    parser = argparse.ArgumentParser(description="我的设备电量")
    parser.add_argument("--once", action="store_true", help="命令行读一次就退出")
    parser.add_argument("--install-links", action="store_true",
                        help="在桌面重建软连接（项目文件夹 + 启动脚本）")
    parser.add_argument("--autostart", choices=["on", "off", "status"],
                        help="开机自启：on 打开 / off 关闭 / status 查看")
    args = parser.parse_args()

    if args.install_links:
        r = tc.install_desktop_links()
        print("桌面链接：")
        print(f"  项目文件夹 {tc.DESKTOP_LINK_NAME} -> "
              f"{win_link.KIND_LABEL.get(r['folder'], r['folder'] or '创建失败')}")
        for name, kind in r["links"].items():
            print(f"  {name} -> {win_link.KIND_LABEL.get(kind, kind)}")
        for msg in r["errors"]:
            print("  注意：", msg)
        return

    if args.autostart:
        if args.autostart == "status":
            st = tc.autostart_status()
            print("开机自启：", "已启用" if st["enabled"] else "未启用")
            print("  方式：", st["method"])
            print("  快捷方式：", st["shortcut"],
                  "(存在)" if st["shortcut_exists"] else "(不存在)")
            print("  任务管理器状态：", st["taskmanager_state"])
            print("  目标：", st["target"])
            print("  旧注册表项：", "还在" if st["legacy_registry"] else "已清理")
        else:
            ok = tc.set_autostart(args.autostart == "on")
            print("已" + ("加入" if args.autostart == "on" else "取消") + "开机自启",
                  "" if ok else "（失败）")
        return

    if args.once:
        cli_once()
        return
    try:
        root = build_ui()
    except Exception:
        print("无法启动图形界面，改用命令行模式：")
        traceback.print_exc()
        cli_once()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
