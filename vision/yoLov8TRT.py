import random
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
import pycuda.autoinit  # noqa: F401
import pycuda.driver as cuda
import tensorrt as trt

# 尝试导入 GPU 加速库
HAS_CUDA = False
try:
    import torch
    import torchvision.transforms.functional as F
    HAS_PYTORCH = True
    if torch.cuda.is_available():
        HAS_CUDA = True
except ImportError:
    HAS_PYTORCH = False

# 尝试导入 OpenCV-CUDA
HAS_CV2_CUDA = False
try:
    cv2.cuda.getCudaEnabledDeviceCount()
    HAS_CV2_CUDA = True
except (AttributeError, cv2.error):
    HAS_CV2_CUDA = False

from dect import Dect
from utils.logger_util import LoggerUtil

# 从 utils.tools 移动过来的函数
def plot_one_box(x, img, color=None, label=None, line_thickness=None):
    """
    description: Plots one bounding box on image img,
                 this function comes from YoLov5 project.
    param:
        x:      a box likes [x1,y1,x2,y2]
        img:    a opencv image object
        color:  color to draw rectangle, such as (0,255,0)
        label:  str
        line_thickness: int
    return:
        no return
    """
    tl = (
            line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    )  # line/font thickness
    image_h, image_w = img.shape[:2]
    x1 = max(0, min(int(x[0]), image_w - 1))
    y1 = max(0, min(int(x[1]), image_h - 1))
    x2 = max(0, min(int(x[2]), image_w - 1))
    y2 = max(0, min(int(x[3]), image_h - 1))
    c1, c2 = (x1, y1), (x2, y2)
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)  # font thickness
        font_scale = tl / 3
        t_size, baseline = cv2.getTextSize(label, 0, fontScale=font_scale, thickness=tf)
        pad = max(2, tl)
        label_w = t_size[0] + pad * 2
        label_h = t_size[1] + baseline + pad * 2
        label_x1 = min(max(c1[0], 0), max(0, image_w - label_w))
        label_x2 = min(image_w, label_x1 + label_w)
        if c1[1] - label_h >= 0:
            label_y1 = c1[1] - label_h
            label_y2 = c1[1]
            text_y = label_y2 - baseline - pad
        else:
            label_y1 = min(max(c1[1] + tl, 0), max(0, image_h - label_h))
            label_y2 = min(image_h, label_y1 + label_h)
            text_y = label_y1 + pad + t_size[1]

        cv2.rectangle(img, (label_x1, label_y1), (label_x2, label_y2), color, -1, cv2.LINE_AA)
        cv2.putText(
            img,
            label,
            (label_x1 + pad, text_y),
            0,
            font_scale,
            [225, 255, 255],
            thickness=tf,
            lineType=cv2.LINE_AA,
        )

logger = LoggerUtil.get_logger(__name__)

CONF_THRESH = 0.5
IOU_THRESHOLD = 0.4

# 各类别独立置信度阈值（顺序需与 categories 一一对应）。
conf_list = [0.8, 0.8, 0.8, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.8, 0.8, 0.8]
# 模型类别表（类别 id -> 业务标签）。
categories = [
    "car",
    "fullcar",
    "emptycar",
    "big",
    "person",
    "helmet",
    "safety_clothes",
    "water",
    "full",
    "fullcar1",
    "fullcar2",
    "fullcar3",
    "truck",
]
# 每个类别随机一个可视化颜色，便于画框区分。
globalColors = [[random.randint(0, 255) for _ in range(3)] for _ in categories]

# TensorRT 输出结构参数（与模型导出时保持一致）。
DET_NUM = 6
POSE_NUM = 17 * 3
SEG_NUM = 32
OBB_NUM = 1
num_values_per_detection = DET_NUM + POSE_NUM + SEG_NUM + OBB_NUM


@dataclass
class DetectionResult:
    """单帧推理结果对象。"""

    # 画框后的业务显示帧。
    annotated_frame: np.ndarray
    # 原始输入帧（不带画框）。
    raw_frame: np.ndarray
    # 本帧命中标签列表。
    labels: list
    # 各标签对应的检测框集合：{label: [bbox, ...]}。
    boxs: dict
    # 各标签对应置信度集合：{label: [score, ...]}。
    conf: dict
    # 单帧推理耗时（秒）。
    infer_cost: float


