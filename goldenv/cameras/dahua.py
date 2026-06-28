from __future__ import annotations

import sys
import threading
from ctypes import (
    byref,
    c_buffer,
    c_char_p,
    c_double,
    c_int,
    c_ulonglong,
    c_void_p,
    cast,
    memmove,
    pointer,
    POINTER,
)
from pathlib import Path
from queue import Empty, Queue

import numpy as np

from goldenv.cameras.base import CameraFrame, utc_now
from goldenv.cameras.dahua_sdk_loader import _load_mvsdk, is_dahua_sdk_available
from goldenv.config import CameraConfig
from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime


def _ensure_runtime() -> None:
    prepare_dahua_runtime()


class DahuaCamera:
    """大华 GigE/USB 工业相机 Adapter（MVSDK / MV Viewer SDK）。"""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera_id = config.id
        self._bundle = None
        self._dev = None
        self._stream = None
        self._connected = False
        self._frame_queue: Queue[np.ndarray] = Queue(maxsize=2)
        self._grabbing = False
        self._lock = threading.Lock()
        self._callback = None

    def connect(self) -> None:
        _ensure_runtime()
        self._bundle = _load_mvsdk()
        if self._bundle is None:
            raise RuntimeError(
                "未找到大华 MVSDK。请确认安装程序已完成大华运行时配置，或设置 DAHUA_SDK_PATH"
            )
        mv = self._bundle["MVSDK"]
        camera_cnt, camera_list = self._enum_cameras(mv)
        if not camera_cnt:
            raise RuntimeError("未发现大华工业相机")

        camera = self._select_camera(mv, camera_list, camera_cnt)
        ret = camera.connect(camera, c_int(mv.GENICAM_ECameraAccessPermission.accessPermissionControl))
        if ret != 0:
            raise RuntimeError(f"连接大华相机失败 (ret={ret})")

        self._dev = camera
        self._set_exposure_gain(mv, camera)
        self._stream = self._create_stream(mv, camera)
        self._start_grabbing(mv)
        self._connected = True

    def _enum_cameras(self, mv):
        system = pointer(mv.GENICAM_System())
        n_ret = mv.GENICAM_createSystem(byref(mv.GENICAM_SystemInfo()), byref(system))
        if n_ret != 0:
            raise RuntimeError("GENICAM_createSystem 失败")
        camera_cnt = c_int(0)
        camera_list = mv.GENICAM_Camera()
        n_ret = system.contents.discovery(system, byref(camera_list), byref(camera_cnt), c_int(mv.GENICAM_EProtocolType.typeAll))
        if n_ret != 0 or camera_cnt.value == 0:
            raise RuntimeError("枚举大华相机失败")
        return camera_cnt.value, camera_list

    def _select_camera(self, mv, camera_list, camera_cnt):
        target_ip = self.config.ip
        target_name = self.config.user_defined_name
        for index in range(camera_cnt):
            camera = camera_list[index]
            if target_ip:
                ip = camera.getIpAddress(camera)
                if isinstance(ip, bytes):
                    ip = ip.decode("utf-8", errors="ignore")
                if str(ip) == target_ip:
                    return camera
            if target_name:
                name = camera.getName(camera)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="ignore")
                if str(name) == target_name:
                    return camera
        return camera_list[0]

    def _set_exposure_gain(self, mv, camera) -> None:
        if self.config.exposure_us is None and self.config.gain is None:
            return
        acq_info = mv.GENICAM_AcquisitionControlInfo()
        acq_info.pCamera = pointer(camera)
        acq_ctrl = pointer(mv.GENICAM_AcquisitionControl())
        if mv.GENICAM_createAcquisitionControl(pointer(acq_info), byref(acq_ctrl)) != 0:
            return
        try:
            if self.config.exposure_us is not None:
                exp_node = acq_ctrl.contents.exposureTime(acq_ctrl)
                exp_node.setValue(acq_ctrl, c_double(float(self.config.exposure_us)))
                exp_node.release(exp_node)
            if self.config.gain is not None:
                gain_node = acq_ctrl.contents.gainRaw(acq_ctrl)
                gain_node.setValue(acq_ctrl, c_double(float(self.config.gain)))
                gain_node.release(gain_node)
        finally:
            acq_ctrl.contents.release(acq_ctrl)

    def _create_stream(self, mv, camera):
        stream_info = mv.GENICAM_StreamSourceInfo()
        stream_info.channelId = 0
        stream_info.pCamera = pointer(camera)
        stream = pointer(mv.GENICAM_StreamSource())
        n_ret = mv.GENICAM_createStreamSource(pointer(stream_info), byref(stream))
        if n_ret != 0:
            raise RuntimeError("创建 StreamSource 失败")
        return stream

    def _start_grabbing(self, mv) -> None:
        ic = self._bundle["ImageConvert"]

        def on_frame(frame, _user_info):
            if not self._grabbing:
                return
            try:
                if frame.contents.valid(frame) != 0:
                    frame.contents.release(frame)
                    return
                params = ic.IMGCNV_SOpenParam()
                params.dataSize = frame.contents.getImageSize(frame)
                params.height = frame.contents.getImageHeight(frame)
                params.width = frame.contents.getImageWidth(frame)
                params.paddingX = frame.contents.getImagePaddingX(frame)
                params.paddingY = frame.contents.getImagePaddingY(frame)
                params.pixelForamt = frame.contents.getImagePixelFormat(frame)
                image_buff = frame.contents.getImage(frame)
                user_buff = c_buffer(b"\0", params.dataSize)
                memmove(user_buff, c_char_p(image_buff), params.dataSize)
                frame.contents.release(frame)

                if params.pixelForamt == ic.EPixelType.gvspPixelMono8:
                    gray = np.frombuffer(bytearray(user_buff), dtype=np.uint8).reshape(
                        params.height, params.width
                    )
                    import cv2

                    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                else:
                    rgb_size = c_int()
                    rgb_buff = c_buffer(b"\0", params.height * params.width * 3)
                    ic.IMGCNV_ConvertToBGR24(
                        cast(user_buff, c_void_p),
                        byref(params),
                        cast(rgb_buff, c_void_p),
                        byref(rgb_size),
                    )
                    bgr = np.frombuffer(bytearray(rgb_buff), dtype=np.uint8).reshape(
                        params.height, params.width, 3
                    )
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except Empty:
                        pass
                self._frame_queue.put(bgr.copy())
            except Exception:
                return

        self._callback = mv.callbackFuncEx(on_frame)
        n_ret = self._stream.contents.attachGrabbingEx(
            self._stream, self._callback, b"goldenv"
        )
        if n_ret != 0:
            raise RuntimeError("注册拉流回调失败")
        self._grabbing = True
        n_ret = self._stream.contents.startGrabbing(self._stream, c_ulonglong(0), c_int(mv.GENICAM_EGrabStrategy.grabStrartegySequential))
        if n_ret != 0:
            raise RuntimeError("开始拉流失败")

    def disconnect(self) -> None:
        self._grabbing = False
        if self._stream and self._bundle:
            try:
                self._stream.contents.stopGrabbing(self._stream)
                self._stream.contents.release(self._stream)
            except Exception:
                pass
        if self._dev:
            try:
                self._dev.disconnect(self._dev)
            except Exception:
                pass
        self._stream = None
        self._dev = None
        self._connected = False

    def capture(self) -> CameraFrame:
        if not self._connected:
            raise RuntimeError(f"相机 {self.camera_id} 未连接")
        try:
            image = self._frame_queue.get(timeout=2.0)
        except Empty as exc:
            raise RuntimeError("大华相机采图超时") from exc
        return CameraFrame(camera_id=self.camera_id, captured_at=utc_now(), image=image)
