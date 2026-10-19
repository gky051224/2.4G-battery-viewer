"""Direct battery-only query for the tested EDIFIER W820NB 双金标版.

Uses the paired headset's advertised RFCOMM service, not its HFP battery cache.
Only sends command D0 (battery GET); there is no settings/firmware command API.
Protocol: https://github.com/GlitchPunkWTF/edifier-proto
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import re
import time
from typing import Optional

SUPPORTED_NAMES = {"EDIFIER W820NB 双金标版"}
SERVICE_UUID = "edf00000-edfe-dfed-fedf-edfedfedfedf"
BATTERY_QUERY = bytes.fromhex("AA 01 D0 21 94")


@dataclass(frozen=True)
class Reading:
    level: Optional[int] = None
    detail: str = ""
    raw: bytes = b""


def parse_battery_frame(frame: bytes) -> Optional[int]:
    if len(frame) != 6 or frame[:3] != bytes.fromhex("BB 02 D0"):
        return None
    checksum = (sum(frame[:-2]) + 0x2019) & 0xFFFF
    if int.from_bytes(frame[-2:], "big") != checksum or frame[3] > 100:
        return None
    return frame[3]


def find_battery_frame(data: bytes) -> Optional[Reading]:
    start = 0
    while True:
        index = data.find(bytes.fromhex("BB 02 D0"), start)
        if index < 0:
            return None
        frame = data[index:index + 6]
        level = parse_battery_frame(frame)
        if level is not None:
            return Reading(level, "来自耳机本次电量查询回复", frame)
        start = index + 1


def _exchange(address: str, timeout: float) -> Reading:
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", address):
        return Reading(detail="无法确定耳机地址")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    # Lazy imports keep protocol parsing testable without Windows.
    import ctypes
    import select
    import socket
    import struct
    import uuid

    try:
        ws = ctypes.WinDLL("ws2_32", use_last_error=True)
        ws.connect.argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
        ws.connect.restype = ctypes.c_int
        ws.WSAGetLastError.restype = ctypes.c_int
        # ws2bth.h uses pack(1): USHORT + BTH_ADDR + GUID + ULONG = 30 bytes.
        # A zero port asks Windows to resolve the advertised service's channel.
        target = (struct.pack("<HQ", 32, int(address, 16))
                  + uuid.UUID(SERVICE_UUID).bytes_le + struct.pack("<I", 0))
        deadline = time.monotonic() + timeout
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                           socket.BTPROTO_RFCOMM) as stream:
            stream.setblocking(False)
            target_buffer = ctypes.create_string_buffer(target)
            result = ws.connect(stream.fileno(), target_buffer, len(target))
            if result:
                error = ws.WSAGetLastError()
                if error not in (10035, 10036, 10037):
                    raise OSError(error, "耳机查询通道连接失败")
                _, writable, failed = select.select(
                    [], [stream], [stream], max(0, deadline - time.monotonic()))
                if not writable and not failed:
                    raise TimeoutError("耳机查询通道连接超时")
                error = stream.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if error:
                    raise OSError(error, "耳机查询通道连接失败")
            stream.settimeout(max(0.001, deadline - time.monotonic()))
            stream.sendall(BATTERY_QUERY)
            data = b""
            while time.monotonic() < deadline:
                stream.settimeout(max(0.001, deadline - time.monotonic()))
                chunk = stream.recv(256)
                if not chunk:
                    break
                data = (data + chunk)[-4096:]
                reading = find_battery_frame(data)
                if reading is not None:
                    return reading
        return Reading(detail="耳机没有回复有效电量")
    except OSError:
        raise


@contextmanager
def _query_lock(address: str, deadline: float):
    """Serialize panel/tray queries across processes; no battery cache on disk."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.ReleaseMutex.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateMutexW(None, False, "Local\\DeviceBattery_Edifier_" + address.upper())
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    try:
        result = kernel.WaitForSingleObject(handle, max(0, int((deadline - time.monotonic()) * 1000)))
        if result == 258:
            raise TimeoutError("另一个电量查询尚未完成")
        if result not in (0, 128):
            raise ctypes.WinError(ctypes.get_last_error())
        acquired = True
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def read_battery(address: str, timeout: float = 3.0) -> Reading:
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", address):
        return Reading(detail="无法确定耳机地址")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    deadline = time.monotonic() + timeout
    try:
        with _query_lock(address, deadline):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("耳机查询超时")
                try:
                    return _exchange(address, remaining)
                except OSError as exc:
                    # RFCOMM teardown can briefly keep the previous channel busy.
                    # Retry only establishing the connection, not other commands.
                    if exc.errno != 10048 or deadline - time.monotonic() < 0.15:
                        raise
                    time.sleep(0.1)
    except OSError as exc:
        return Reading(detail=f"耳机直读失败：{exc}")