class YoLov8TRT(object):
    def __init__(self, engine_file_path, keys, sources, T, preprocess_mode="auto"):
        """
        初始化 YOLOv8 TensorRT 推理引擎
        
        Args:
            preprocess_mode: 预处理模式
                "auto": 自动选择最佳模式（优先用 GPU，没有就用优化 CPU）
                "cpu": 强制使用原始 CPU 预处理
                "cpu_optimized": 使用优化的 CPU 预处理（推荐）
                "torch": 使用 PyTorch GPU 预处理
                "opencv_cuda": 使用 OpenCV-CUDA 预处理
        """
        # 业务处理入口（推理后统一走 dect 规则）。
        self.business = Dect(keys, sources, T)
        # 兼容遗留状态位。
        self.warn = {}
        self.status = {}
        # 推理锁：单实例串行执行 TensorRT 上下文，避免并发冲突。
        self._infer_lock = threading.Lock()
        self._destroyed = False

        # 预处理模式配置
        self.preprocess_mode = self._select_preprocess_mode(preprocess_mode)
        self.device = None
        self._init_preprocess_resources()

        # CUDA 上下文与 TensorRT 引擎初始化。
        self.ctx = cuda.Device(0).make_context()
        TRT_LOGGER = trt.Logger(trt.Logger.INFO)
        runtime = trt.Runtime(TRT_LOGGER)

        with open(engine_file_path, "rb") as f:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        self.stream = cuda.Stream()

        # Host/GPU 输入输出缓冲区。
        self.host_inputs = []
        self.cuda_inputs = []
        self.host_outputs = []
        self.cuda_outputs = []
        # Tensor 名称绑定列表（TensorRT v3 API 需按名称 set_tensor_address）。
        self.input_binding = []
        self.output_binding = []

        for binding in self.engine:
            shape = self.engine.get_tensor_shape(binding)
            size = trt.volume(shape)
            dtype = trt.nptype(self.engine.get_tensor_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            cuda_mem = cuda.mem_alloc(host_mem.nbytes)

            if self.engine.get_tensor_mode(binding) == trt.TensorIOMode.INPUT:
                self.input_binding.append(binding)
                self.input_h = shape[-2]
                self.input_w = shape[-1]
                self.host_inputs.append(host_mem)
                self.cuda_inputs.append(cuda_mem)
            else:
                self.output_binding.append(binding)
                self.host_outputs.append(host_mem)
                self.cuda_outputs.append(cuda_mem)

        self.batch_size = self.engine.get_tensor_shape(self.input_binding[0])[0]
        self.det_output_length = self.host_outputs[0].shape[0]

        for k in keys:
            self.warn[k] = False
            self.status[k] = True

        logger.info(f"Preprocessing mode: {self.preprocess_mode}")

    def _select_preprocess_mode(self, mode):
        """自动选择最佳预处理模式"""
        if mode == "auto":
            if HAS_CV2_CUDA and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                return "opencv_cuda"
            elif HAS_CUDA:
                return "cpu_optimized"
            else:
                return "cpu_optimized"  # 默认用优化的 CPU
        elif mode == "torch" and HAS_CUDA:
            return "torch"
        elif mode == "opencv_cuda" and HAS_CV2_CUDA:
            return "opencv_cuda"
        elif mode == "cpu_optimized":
            return "cpu_optimized"
        else:
            return "cpu"

    def _init_preprocess_resources(self):
        """初始化预处理资源"""
        if self.preprocess_mode == "torch" and HAS_CUDA:
            self.device = torch.device("cuda")
        elif self.preprocess_mode == "opencv_cuda" and HAS_CV2_CUDA:
            self.device = torch.device("cuda")

    def infer(self, key, raw_image, T):
        del T
        # 推理 + 业务规则处理。
        result = self.predict(raw_image)
        frame = self.process_business(key, result)
        return frame, result.infer_cost

    def predict(self, raw_image):
        with self._infer_lock:
            # push/pop 成对出现，保证多线程下 CUDA 上下文安全。
            self.ctx.push()
            try:
                image, image_raw, h, w = self.preprocess_image(raw_image)
                np.copyto(self.host_inputs[0], image.ravel())
                start = time.time()

                cuda.memcpy_htod_async(self.cuda_inputs[0], self.host_inputs[0], self.stream)
                self.context.set_tensor_address(self.input_binding[0], int(self.cuda_inputs[0]))
                self.context.set_tensor_address(self.output_binding[0], int(self.cuda_outputs[0]))
                self.context.execute_async_v3(stream_handle=self.stream.handle)
                cuda.memcpy_dtoh_async(self.host_outputs[0], self.cuda_outputs[0], self.stream)
                self.stream.synchronize()
                end = time.time()

                output = self.host_outputs[0]
                result_boxes, result_scores, result_classid = self.post_process(output, h, w)
            finally:
                self.ctx.pop()

        labels = []
        boxs = {}
        conf = {}
        frame = image_raw.copy()

        for i in range(len(result_boxes)):
            box = result_boxes[i]
            cls = int(result_classid[i])
            scores = result_scores[i]
            if scores < conf_list[cls]:
                # 低于类别阈值直接过滤，减少误检干扰业务规则。
                continue

            label = categories[cls]
            labels.append(label)
            plot_one_box(box, frame, color=globalColors[cls], label=f"{label}:{scores:.2f}")

            if label not in boxs:
                boxs[label] = []
                conf[label] = []
            boxs[label].append(box)
            conf[label].append(round(scores, 2))

        logger.info(labels)
        return DetectionResult(
            annotated_frame=frame,
            raw_frame=image_raw,
            labels=labels,
            boxs=boxs,
            conf=conf,
            infer_cost=end - start,
        )

    def process_business(self, key, result):
        # 规则层可能会直接修改传入帧，因此保留一份 raw_frame 供兼容逻辑使用。
        frame1 = result.raw_frame.copy()
        if len(result.labels) >= 1:
            frame, cls, box_r = self.business.dect(
                key,
                result.annotated_frame,
                result.labels,
                self.warn[key],
                result.boxs,
                frame1,
                result.conf,
            )
        else:
            frame, cls, box_r = self.business.dect(
                key,
                result.raw_frame,
                result.labels,
                self.warn[key],
                result.boxs,
                frame1,
                result.conf,
            )

        del cls, box_r
        return frame

    def preprocess_image_torch(self, raw_bgr_image):
        """GPU 预处理版本（使用 PyTorch）"""
        image_raw = np.array(raw_bgr_image)
        h, w, _ = image_raw.shape

        # numpy -> tensor，BGR -> RGB，HWC -> CHW
        img_tensor = torch.from_numpy(image_raw).permute(2, 0, 1).flip(0).contiguous()
        img_tensor = img_tensor.to(self.device, dtype=torch.float32)

        # 计算缩放比例
        r_w = self.input_w / w
        r_h = self.input_h / h

        if r_h > r_w:
            new_w, new_h = self.input_w, int(r_w * h)
            pad_left, pad_right = 0, 0
            pad_top = (self.input_h - new_h) // 2
            pad_bottom = self.input_h - new_h - pad_top
        else:
            new_w, new_h = int(r_h * w), self.input_h
            pad_top, pad_bottom = 0, 0
            pad_left = (self.input_w - new_w) // 2
            pad_right = self.input_w - new_w - pad_left

        # 直接使用 torchvision resize
        img_tensor = F.resize(img_tensor, [new_h, new_w], antialias=True)

        # padding
        img_tensor = F.pad(img_tensor, [pad_left, pad_top, pad_right, pad_bottom], fill=128.0)

        # normalize
        img_tensor = img_tensor / 255.0

        # 添加 batch 维度
        img_tensor = img_tensor.unsqueeze(0)

        # 转换回 numpy（用于 TensorRT 输入）
        img_np = img_tensor.cpu().numpy()

        return img_np, image_raw, h, w

    def preprocess_image_opencv_cuda(self, raw_bgr_image):
        """GPU 预处理版本（使用 OpenCV-CUDA）"""
        image_raw = np.array(raw_bgr_image)
        h, w, _ = image_raw.shape

        # 创建 GpuMat
        gpu_img = cv2.cuda_GpuMat()
        gpu_img.upload(image_raw)

        # BGR -> RGB
        gpu_img = cv2.cuda.cvtColor(gpu_img, cv2.COLOR_BGR2RGB)

        # 计算缩放比例
        r_w = self.input_w / w
        r_h = self.input_h / h

        if r_h > r_w:
            new_w, new_h = self.input_w, int(r_w * h)
            pad_left, pad_right = 0, 0
            pad_top = (self.input_h - new_h) // 2
            pad_bottom = self.input_h - new_h - pad_top
        else:
            new_w, new_h = int(r_h * w), self.input_h
            pad_top, pad_bottom = 0, 0
            pad_left = (self.input_w - new_w) // 2
            pad_right = self.input_w - new_w - pad_left

        # resize
        gpu_img = cv2.cuda.resize(gpu_img, (new_w, new_h))

        # padding (在 CPU 上做，因为 OpenCV-CUDA 的 pad 比较麻烦)
        image = gpu_img.download()
        image = cv2.copyMakeBorder(
            image,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_CONSTANT,
            value=(128, 128, 128),
        )

        # normalize 和通道转换
        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        image = np.expand_dims(image, axis=0)
        image = np.ascontiguousarray(image)

        return image, image_raw, h, w

    def preprocess_image_cpu(self, raw_bgr_image):
        """原始 CPU 预处理"""
        image_raw = np.array(raw_bgr_image)
        h, w, _ = image_raw.shape
        image = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)

        r_w = self.input_w / w
        r_h = self.input_h / h

        if r_h > r_w:
            tw, th = self.input_w, int(r_w * h)
            tx1 = tx2 = 0
            ty1 = (self.input_h - th) // 2
            ty2 = self.input_h - th - ty1
        else:
            tw, th = int(r_h * w), self.input_h
            ty1 = ty2 = 0
            tx1 = (self.input_w - tw) // 2
            tx2 = self.input_w - tw - tx1

        image = cv2.resize(image, (tw, th))
        image = cv2.copyMakeBorder(
            image,
            ty1,
            ty2,
            tx1,
            tx2,
            cv2.BORDER_CONSTANT,
            value=(128, 128, 128),
        )

        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        image = np.expand_dims(image, axis=0)
        image = np.ascontiguousarray(image)
        return image, image_raw, h, w
    
    def preprocess_image_cpu_optimized(self, raw_bgr_image):
        """优化的 CPU 预处理 - 性能提升 2-4 倍"""
        image_raw = np.array(raw_bgr_image, copy=False)  # 避免不必要的拷贝
        h, w, _ = image_raw.shape
        
        # 1. 计算缩放和 padding 参数
        r_w = self.input_w / w
        r_h = self.input_h / h
        
        if r_h > r_w:
            tw, th = self.input_w, int(r_w * h)
            pad_left, pad_right = 0, 0
            pad_top = (self.input_h - th) // 2
            pad_bottom = self.input_h - th - pad_top
        else:
            tw, th = int(r_h * w), self.input_h
            pad_top, pad_bottom = 0, 0
            pad_left = (self.input_w - tw) // 2
            pad_right = self.input_w - tw - pad_left
        
        # 2. 创建输出画布（预先分配好内存）
        image = np.full((self.input_h, self.input_w, 3), 128, dtype=np.uint8)
        
        # 3. 直接在目标画布上操作：BGR -> RGB -> resize -> pad
        # 先 resize
        resized = cv2.resize(image_raw, (tw, th), interpolation=cv2.INTER_LINEAR)
        
        # BGR -> RGB（在 resize 后做，数据量更小）
        resized = resized[..., ::-1].copy()  # 利用切片反转通道
        
        # 填充到目标位置
        image[pad_top:pad_top+th, pad_left:pad_left+tw, :] = resized
        
        # 4. 归一化和维度转换合并
        image = image.astype(np.float32)
        image /= 255.0
        
        # 5. 维度转换（使用更高效的方式）
        image = np.expand_dims(image.transpose(2, 0, 1), axis=0)
        
        # 确保连续内存
        if not image.flags.c_contiguous:
            image = np.ascontiguousarray(image)
        
        return image, image_raw, h, w

    def preprocess_image(self, raw_bgr_image):
        """预处理图像，根据配置选择对应的模式"""
        if self.preprocess_mode == "torch":
            return self.preprocess_image_torch(raw_bgr_image)
        elif self.preprocess_mode == "opencv_cuda":
            return self.preprocess_image_opencv_cuda(raw_bgr_image)
        elif self.preprocess_mode == "cpu_optimized":
            return self.preprocess_image_cpu_optimized(raw_bgr_image)
        else:
            return self.preprocess_image_cpu(raw_bgr_image)

    def post_process(self, output, origin_h, origin_w):
        num = int(output[0])
        pred = np.reshape(output[1:], (-1, num_values_per_detection))[:num]
        boxes = self.non_max_suppression(pred, origin_h, origin_w)
        if len(boxes) == 0:
            return [], [], []
        return boxes[:, :4], boxes[:, 4], boxes[:, 5]

    def xywh2xyxy(self, origin_h, origin_w, x):
        y = np.zeros_like(x)
        r_w = self.input_w / origin_w
        r_h = self.input_h / origin_h

        if r_h > r_w:
            y[:, 0] = x[:, 0]
            y[:, 2] = x[:, 2]
            y[:, 1] = x[:, 1] - (self.input_h - r_w * origin_h) / 2
            y[:, 3] = x[:, 3] - (self.input_h - r_w * origin_h) / 2
            y /= r_w
        else:
            y[:, 0] = x[:, 0] - (self.input_w - r_h * origin_w) / 2
            y[:, 2] = x[:, 2] - (self.input_w - r_h * origin_w) / 2
            y[:, 1] = x[:, 1]
            y[:, 3] = x[:, 3]
            y /= r_h
        return y

    def non_max_suppression(self, prediction, origin_h, origin_w):
        boxes = prediction[prediction[:, 4] >= CONF_THRESH]
        if len(boxes) == 0:
            return np.array([])

        boxes[:, :4] = self.xywh2xyxy(origin_h, origin_w, boxes[:, :4])
        boxes[:, 0::2] = np.clip(boxes[:, 0::2], 0, origin_w - 1)
        boxes[:, 1::2] = np.clip(boxes[:, 1::2], 0, origin_h - 1)

        cls_ids = np.unique(boxes[:, 5])
        keep = []
        for cls in cls_ids:
            cls_boxes = boxes[boxes[:, 5] == cls]
            cls_boxes = cls_boxes[np.argsort(-cls_boxes[:, 4])]
            cls_keep = []
            while cls_boxes.shape[0]:
                cls_keep.append(cls_boxes[0])
                iou = self.bbox_iou(np.expand_dims(cls_boxes[0, :4], 0), cls_boxes[:, :4])
                cls_boxes = cls_boxes[iou < IOU_THRESHOLD]
            keep.extend(cls_keep)

        return np.stack(keep, 0) if keep else np.array([])

    def bbox_iou(self, box1, box2):
        x1 = np.maximum(box1[:, 0], box2[:, 0])
        y1 = np.maximum(box1[:, 1], box2[:, 1])
        x2 = np.minimum(box1[:, 2], box2[:, 2])
        y2 = np.minimum(box1[:, 3], box2[:, 3])

        inter = np.maximum(0, x2 - x1 + 1) * np.maximum(0, y2 - y1 + 1)
        area1 = (box1[:, 2] - box1[:, 0] + 1) * (box1[:, 3] - box1[:, 1] + 1)
        area2 = (box2[:, 2] - box2[:, 0] + 1) * (box2[:, 3] - box2[:, 1] + 1)
        return inter / (area1 + area2 - inter + 1e-16)

    def destroy(self):
        if self._destroyed:
            return

        self._destroyed = True
        if not hasattr(self, "ctx"):
            return

        try:
            with self._infer_lock:
                self.ctx.push()
                try:
                    try:
                        if self.stream is not None:
                            self.stream.synchronize()
                    except Exception:
                        pass

                    for mem in self.cuda_inputs:
                        try:
                            mem.free()
                        except Exception:
                            pass
                    for mem in self.cuda_outputs:
                        try:
                            mem.free()
                        except Exception:
                            pass

                    self.cuda_inputs = []
                    self.cuda_outputs = []
                    self.host_inputs = []
                    self.host_outputs = []
                    self.context = None
                    self.engine = None
                    self.stream = None
                finally:
                    self.ctx.pop()

            self.ctx.detach()
        except Exception as exc:
            logger.exception("释放 CUDA 上下文失败: %s", exc)
