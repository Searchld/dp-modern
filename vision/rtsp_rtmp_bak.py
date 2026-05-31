import logging
import time

import cv2


logger = logging.getLogger(__name__)


def _gst_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _source_push_pipeline(fps=10, width=None, height=None):
    fps = max(1, int(round(float(fps or 10))))
    caps = ""
    if width and height:
        caps = f"video/x-raw,format=BGR,width={int(width)},height={int(height)},framerate={fps}/1 ! "
    return (
        "appsrc is-live=true block=true format=time do-timestamp=true ! "
        f"{caps}"
        "queue max-size-buffers=4 leaky=downstream ! "
        "videoconvert ! video/x-raw,format=I420 ! "
    )


def _h264_encoder_pipelines(fps=10, bitrate_kbps=2000):
    fps = max(1, int(round(float(fps or 10))))
    bitrate_kbps = max(256, int(bitrate_kbps or 2000))
    bitrate_bps = bitrate_kbps * 1000
    key_interval = fps * 2
    return [
        f"nvh264enc preset=low-latency-hq rc-mode=1 bitrate={bitrate_kbps} zerolatency=true bframes=0 ! h264parse config-interval=1 ! ",
        f"x264enc tune=zerolatency speed-preset=ultrafast bitrate={bitrate_kbps} key-int-max={key_interval} bframes=0 byte-stream=true ! h264parse config-interval=1 ! ",
        f"openh264enc bitrate={bitrate_bps} ! h264parse config-interval=1 ! ",
        f"avenc_h264 bitrate={bitrate_bps} ! h264parse config-interval=1 ! ",
    ]


def create_push_pipelines(uri, fps=10, bitrate_kbps=2000, width=None, height=None):
    """Create candidate GStreamer appsrc pipelines for already-annotated BGR frames."""
    source = _source_push_pipeline(fps, width, height)
    encoders = _h264_encoder_pipelines(fps, bitrate_kbps)
    quoted_uri = _gst_quote(uri)
    lower_uri = uri.lower()
    if lower_uri.startswith("rtsp://"):
        return [
            source + encoder + f"rtph264pay pt=96 config-interval=1 ! rtspclientsink location={quoted_uri} protocols=tcp"
            for encoder in encoders
        ]
    if lower_uri.startswith("rtmp://"):
        sinks = [
            f"flvmux streamable=true ! rtmp2sink location={quoted_uri}",
            f"flvmux streamable=true ! rtmpsink location={quoted_uri}",
        ]
        return [source + encoder + sink for encoder in encoders for sink in sinks]
    raise ValueError(f"Unsupported push uri: {uri}")


def create_push_pipeline(uri, fps=10, bitrate_kbps=2000, width=None, height=None):
    return create_push_pipelines(uri, fps, bitrate_kbps, width, height)[0]


class GStreamerFramePusher:
    """Push processed frames with OpenCV VideoWriter and GStreamer."""

    def __init__(self, uri, fps=10, bitrate_kbps=2000, retry_interval=3, logger_obj=None):
        self.uri = uri
        self.fps = max(1, float(fps or 10))
        self.bitrate_kbps = int(bitrate_kbps or 2000)
        self.retry_interval = max(0.5, float(retry_interval or 3))
        self.logger = logger_obj or logger
        self.writer = None
        self.size = None
        self.last_open_attempt = 0.0

    def _open(self, frame):
        now = time.time()
        if now - self.last_open_attempt < self.retry_interval:
            return False
        self.last_open_attempt = now

        height, width = frame.shape[:2]
        self.size = (width, height)
        for pipeline in create_push_pipelines(self.uri, self.fps, self.bitrate_kbps, width, height):
            self.logger.info("准备打开推流 uri=%s pipeline=%s", self.uri, pipeline)
            self.writer = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, 0, self.fps, self.size, True)
            if self.writer.isOpened():
                self.logger.info("推流已打开 uri=%s size=%sx%s fps=%s", self.uri, width, height, self.fps)
                return True
            self.release()

        self.logger.warning("推流打开失败 uri=%s；RTMP 需要 rtmp2sink 或 rtmpsink，RTSP 需要 rtspclientsink", self.uri)
        return False

    def write(self, frame):
        if frame is None or not self.uri:
            return False

        if not frame.flags["C_CONTIGUOUS"]:
            frame = frame.copy()

        height, width = frame.shape[:2]
        size = (width, height)
        if self.writer is None or not self.writer.isOpened() or self.size != size:
            self.release()
            if not self._open(frame):
                return False

        try:
            result = self.writer.write(frame)
            if result is False or self.writer is None or not self.writer.isOpened():
                self.logger.warning("推流写帧后状态异常，准备重连 uri=%s", self.uri)
                self.release()
                return False
            return True
        except Exception as exc:
            self.logger.warning("推流写帧失败 uri=%s error=%s", self.uri, exc)
            self.release()
            return False

    def release(self):
        if self.writer is not None:
            try:
                self.writer.release()
            except Exception:
                pass
        self.writer = None
