# 蓝牙耳机电量

## 已验证

2026-10-19 的首次实现读取 HFP PnP 节点的 **100%**，这只能证明读取了系统属性，
不能证明真实电量准确或刚刚更新。用户反馈长时间使用后仍显示满电。

进一步直接查询 **EDIFIER W820NB 双金标版**，连续收到 `BB 02 D0 5E 22 04`，
校验通过，电量字节 `5E` = **94%**；同一时刻 Windows 属性仍为 **100%**。
差异证明此系统属性不适合作为本型号的精确当前电量，不能只凭连接状态判断数据新鲜。
目前已改用耳机直接回复。

## 读取过程

1. 通过 `BluetoothFindFirstDevice` / `BluetoothFindNextDevice` 读取经典蓝牙设备的
   `BLUETOOTH_DEVICE_INFO.fConnected`，不发起设备扫描。
2. 按蓝牙设备地址将 HFP 子节点和连接状态对应，避免同名设备或其他配对记录误关联。
   地址只用于内存关联，不写入配置或日志。
3. 对已验证的 EDIFIER 型号，连接已公布的 RFCOMM 服务
   `edf00000-edfe-dfed-fedf-edfedfedfedf`，只发送 `AA 01 D0 21 94`（电量 GET）。
   读取完整回复，检查 `BB 02 D0`、长度、16 位校验和及 0..100 范围。
   不发送任何设置、断开、关机、配对或固件指令。
4. EDIFIER 查询失败则显示 `--`，系统值仅在说明中作为未确认参考值，不回退成有效百分比。
5. 其他未适配的耳机继续读取 HFP 属性，但明确标注为“Windows 系统参考值，更新时间无法确认”。
   对 HFP 的 0 保守显示未知；直接协议回复的 0 在校验有效时可作为真实百分比显示。

设置中的耳机选择保存设备名称，保存在已忽略的 `tray_config.json`。
读取不会断开或重新配对耳机，也不会打开麦克风或改变音频模式。
刷新遵循面板设置；每次 EDIFIER 读取会获取新回复。面板/托盘用命名互斥锁串行查询，
避免 RFCOMM 通道竞争；连接、等待锁和收包共享 3 秒期限。
本次没有验证 BLE-only 耳机、左右耳分离电量或充电盒电量。

## 验证

- 自动化测试覆盖断开后的缓存电量、错误地址、指定设备选择、重复节点、缺失和非法属性。
- 新增测试覆盖真实 94% 报文、错误校验、错误命令、截断、越界及直查失败不显示缓存满电。
- 面板实机显示 EDIFIER 94%；构造断开状态后，原百分比被清除。
- 双图标托盘连续启动/退出验证，实机读取到 EDIFIER 94%；并发查询也能串行获得 94%。
- GM3323D 的读取仍返回 80%。

## Windows API 依据

- [BluetoothFindFirstDevice](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/nf-bluetoothapis-bluetoothfindfirstdevice)
- [BLUETOOTH_DEVICE_INFO](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/ns-bluetoothapis-bluetooth_device_info_struct)
- [BLUETOOTH_DEVICE_SEARCH_PARAMS](https://learn.microsoft.com/en-us/windows/win32/api/bluetoothapis/ns-bluetoothapis-bluetooth_device_search_params)
- [SOCKADDR_BTH](https://learn.microsoft.com/windows/win32/api/ws2bth/ns-ws2bth-sockaddr_bth)
- [Edifier 电量指令协议分析](https://github.com/GlitchPunkWTF/edifier-proto)：命令 D0、回复格式及校验算法；使用独立实现，不包含其程序。
