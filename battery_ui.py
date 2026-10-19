"""Compact native battery panel with live skins. No webview or extra packages."""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

import skins
import tray_common as tc
import app_identity

FONT = "Microsoft YaHei UI"


def rounded(canvas, box, radius, **options):
    x1, y1, x2, y2 = box
    r = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    return canvas.create_polygon(
        x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
        x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        smooth=True, splinesteps=24, **options)


class DeviceCard(tk.Canvas):
    def __init__(self, parent, kind, skin):
        super().__init__(parent, height=166, highlightthickness=0, bd=0,
                         background=skin["bg"], takefocus=False)
        self.kind, self.skin, self.reading = kind, skin, None
        self.title_font = tkfont.Font(family=FONT, size=12, weight="bold")
        self.hint_font = tkfont.Font(family=FONT, size=9)
        self.bind("<Configure>", lambda _event: self.draw())

    def set_skin(self, skin):
        self.skin = skin
        self.configure(background=skin["bg"])
        self.draw()

    def update_reading(self, reading):
        self.reading = reading
        self.draw()

    def draw(self):
        self.delete("all")
        s, r = self.skin, self.reading
        w, h = max(200, self.winfo_width()), 166
        rounded(self, (1, 1, w-1, h-1), 18, fill=s["card"], outline=s["border"], width=1)
        rounded(self, (24, 27, 76, 79), 14, fill=s["icon_bg"], outline="")
        ink = s["accent"]
        if self.kind == "mouse":
            rounded(self, (39, 37, 61, 69), 10, fill="", outline=ink, width=2)
            self.create_line(50, 39, 50, 48, fill=ink, width=2)
        else:
            self.create_arc(37, 37, 63, 65, start=0, extent=180, style="arc", outline=ink, width=2)
            rounded(self, (35, 50, 42, 65), 3, fill=ink, outline="")
            rounded(self, (58, 50, 65, 65), 3, fill=ink, outline="")
        title = r.title if r else ("GM3323D 鼠标" if self.kind == "mouse" else "蓝牙耳机")
        # Leave a fixed area for the value so long device names never overlap it.
        display_title = title
        while len(display_title) > 1 and self.title_font.measure(display_title) > w - 270:
            display_title = display_title[:-2] + "…"
        self.create_text(94, 40, anchor="w", text=display_title, fill=s["fg"], font=self.title_font)
        subtitle = r.subtitle if r else "正在等待设备…"
        self.create_text(94, 67, anchor="w", text=subtitle, fill=s["muted"], font=(FONT, 9))
        level = r.level if r else None
        color = skins.level_color(level, s)
        self.create_text(w-57, 58, anchor="e", text=str(level) if level is not None else "—",
                         fill=s["fg"] if level is not None else s["muted"], font=("Segoe UI", 38, "bold"))
        if level is not None:
            self.create_text(w-29, 66, anchor="e", text="%", fill=s["muted"], font=("Segoe UI", 12))
        if r and r.error:
            hint = r.error
            # Keep the actionable reason visible; long diagnostics live in Details.
            if "参考值" in hint:
                hint = hint.split("；")[0]
            if "超时" in hint:
                hint = "暂未收到回复，点“立即刷新”重试"
            if len(hint) > 43:
                hint = hint[:42] + "…"
        elif r:
            if self.kind == "mouse":
                hint = "接收器原始读数 · 设备以 10% 档位上报"
            elif "本次" in r.detail or "直读" in r.extra:
                hint = "耳机直接回复 · 整数百分比"
            else:
                hint = "Windows 系统参考值 · 更新时间未确认"
        else:
            hint = "读取完成后会在这里显示连接与电量来源"
        while len(hint) > 1 and self.hint_font.measure(hint) > w - 76:
            hint = hint[:-2] + "…"
        self.create_oval(27, 101, 33, 107, fill=color, outline="")
        self.create_text(43, 104, anchor="w", text=hint, fill=s["muted"], font=self.hint_font)
        x1, x2, y = 26, w-26, 136
        rounded(self, (x1, y, x2, y+7), 3.5, fill=s["track"], outline="")
        if level is not None and level > 0:
            end = x1 + (x2-x1) * level / 100
            rounded(self, (x1, y, end, y+7), 3.5, fill=color, outline="")


