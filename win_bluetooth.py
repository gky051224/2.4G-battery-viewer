"""Read the Windows classic Bluetooth connection state without discovery/pairing."""
from __future__ import annotations

import ctypes
from ctypes import wintypes


class DeviceSearch(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD),
                ("fReturnAuthenticated", wintypes.BOOL),
                ("fReturnRemembered", wintypes.BOOL),
                ("fReturnUnknown", wintypes.BOOL),
                ("fReturnConnected", wintypes.BOOL),
                ("fIssueInquiry", wintypes.BOOL),
                ("cTimeoutMultiplier", ctypes.c_ubyte), ("hRadio", wintypes.HANDLE)]


class DeviceInfo(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("Address", ctypes.c_ulonglong),
                ("ulClassofDevice", wintypes.ULONG), ("fConnected", wintypes.BOOL),
                ("fRemembered", wintypes.BOOL), ("fAuthenticated", wintypes.BOOL),
                ("stLastSeen", wintypes.WORD * 8), ("stLastUsed", wintypes.WORD * 8),
                ("szName", wintypes.WCHAR * 248)]


def connection_states() -> dict[str, bool]:
    """Map classic Bluetooth addresses to current connection flags.

    fIssueInquiry stays false: no radio scan, connection attempt or audio-mode change.
    A cached battery property is not evidence that the headset is connected.
    """
    api = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
    api.BluetoothFindFirstDevice.argtypes = [ctypes.POINTER(DeviceSearch), ctypes.POINTER(DeviceInfo)]
    api.BluetoothFindFirstDevice.restype = wintypes.HANDLE
    api.BluetoothFindNextDevice.argtypes = [wintypes.HANDLE, ctypes.POINTER(DeviceInfo)]
    api.BluetoothFindNextDevice.restype = wintypes.BOOL
    api.BluetoothFindDeviceClose.argtypes = [wintypes.HANDLE]
    api.BluetoothFindDeviceClose.restype = wintypes.BOOL
    search = DeviceSearch()
    search.dwSize = ctypes.sizeof(search)
    search.fReturnAuthenticated = search.fReturnRemembered = search.fReturnConnected = True
    info = DeviceInfo()
    info.dwSize = ctypes.sizeof(info)
    handle = api.BluetoothFindFirstDevice(ctypes.byref(search), ctypes.byref(info))
    if not handle:
        error = ctypes.get_last_error()
        if error == 259:  # ERROR_NO_MORE_ITEMS (including a disabled radio)
            return {}
        raise ctypes.WinError(error)
    states = {}
    try:
        while True:
            address = f"{info.Address:012X}"
            states[address] = states.get(address, False) or bool(info.fConnected)
            info = DeviceInfo()
            info.dwSize = ctypes.sizeof(info)
            if not api.BluetoothFindNextDevice(handle, ctypes.byref(info)):
                error = ctypes.get_last_error()
                if error != 259:
                    raise ctypes.WinError(error)
                break
    finally:
        api.BluetoothFindDeviceClose(handle)
    return states
