# 蓝牙耳机电量

## 已验证

2026-10-19 在 Windows 上检测到已连接的 **EDIFIER W820NB 双金标版**，
HFP PnP 节点电量属性为 **100%**，面板与托盘均成功显示。
同机另一副未连接的配对耳机仍有历史电量属性；新增连接检查后不会显示该缓存值。

## 读取过程

1. 复用 `bt_battery.py` 读取 HFP 节点的
   `{104EA319-6EE2-4701-BD47-8DDBF425BBE5}, 2` 属性。
2. 通过 `BluetoothFindFirstDevice` / `BluetoothFindNextDevice` 读取经典蓝牙设备的
   `BLUETOOTH_DEVICE_INFO.fConnected`，不发起设备扫描。
3. 按蓝牙设备地址将 HFP 子节点和连接状态对应，避免同名设备或其他配对记录误关联。
   地址只用于内存关联，不写入配置或日志。
4. 仅在连接有效、属性类型为 BYTE 且电量在 1..100 时显示百分比。
   0 可能是尚未上报的占位值，因此保守显示未知，不把它标成已耗尽。
5. 断开、未知连接状态、无属性或非法值显示 `--`；不会把过期读数当成当前电量。

设置中的耳机选择保存设备名称，保存在已忽略的 `tray_config.json`。
读取不会重新连接、配对耳机，也不会打开麦克风或改变音频模式。
刷新遵循面板设置；显示的是 Windows 最近收到的上报值，无法强制耳机立即更新。
本次没有验证 BLE-only 耳机、左右耳分离电量或充电盒电量。

## 验证

- 自动化测试覆盖断开后的缓存电量、错误地址、指定设备选择、重复节点、缺失和非法属性。
- 面板实机显示 EDIFIER 100%；构造断开状态后，原百分比被清除。
- 双图标托盘连续启动/退出验证，实机读取到 EDIFIER 100%。
- GM3323D 的读取仍返回 80%。

## Windows API 依据

- [BluetoothFindFirstDevice](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/nf-bluetoothapis-bluetoothfindfirstdevice)
- [BLUETOOTH_DEVICE_INFO](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/ns-bluetoothapis-bluetooth_device_info_struct)
- [BLUETOOTH_DEVICE_SEARCH_PARAMS](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/ns-bluetoothapis-bluetooth_device_search_params)