class BatteryWindow:
    def __init__(self, reader):
        self.reader, self.cfg = reader, tc.load_config()
        self.skin = skins.get_skin(self.cfg["theme"])
        app_identity.set_process_identity()
        self.root = tk.Tk()
        app_identity.set_window_icon(self.root)
        self.root.battery_app = self
        self.root.title(tc.UI_TITLE)
        self.root.geometry("800x620")
        self.root.minsize(720, 590)
        self.root.protocol("WM_DELETE_WINDOW", self.close_panel)
        self.root.bind("<F5>", lambda _event: self.refresh())
        self.root.bind("<Control-comma>", lambda _event: self.open_settings())
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.events = queue.Queue()
        self.busy = self.pending = self.starting_tray = False
        self.after_refresh = None
        self.settings = None
        self.last_updated = ""
        self.readings = []
        self.cards = []
        self._build()
        self.apply_skin()
        self.reschedule()
        self.root.after(100, self.refresh)
        self.root.after(150, self.pump)
        self.root.after(0, self.start_tray)

    def _build(self):
        self.outer = ttk.Frame(self.root, style="Page.TFrame", padding=(28, 24, 28, 20))
        self.outer.pack(fill="both", expand=True)
        header = ttk.Frame(self.outer, style="Page.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="外设电量", style="Title.TLabel").pack(side="left")
        self.theme_name = tk.StringVar(value=self.skin["name"])
        selector = ttk.Combobox(header, textvariable=self.theme_name, state="readonly", width=9,
                                values=[s["name"] for s in skins.SKINS.values()], style="Skin.TCombobox")
        selector.pack(side="right", pady=(3, 0))
        selector.bind("<<ComboboxSelected>>", lambda _event: self.change_skin(
            next(k for k, s in skins.SKINS.items() if s["name"] == self.theme_name.get())))
        self.subtitle = ttk.Label(self.outer, style="Muted.TLabel")
        self.subtitle.pack(anchor="w", pady=(6, 24))
        footer = ttk.Frame(self.outer, style="Page.TFrame")
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        self.status = ttk.Label(footer, text="正在连接设备…", style="Muted.TLabel")
        self.status.pack(side="left")
        ttk.Button(footer, text="退出", command=self.quit, style="Quiet.TButton").pack(side="right")
        ttk.Button(footer, text="收起", command=self.hide_to_tray, style="Quiet.TButton").pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="设置", command=self.open_settings, style="Quiet.TButton").pack(side="right", padx=(0, 8))
        self.refresh_button = ttk.Button(self.outer, text="立即刷新", command=self.refresh, style="Accent.TButton")
        self.refresh_button.pack(side="bottom", anchor="e", pady=(0, 7))
        self.body = ttk.Frame(self.outer, style="Page.TFrame")
        self.body.pack(fill="both", expand=True)
        self.ensure_cards(2)

    def ensure_cards(self, count):
        if len(self.cards) == count:
            return
        for card in self.cards:
            card.destroy()
        self.cards = []
        for index in range(count):
            card = DeviceCard(self.body, "mouse" if index == 0 else "headset", self.skin)
            card.pack(fill="x", pady=(0, 12))
            self.cards.append(card)
        if count > 2:
            height = min(self.root.winfo_screenheight()-80, 276 + count*178)
            self.root.geometry(f"{max(800, self.root.winfo_width())}x{height}")

    def apply_skin(self):
        self.skin = s = skins.get_skin(self.cfg["theme"])
        self.root.configure(background=s["bg"])
        self.style.configure("Page.TFrame", background=s["bg"])
        self.style.configure("TLabel", background=s["bg"], foreground=s["fg"], font=(FONT, 10))
        self.style.configure("Title.TLabel", font=(FONT, 21, "bold"))
        self.style.configure("Section.TLabel", font=(FONT, 11, "bold"))
        self.style.configure("Muted.TLabel", foreground=s["muted"], font=(FONT, 9))
        self.style.configure("Quiet.TButton", background=s["card"], foreground=s["fg"],
                             bordercolor=s["border"], lightcolor=s["card"], darkcolor=s["card"],
                             relief="flat", padding=(14, 9), width=6, font=(FONT, 10), focuscolor=s["accent"])
        self.style.map("Quiet.TButton", background=[("active", s["hover"]), ("pressed", s["track"])])
        self.style.configure("Accent.TButton", background=s["accent"], foreground=s["on_accent"],
                             bordercolor=s["accent"], lightcolor=s["accent"], darkcolor=s["accent"],
                             relief="flat", padding=(20, 10), font=(FONT, 10, "bold"), focuscolor=s["fg"])
        self.style.map("Accent.TButton", background=[("disabled", s["track"]), ("active", s["good"])],
                       foreground=[("disabled", s["muted"])])
        self.style.configure("TCheckbutton", background=s["bg"], foreground=s["fg"], font=(FONT, 10))
        self.style.map("TCheckbutton", background=[("active", s["bg"])])
        self.style.configure("TCombobox", fieldbackground=s["card"], background=s["card"],
                             foreground=s["fg"], arrowcolor=s["muted"], bordercolor=s["border"],
                             lightcolor=s["card"], darkcolor=s["card"], padding=7, font=(FONT, 10))
        self.style.map("TCombobox", fieldbackground=[("readonly", s["card"])],
                       foreground=[("readonly", s["fg"])], selectbackground=[("readonly", s["card"])],
                       selectforeground=[("readonly", s["fg"])])
        self.root.option_add("*TCombobox*Listbox.background", s["card"])
        self.root.option_add("*TCombobox*Listbox.foreground", s["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", s["hover"])
        self.theme_name.set(s["name"])
        for card in self.cards:
            card.set_skin(s)
        if self.settings and self.settings.winfo_exists():
            self.settings.configure(background=s["bg"])
        self._set_titlebar()
        self.update_subtitle()

    def _set_titlebar(self, window=None):
        try:
            import ctypes
            from ctypes import wintypes
            api = ctypes.WinDLL("user32")
            api.GetParent.argtypes, api.GetParent.restype = [wintypes.HWND], wintypes.HWND
            window = window or self.root
            window.update_idletasks()
            hwnd = api.GetParent(window.winfo_id()) or window.winfo_id()
            dwm = ctypes.WinDLL("dwmapi")
            dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
            dark = ctypes.c_int(int(self.skin["dark"]))
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
            for attribute, token in ((35, "bg"), (36, "fg")):
                r, g, b = skins.rgb(self.skin[token])
                color = wintypes.DWORD(r | g << 8 | b << 16)
                dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color))
        except (OSError, AttributeError):
            pass

    def save(self, **changes):
        self.cfg = tc.load_config()
        self.cfg.update(changes)
        tc.save_config(self.cfg)
        tc.post_to_tray(tc.MSG_RELOAD)

    def change_skin(self, key):
        self.save(theme=key)
        self.apply_skin()
        if self.settings and self.settings.winfo_exists():
            self.build_settings()

    def update_subtitle(self):
        interval = dict(tc.INTERVAL_CHOICES).get(self.cfg["interval"], "1 分钟")
        suffix = f"每 {interval}自动刷新" if self.cfg["auto_refresh"] else "自动刷新已暂停"
        self.subtitle.configure(text="鼠标与蓝牙耳机  ·  " + suffix)

    def refresh(self):
        if self.busy:
            self.pending = True
            return
        self.busy = True
        self.refresh_button.configure(text="正在读取…", state="disabled")
        self.status.configure(text="正在读取设备电量…")

        def work():
            try:
                self.events.put(("readings", self.reader()))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def pump(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "readings":
                    self.readings = data
                    self.ensure_cards(len(data))
                    for card, reading in zip(self.cards, data):
                        card.update_reading(reading)
                    self.last_updated = time.strftime("%H:%M:%S")
                    self.status.configure(text=f"更新于 {self.last_updated}")
                    self.finish_refresh()
                elif kind == "error":
                    # Clear visible results rather than leaving a success from an old read.
                    from my_devices import Reading
                    self.readings = [Reading("GM3323D 鼠标", "暂不可用", error=data),
                                     Reading("蓝牙耳机", "暂不可用", error=data)]
                    self.ensure_cards(2)
                    for card, reading in zip(self.cards, self.readings):
                        card.update_reading(reading)
                    self.status.configure(text="读取失败，可点击刷新重试")
                    self.finish_refresh()
                elif kind == "tray":
                    ok, hide = data
                    self.starting_tray = False
                    if ok and hide:
                        self.root.withdraw()
                    self.status.configure(text=("已收起到系统托盘" if hide else "托盘已启动")
                                          if ok else "托盘未能启动，请点击“收起”重试")
                    if self.settings and self.settings.winfo_exists():
                        self.build_settings()
                elif kind == "choices":
                    self.headset_names = data
                    if self.settings and self.settings.winfo_exists():
                        self.build_settings()
                elif kind == "links":
                    self.status.configure(text="桌面入口已更新" if not data.get("errors") else "部分桌面入口未创建")
                    if data.get("errors"):
                        messagebox.showwarning("桌面入口", "\n".join(data["errors"]), parent=self.root)
        except queue.Empty:
            pass
        self.root.after(150 if self.busy or self.starting_tray else 650, self.pump)

    def finish_refresh(self):
        self.busy = False
        self.refresh_button.configure(text="立即刷新", state="normal")
        if self.pending:
            self.pending = False
            self.root.after(0, self.refresh)

    def reschedule(self):
        if self.after_refresh is not None:
            self.root.after_cancel(self.after_refresh)
            self.after_refresh = None
        if self.cfg["auto_refresh"]:
            self.after_refresh = self.root.after(self.cfg["interval"]*1000, self.tick)
        self.update_subtitle()

    def tick(self):
        self.refresh()
        self.reschedule()

    def start_tray(self, hide=False):
        if self.starting_tray:
            return
        if tc.is_tray_running():
            if hide:
                self.root.withdraw()
            return
        self.starting_tray = True
        self.status.configure(text="正在启动托盘…")
        def work():
            try:
                ok = tc.start_tray_app()
            except Exception:
                ok = False
            self.events.put(("tray", (ok, hide)))
        threading.Thread(target=work, daemon=True).start()

    def hide_to_tray(self):
        self.start_tray(hide=True)

    def close_panel(self):
        if tc.is_tray_running():
            self.root.withdraw()
        else:
            self.root.destroy()

    def quit(self):
        tc.post_to_tray(tc.MSG_QUIT)
        self.root.destroy()

    def open_settings(self):
        if self.settings and self.settings.winfo_exists():
            self.settings.lift()
            return
        self.settings = tk.Toplevel(self.root)
        app_identity.set_window_icon(self.settings)
        self.settings.title("偏好设置")
        self.settings.transient(self.root)
        self.settings.resizable(False, False)
        self.settings.bind("<Escape>", lambda _event: self.settings.destroy())
        self.headset_names = []
        self.build_settings()
        # Only enumerate metadata here; never query Bluetooth on the UI thread.
        def work():
            import bt_battery as bt
            import headset_battery as hb
            try:
                names = sorted({hb.clean_name(d.name) for d in bt.displayable_devices() if d.is_handsfree})
            except OSError:
                names = []
            self.events.put(("choices", names))
        threading.Thread(target=work, daemon=True).start()

    def build_settings(self):
        win, s = self.settings, self.skin
        for child in win.winfo_children():
            child.destroy()
        win.configure(background=s["bg"])
        pane = ttk.Frame(win, style="Page.TFrame", padding=24)
        pane.pack(fill="both", expand=True)
        ttk.Label(pane, text="偏好设置", style="Section.TLabel").pack(anchor="w")
        ttk.Label(pane, text="外观即时生效，关闭窗口后仍会保留。", style="Muted.TLabel").pack(anchor="w", pady=(6, 18))
        themes = ttk.Frame(pane, style="Page.TFrame")
        themes.pack(fill="x")
        for index, (key, theme) in enumerate(skins.SKINS.items()):
            button = tk.Button(themes, text=theme["name"], width=9, pady=12, relief="flat", bd=0,
                               background=theme["card"], foreground=theme["fg"],
                               activebackground=theme["hover"], activeforeground=theme["fg"],
                               highlightthickness=2, highlightbackground=s["accent"] if key == self.cfg["theme"] else s["border"],
                               font=(FONT, 10), command=lambda k=key: self.change_skin(k), cursor="hand2")
            button.grid(row=0, column=index, padx=(0, 8 if index < 3 else 0))

        form = ttk.Frame(pane, style="Page.TFrame")
        form.pack(fill="x", pady=(22, 14))
        form.columnconfigure(1, weight=1)
        def choice(row, label, options, current, callback):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 20), pady=7)
            var = tk.StringVar(value=current)
            box = ttk.Combobox(form, textvariable=var, values=list(options), state="readonly", width=28)
            box.grid(row=row, column=1, sticky="ew", pady=7)
            box.bind("<<ComboboxSelected>>", lambda _event: callback(options[var.get()]))
        icon_styles = {"圆环进度": "ring", "数字百分比": "digits"}
        choice(0, "托盘图标", icon_styles, next(k for k,v in icon_styles.items() if v == self.cfg["icon_style"]),
               lambda value: self.save(icon_style=value))
        intervals = {label: sec for sec, label in tc.INTERVAL_CHOICES}
        def interval_changed(value):
            self.save(interval=value)
            self.reschedule()
        choice(1, "刷新间隔", intervals, dict(tc.INTERVAL_CHOICES)[self.cfg["interval"]], interval_changed)
        devices = {"自动选择已连接耳机": "auto", "全部已配对耳机": "all"}
        devices.update({name: name for name in self.headset_names})
        selected = self.cfg["headset"]
        if selected not in devices.values():
            devices[selected] = selected
        def device_changed(value):
            self.save(headset=value)
            self.refresh()
        choice(2, "蓝牙耳机", devices, next(k for k,v in devices.items() if v == selected), device_changed)
        auto = tk.BooleanVar(value=self.cfg["auto_refresh"])
        def on_auto():
            self.save(auto_refresh=auto.get())
            self.reschedule()
        ttk.Checkbutton(pane, text="自动刷新面板与托盘", variable=auto, command=on_auto).pack(anchor="w", pady=5)
        boot = tk.BooleanVar(value=tc.is_autostart_enabled())
        def on_boot():
            ok = tc.set_autostart(boot.get())
            self.save(autostart=tc.is_autostart_enabled())
            if not ok:
                messagebox.showwarning("开机自启", "无法更新启动入口，请稍后重试。", parent=win)
        ttk.Checkbutton(pane, text="开机启动电量托盘", variable=boot, command=on_boot).pack(anchor="w", pady=5)
        ttk.Label(pane, text="精度说明", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        ttk.Label(pane, text="显示原始整数百分比，不估算中间值。\n耳机可直读 1% 整数；鼠标接收器目前只上报 10% 档位。\n不保存电量历史。", style="Muted.TLabel").pack(anchor="w")
        actions = ttk.Frame(pane, style="Page.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="读取详情", command=self.show_details, style="Quiet.TButton").pack(side="left")
        ttk.Button(actions, text="桌面入口", command=self.install_links, style="Quiet.TButton").pack(side="left", padx=8)
        ttk.Button(actions, text="完成", command=win.destroy, style="Accent.TButton").pack(side="right")
        self._set_titlebar(win)

    def show_details(self):
        win = tk.Toplevel(self.root)
        app_identity.set_window_icon(win)
        win.title("电量读取详情")
        win.transient(self.root)
        text = tk.Text(win, width=72, height=20, wrap="word", borderwidth=0, padx=20, pady=20,
                       background=self.skin["card"], foreground=self.skin["fg"], font=(FONT, 10))
        text.pack(fill="both", expand=True)
        for reading in self.readings:
            value = f"{reading.level}%" if reading.ok else "未知"
            text.insert("end", f"{reading.title} · {value}\n{reading.subtitle}\n{reading.error or reading.detail}\n{reading.extra}\n\n")
        text.configure(state="disabled")
        win.bind("<Escape>", lambda _event: win.destroy())

    def install_links(self):
        def work():
            try:
                result = tc.install_desktop_links()
            except OSError as exc:
                result = {"errors": [str(exc)]}
            self.events.put(("links", result))
        threading.Thread(target=work, daemon=True).start()
