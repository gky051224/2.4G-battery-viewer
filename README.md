# GM3323D 电量查看器

基于 [yszyszysz233/2.4G-battery-viewer](https://github.com/yszyszysz233/2.4G-battery-viewer)
制作的 **戴记严选 GM3323D 专用分支**。简洁面板与托盘现在显示 GM3323D；
原项目的 ATK / DARKRIM 等调试读取代码保留在 `app.py` / `battery.py` 中。

已在真实 GM3323D 接收器（`1D57:FA60`）上读到 **80%**。
鼠标按 **10% 一档**上报，不是逐 1% 的精确测量。
只监听电量报文，不修改 DPI、灯效、宏或固件。运行无需安装厂商软件。

## 使用

需要 Windows 10/11、Python 3.10+（包含 tkinter）；无需安装第三方 Python 包。

1. 下载本分支的全部文件并解压到固定文件夹。
2. 插入 GM3323D 的 USB 接收器，打开鼠标并移动一下。
3. 双击 `GM3323D.bat` 打开面板。
4. 点击面板里的“启动托盘程序”，右下角就会显示电量数字。

也可以在项目文件夹打开终端运行：

```bat
python my_devices.py
```

只读一次：

```bat
python my_devices.py --once
```

若系统使用 Python Launcher，可将 `python` 换成 `py -3`。

## 托盘与设置

- 左键托盘图标：刷新电量；右键：打开面板。
- 默认每 60 秒刷新，可在面板调整为 30 秒至 30 分钟。
- 关闭面板后，已经启动的托盘继续运行；在面板点击“退出托盘程序”可结束后台进程。
- 开机自启默认关闭；需要时在面板勾选，启动项名称为“GM3323D 电量托盘”。
- “重建桌面链接”会创建项目目录与两个启动入口的链接。
- 主动修改设置时保存 `tray_config.json`；电量报文不写日志。
- 开机自启与桌面入口依赖项目目录，请先把项目放到固定位置。

直接启动或退出托盘：

```bat
pythonw tray_app.py
python tray_app.py --quit
```

## 读不到时

- 显示找不到接收器：重新插拔 USB 接收器，确认是 GM3323D、`1D57:FA60`。
- 显示超时或未连接：打开鼠标，移动唤醒，再点击刷新；每次读取最多等待 5 秒。
- 无数据时显示 `--`，不会把旧数据或不认识的字节当成当前电量。
- 当前只验证 2.4G 连接下的电量；有线电量和独立充电状态尚未实机验证。
- 不保证其他型号、相同芯片或不同接收器版本兼容。

## 开发与验证

```bat
python -m unittest discover -s tests -v
python my_devices.py --once
python tray_app.py --debug
```

协议和验证范围见 [GM3323D_PROTOCOL.md](docs/GM3323D_PROTOCOL.md)。
原作者说明见 [UPSTREAM_README.md](docs/UPSTREAM_README.md)；原 `PROMPT.md` 保留作为开发参考。