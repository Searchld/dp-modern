"""
Dect - 业务检测模块

负责处理YOLOv8检测结果，执行各类业务规则：
- 车辆检测与录像
- 溜井安全监测（大块、满载、水流）
- 人员安全监测（安全帽、劳保服、安全绳）
- 报警日志上报
"""

import json
import os
import time
import threading

import cv2
import numpy as np
import requests
from shapely import geometry

from utils.logger_util import LoggerUtil

logger = LoggerUtil.get_logger(__name__)

# 全局变量（保留兼容性）
box_r = ""
overline = False


class Dect:
    """业务检测主类"""

    # ==================== 类常量 ====================
    # 溜井区域多边形（用于判断目标是否在溜井范围内）
    LIUJING_AREA = geometry.Polygon([(20, 205), (17, 1067), (610, 1035), (430, 125)])

    # 图片存储目录
    IMG_DIR = "/mnt/1.9t2/img_log"

    # API基础地址
    API_BASE = "http://192.168.246.136"

    # 报警接口1：溜井相关报警（水流、满载、大块）
    API_WARNING_1 = f"{API_BASE}/api/ai/warning/1"

    # 报警接口2：人员安全报警（安全帽、劳保服、安全绳）
    API_WARNING_2 = f"{API_BASE}/api/ai/warning/2"

    # 车辆日志接口
    API_CARS_LOG = f"{API_BASE}/api/carsLogs/save"

    # 本地安全区域配置
    SAFETY_AREA_PATH = "config/safety_area.json"

    # 大块报警阈值面积（像素）
    BIG_AREA_THRESHOLD = 23250

    # 水流报警X坐标阈值（用于判断水流位置）
    WATER_X_MAX = 615

    # 水流报警间隔（秒，28小时）
    WATER_ALARM_INTERVAL = 28800

    # 车辆录像停止超时（秒，无车后多少秒停止录像）
    RECORDING_STOP_TIMEOUT = 8

    # 录像最短持续时间（秒，少于此时间不发送日志）
    MIN_RECORDING_DURATION = 30

    # 车辆相关标签集合
    CAR_LABELS = {"car", "fullcar", "fullcar1", "fullcar2", "fullcar3"}
    save_labels = {"fullcar", "fullcar1", "fullcar2", "fullcar3"}
    all_car = {"car", "fullcar", "fullcar1", "fullcar2", "fullcar3", "emptycar"}

    def __init__(self, keys, sources, T):
        """
        初始化检测器

        Args:
            keys: 视频通道ID列表
            sources: 视频源配置字典
            T: 是否为测试模式（保留参数）
        """
        # 发送状态字典（未使用但保留）
        self.send = {}

        # 视频源配置
        self.sources = sources

        # 各报警类型最后一次触发时间（用于控制报警间隔）
        self.alarm_time = {sid: time.time() for sid in [
            "big", "water", "person", "full", "helmet", "safety_clothes",
            "liujing_person", "car_person", "safety_line"
        ]}

        # 各报警类型是否首次触发标志
        self.frist_time = {sid: False for sid in [
            "big", "water", "person", "full", "helmet", "safety_clothes",
            "liujing_person", "car_person", "safety_line"
        ]}

        # 通用报警间隔（秒，1小时）
        self.alarm_jiange = 3600

        # 人员相关报警间隔（秒，10分钟）
        self.alarm_jiange_person = 600

        # 安全区域（从本地配置读取，失败时使用默认溜井区域）
        self.safety_area = self.load_safety_area()
        logger.info("安全区域加载成功: %s", self.safety_area)

        # ==================== 车辆相关状态（按通道存储） ====================
        self.jushi = None          # 矿石状态
        self.zhuangzai = None      # 装载率
        self.filename = ""         # 当前截图文件名
        self.Time_End = ""         # 录像结束时间
        self.Time_Start = ""       # 录像开始时间
        self.save_img = False      # 是否已保存图片
        self.end_car = False       # 车辆是否离开
        self.frame_num = 0         # 连续检测到车辆帧数
        self.helmet_frame_count = 0      # 未戴安全帽连续帧数
        self.person_frame_count = 0      # 人员入侵连续帧数
        self.line_frame_count = 0        # 安全绳报警连续帧数

        # 按通道存储的运行时状态
        self.frames = {}           # 通道帧数据
        self.carids = {}           # 通道车辆ID
        self.starttimes = {}       # 通道录像开始时间
        self.stop = {}             # 通道停止标志
        self.ubuntu = True         # 是否Ubuntu系统
        self.writeState = {}       # 通道是否正在录像
        self.start = {}            # 通道检测到车辆时间
        self.found_car = {}        # 通道连续发现车辆帧数
        self.true_car = {}         # 通道是否确认为真车
        self.find_car_time = {}    # 通道最后发现车辆时间
        self.true_car_time = {}    # 通道确认真车时间（毫秒）

        # 通道满载图片存储
        self.fullcarimgs = {}

        # 通道车牌统计
        self.count_dic = {}
        self.count_list = {}
        self.car_choose = {}

        # 通道拍摄标志（各类型报警是否已触发）
        self.takephoto = {}        # 满载拍照标志
        self.big = {}              # 大块报警标志
        self.yiwu = {}             # 异物报警标志
        self.mud = {}              # 泥浆报警标志
        self.water = {}            # 水流报警标志
        self.fullcar_40 = {}       # 40%满载标志
        self.fullcar_60 = {}       # 60%满载标志
        self.fullcar_80 = {}       # 80%满载标志
        self.fullcar_100 = {}      # 100%满载标志

        # 车辆停留时间状态
        self.car_stay_time = {}    # 通道车辆停留时间（秒）
        self.car_stay_start_time = {}  # 通道车辆停留开始时间
        self.car_stay_alarmed = {}     # 通道车辆停留是否已报警

        # 车辆跟踪状态
        self.states = {}

        # 车牌识别对象（未使用但保留）
        self.cars = None

        # ==================== 图像处理参数 ====================
        # 车辆检测Y轴范围（归一化坐标）
        self.y_c = 0.185   # 中心Y
        self.y_u = 0.185   # 上界
        self.y_d = 0.925   # 下界

        # 车辆类型阈值
        self.thres = [127, 107, 87]

        # 允许的车牌号列表
        self.carnum = ["16", "86", "92", "97", "A70", "D25", "X02", "X05", "X10", "X12"]

        # HTTP请求头
        self.headers = {
            "Content-Type": "application/json",
            "Postman-Token": "255b9cb2-36a4-46b1-a341-2a147c94788a",
            "cache-control": "no-cache",
        }

        # 初始化各通道参数
        for key in keys:
            self.initParm(key)

    def initParm(self, key):
        """
        初始化单个通道的参数

        Args:
            key: 通道ID
        """
        # 基础状态重置
        self.jushi = "无"
        self.zhuangzai = 100
        self.filename = ""
        self.Time_End = ""
        self.Time_Start = ""
        self.save_img = False
        self.end_car = False
        self.frame_num = 0
        self.car_line = False

        # 发送状态
        self.send[key] = False
        self.starttimes[key] = 0
        self.states[key] = 0

        # 车辆检测状态
        self.start[key] = 0
        self.found_car[key] = 0
        self.duration_min = 0

        # 车辆确认状态
        self.true_car[key] = False
        self.find_car_time[key] = 0
        self.true_car_time[key] = 0

        # 车辆停留时间状态
        self.car_stay_time[key] = 0
        self.car_stay_start_time[key] = 0
        self.car_stay_alarmed[key] = False

        # 各类型报警触发标志
        self.takephoto[key] = False
        self.big[key] = False
        self.yiwu[key] = False
        self.mud[key] = False
        self.water[key] = False
        self.fullcar_40[key] = False
        self.fullcar_60[key] = False
        self.fullcar_80[key] = False
        self.fullcar_100[key] = False

        # 通道私有数据
        self.fullcarimgs[key] = ""
        self.count_dic[key] = {}
        self.count_list[key] = {}
        self.car_choose[key] = {}
        self.writeState[key] = False

    def _get_channel_from_stream(self, stream_url):
        """
        从流地址中提取 channel 编号

        Args:
            stream_url: 流地址，如 "rtsp://192.168.18.119:10086/stream_2"

        Returns:
            int: channel 编号
        """
        import re
        match = re.search(r'stream_([0-9]+)', stream_url)
        if match:
            return int(match.group(1))
        return 2

    def _get_channel(self, key):
        """
        获取通道编号

        Args:
            key: 通道ID

        Returns:
            int: 通道编号
        """
        stream_url = self.sources.get(key, "")
        return self._get_channel_from_stream(stream_url)

    def post_log(self, url, json_data):
        """
        发送日志到服务器

        Args:
            url: API地址
            json_data: POST数据（字典，会自动序列化为JSON）
        """
        try:
            # 发送POST请求，5秒超时
            response = requests.post(url, json=json_data, timeout=5)
            if response.status_code == 200:
                logger.info(f"{url}日志发送成功")
                logger.info(f"{json_data}日志发送成功")
            else:
                logger.info(f"{json_data}日志发送错误")
                logger.info(f"{url}日志发送错误 status={response.status_code} body={response.text}")
        except Exception as e:
            logger.info(f"{json_data}日志发送错误")
            logger.info(f"{url}日志发送错误 {e}")

    def load_safety_area(self):
        """
        从本地配置读取安全区域。

        配置格式：
        {"x": 11.52, "y": 9.59, "width": 1353.6, "height": 1060.654}
        """
        try:
            with open(self.SAFETY_AREA_PATH, "r", encoding="utf-8") as file:
                area = json.load(file)

            x = float(area["x"])
            y = float(area["y"])
            width = float(area["width"])
            height = float(area["height"])
            return geometry.Polygon([
                (x, y),
                (x, y + height),
                (x + width, y + height),
                (x + width, y),
            ])
        except Exception as e:
            logger.info("安全区域配置加载失败，使用默认区域: %s", e)
            return self.LIUJING_AREA

    def isCar(self, frame, key, cls):
        """
        判断检测结果是否包含车辆

        Args:
            frame: 图像帧（未使用）
            key: 通道ID（未使用）
            cls: 检测到的类别列表

        Returns:
            bool: 是否包含车辆
        """
        # 使用集合交集判断是否包含车辆相关标签
        return bool(self.CAR_LABELS & set(cls))

    def _save_img(self, key, suffix):
        """
        保存当前帧为图片

        Args:
            key: 通道ID
            suffix: 文件名后缀（如"liujing_water"）

        Returns:
            str: 保存的文件名
        """
        # 确保目录存在
        os.makedirs(self.IMG_DIR, exist_ok=True)

        # 生成文件名：stream_{通道}_{后缀}_{时间戳}.jpg
        filename = f"stream_{key}_{suffix}_{time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))}.jpg"
        imgpath = os.path.join(self.IMG_DIR, filename)

        # 保存图片
        cv2.imwrite(imgpath, self._current_frame)
        return filename

    def _async_post_log(self, url, params):
        """
        异步发送日志（不阻塞主线程）

        Args:
            url: API地址
            params: POST参数
        """
        thread = threading.Thread(target=self.post_log, args=(url, params), daemon=True)
        thread.start()

    def _get_center_point(self, box):
        """
        计算检测框中心点

        Args:
            box: 检测框坐标 [x1, y1, x2, y2]

        Returns:
            geometry.Point: 中心点几何对象
        """
        center_x = (int(box[0]) + int(box[2])) // 2
        center_y = (int(box[1]) + int(box[3])) // 2
        return geometry.Point(center_x, center_y)

    def dect(self, key, frame, cls, warn, boxs, frame1, conf):
        """
        业务检测主入口

        Args:
            key: 通道ID
            frame: 标注后的图像帧
            cls: 检测到的类别列表
            warn: 警告标志（未使用）
            boxs: 各类别对应的检测框字典 {label: [box1, box2, ...]}
            frame1: 原始图像帧
            conf: 各类别置信度字典

        Returns:
            tuple: (frame, cls, box_r)
        """
        # 保存当前帧供异步方法使用
        self._current_frame = frame

        # 1. 人员安全监测
        self.person_safety(frame, key, cls, boxs)

        # 2. 溜井安全监测
        self.liujing_work(frame, key, cls, boxs)

        # 3. 车辆检测与录像处理
        self._handle_car_detection(key, frame, cls, boxs, conf)

        return frame, cls, box_r

    def _handle_car_detection(self, key, frame, cls, boxs, conf):
        """
        处理车辆检测逻辑

        包含三个阶段：
        1. 发现车辆（连续5帧以上确认）
        2. 车辆录像中（持续检测）
        3. 车辆离开（8秒无车则停止录像）

        Args:
            key: 通道ID
            frame: 图像帧
            cls: 检测类别列表
            boxs: 检测框字典
            conf: 置信度字典
        """
        if self.isCar(frame, key, cls):
            # 阶段1：检测到车辆
            self._process_car_found(key, cls)
            # 检查车辆长时间停留
            self._check_car_stay_time(key, frame)
        else:
            # 阶段3：没有检测到车辆
            self._process_no_car(key, cls)
            # 重置车辆停留时间
            self._reset_car_stay_time(key)

        # 连续发现车辆超过5帧，开始录像
        if self.found_car[key] > 5:
            self._start_recording_if_needed(key)

        # 阶段2：车辆录像中
        if self.true_car[key]:
            self._handle_true_car(key, frame, cls, boxs, conf)

    def _process_car_found(self, key, cls):
        """
        处理检测到车辆的情况

        Args:
            key: 通道ID
            cls: 检测类别列表
        """
        # 连续发现车辆帧数+1
        self.found_car[key] += 1

        # 如果已经开始录像，则确认为真车
        if self.starttimes[key] > 0:
            self.true_car[key] = True

        # 记录发现车辆的时间
        self.find_car_time[key] = int(time.time())
        self.frame_num += 1
        self.start[key] = int(time.time())

    def _process_no_car(self, key, cls):
        """
        处理未检测到车辆的情况

        Args:
            key: 通道ID
            cls: 检测类别列表
        """
        # 如果检测到空车且之前有车，更新最后发现车辆时间
        if "emptycar" in cls and self.frame_num > 0:
            self.frame_num += 1
            self.start[key] = int(time.time())
            self.end_car = True

        # 如果正在录像，检查是否该停止
        if self.starttimes[key] > 0:
            self.true_car[key] = True
            if self.start[key] == 0:
                self.start[key] = self.starttimes[key]
            # 检查停止条件
            self._check_stop_recording(key)

    def _check_stop_recording(self, key):
        """
        检查是否应该停止录像

        条件：无车时间超过8秒

        Args:
            key: 通道ID
        """
        timenums = int(time.time()) - self.start[key]
        if timenums > self.RECORDING_STOP_TIMEOUT and self.writeState[key]:
            self._stop_recording(key)

    def _stop_recording(self, key):
        """
        停止录像

        Args:
            key: 通道ID
        """
        # 重置车辆状态
        self.true_car[key] = False

        # 计算录像持续时间
        if self.true_car_time[key] is not None:
            duration = int(round(time.time() * 1000)) - self.true_car_time[key]
            self.duration_min = int(round(duration / 1000))

        # 记录结束时间
        self.Time_End = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        logger.info(self.save_img)
        logger.info(self.duration_min)

        # 发送车辆日志（如果录像超过30秒）
        if self.save_img and self.duration_min > self.MIN_RECORDING_DURATION:
            params = {
                "channel": self._get_channel(key),
                "imgpath": f"{self.API_BASE}:888/img/{self.filename}",
                "rate": self.zhuangzai,
                "timecha": self.duration_min,
                "startTime": self.Time_Start,
                "endTime": self.Time_End,
                "bigs": self.jushi,
                "yiwu": "无"
            }
            self._async_post_log(self.API_CARS_LOG, params)

        logger.info("停止录制")
        logger.info(self.Time_End)

        # 重置通道参数
        self.initParm(key)

    def _start_recording_if_needed(self, key):
        """
        开始录像（如果尚未开始）

        Args:
            key: 通道ID
        """
        self.true_car[key] = True

        if not self.writeState[key]:
            # 记录录像开始时间
            self.starttimes[key] = int(time.time())
            self.writeState[key] = True
            self.found_car[key] = 0

            # 记录确认真车的时间（毫秒级）
            self.true_car_time[key] = int(round(time.time() * 1000))

            # 记录开始时间字符串
            self.Time_Start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            logger.info("开始录像")
            logger.info(self.Time_Start)

    def _handle_true_car(self, key, frame, cls, boxs, conf):
        """
        处理确认为真车后的逻辑

        - 判断车辆位置（是否过线）
        - 保存车辆图片
        - 检测大块

        Args:
            key: 通道ID
            frame: 图像帧
            cls: 检测类别列表
            boxs: 检测框字典
            conf: 置信度字典
        """
        self.writeState[key] = True
        self.found_car[key] = 0

        # 判断车辆是否过线（car左边框 < 600）
        if "car" in cls and not self.car_line:
            box = boxs.get("car", [])
            for i in box:
                if int(i[0]) < 600:
                    self.car_line = True

        # 车辆过线后保存图片
        car_labels = self.save_labels & set(cls)
        if car_labels and not self.save_img and self.car_line:
            filepath = f"{self.IMG_DIR}/"
            os.makedirs(filepath, exist_ok=True)
            self.filename = f"stream_{key}_{time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))}.jpg"
            self.imgpath = os.path.join(filepath, self.filename)
            cv2.imwrite(self.imgpath, frame)
            self.save_img = True
            # 调用称重方法（未实现）
            self.weight(frame, key, cls, box_r, conf)

        # 检测大块
        if "big" in cls:
            self.bigs(frame, key, cls, boxs)

    def weight(self, frame, key, cls, box_r, conf):
        """
        车辆称重（预留接口，未实现）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            box_r: 检测框
            conf: 置信度
        """
        pass

    def bigs(self, frame, key, cls, boxs):
        """
        检测大块矿石

        当大块面积超过阈值时设置标志

        Args:
            frame: 图像帧（未使用）
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
        """
        if "big" in cls and not self.big[key]:
            box = boxs.get("big", [])
            for i in box:
                # 计算检测框面积
                area = (int(i[2]) - int(i[0])) * (int(i[3]) - int(i[1]))
                if area >= self.BIG_AREA_THRESHOLD:
                    self.jushi = '大块'
                    self.big[key] = True

    def liujing_work(self, frame, key, cls, boxs):
        """
        溜井安全监测入口

        检测三类报警：
        1. 水流涌入
        2. 溜井满载
        3. 溜井大块

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
        """
        time_now = time.time()
        try:
            # 检查水流报警
            self._check_water_alarm(frame, key, cls, boxs, time_now)

            # 检查满载报警
            self._check_full_alarm(frame, key, cls, time_now)

            # 检查大块报警
            self._check_big_alarm(frame, key, cls, boxs, time_now)
        except Exception as e:
            logger.info(f"溜井检查错误：{e}")

    def _check_water_alarm(self, frame, key, cls, boxs, time_now):
        """
        检查水流涌入报警

        条件：
        - 检测到water标签
        - water左边框 < 615
        - 距离上次报警 > 28800秒（8小时）
        - 当前没有车辆（避免误报）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
            time_now: 当前时间戳
        """
        # 不在检测列表中，返回
        if "water" not in cls:
            return

        water_boxes = boxs.get("water", [])

        # 没有检测框或位置不符合条件
        if not water_boxes or water_boxes[0][0] >= self.WATER_X_MAX:
            return

        # 报警间隔未到
        if time_now - self.alarm_time["water"] <= self.WATER_ALARM_INTERVAL:
            return

        # 有车辆时不做水流报警（避免误报）
        if self.true_car.get(key, False):
            return

        # 保存图片并发送报警
        filename = self._save_img(key, "liujing_water")
        params = {
            "status": 3,  # 水流涌入
            "channel": self._get_channel(key),
            "img": f"{self.API_BASE}:888/img/{filename}",
            "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now))
        }
        self._async_post_log(self.API_WARNING_1, params)
        self.alarm_time["water"] = time_now

    def _check_full_alarm(self, frame, key, cls, time_now):
        """
        检查溜井满载报警

        条件：
        - 检测到full标签
        - 距离上次报警 > 3600秒（1小时）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            time_now: 当前时间戳
        """
        if "full" not in cls:
            return

        if time_now - self.alarm_time["full"] <= self.alarm_jiange:
            return

        filename = self._save_img(key, "liujing_full")
        params = {
            "status": 5,  # 溜井满载
            "channel": self._get_channel(key),
            "img": f"{self.API_BASE}:888/img/{filename}",
            "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now))
        }
        self._async_post_log(self.API_WARNING_1, params)
        self.alarm_time["full"] = time_now

    def _check_big_alarm(self, frame, key, cls, boxs, time_now):
        """
        检查溜井大块报警

        条件：
        - 检测到big标签
        - 大块面积 >= 23250
        - 大块中心在溜井区域内
        - 距离上次报警 > 3600秒
        - 当前没有车辆

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
            time_now: 当前时间戳
        """
        if "big" not in cls:
            return

        if time_now - self.alarm_time["big"] <= self.alarm_jiange:
            return

        if self.true_car.get(key, False):
            return

        big_boxes = boxs.get("big", [])
        for i in big_boxes:
            # 检查面积
            area = (int(i[2]) - int(i[0])) * (int(i[3]) - int(i[1]))
            if area < self.BIG_AREA_THRESHOLD:
                continue

            # 检查是否在溜井区域内
            center_point = self._get_center_point(i)
            if center_point.distance(self.LIUJING_AREA) == 0:
                filename = self._save_img(key, "liujing_big")
                params = {
                    "status": 6,  # 溜井大块
                    "channel": self._get_channel(key),
                    "img": f"{self.API_BASE}:888/img/{filename}",
                    "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now))
                }
                self._async_post_log(self.API_WARNING_1, params)
                self.alarm_time["big"] = time_now
                break

    def person_safety(self, frame, key, cls, boxs):
        """
        人员安全监测入口

        检测三类报警：
        1. 人员进入安全区域
        2. 未戴安全帽/未穿劳保服
        3. 未系安全绳进入溜井

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
        """
        time_now = time.time()
        url = self.API_WARNING_2

        # 检查人员入侵
        self._check_person_in_safety_area(frame, key, cls, boxs, time_now, url)

        # 检查安全帽/劳保服
        self._check_helmet_alarm(frame, key, cls, boxs, time_now, url)

        # 检查安全绳
        self._check_safety_line_alarm(frame, key, cls, boxs, time_now, url)

    def _check_person_in_safety_area(self, frame, key, cls, boxs, time_now, url):
        """
        检查人员入侵安全区域

        有车和无车场景不同：
        - 无车：人员入侵后30秒报警
        - 有车：人员入侵后10秒报警

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
            time_now: 当前时间戳
            url: 报警API地址
        """
        if "person" not in cls:
            # 无person时重置计数
            self.person_frame_count = 0
            self.frist_time["liujing_person"] = False
            self.frist_time["car_person"] = False
            return

        # 报警间隔控制
        if time_now - self.alarm_time["person"] <= self.alarm_jiange_person:
            return

        # 判断是否有车辆
        has_car = bool(self.all_car & set(cls))
        person_boxes = boxs.get("person", [])

        if not has_car:
            # 无车场景：连续10帧确认后计时30秒
            self._process_person_without_car(frame, key, person_boxes, time_now, url)
        else:
            # 有车场景：连续10帧确认后计时10秒
            self._process_person_with_car(frame, key, person_boxes, time_now, url)

    def _process_person_without_car(self, frame, key, person_boxes, time_now, url):
        """
        处理无车时的人员入侵

        Args:
            frame: 图像帧
            key: 通道ID
            person_boxes: 人员检测框列表
            time_now: 当前时间戳
            url: 报警API地址
        """
        for i in person_boxes:
            center_point = self._get_center_point(i)
            # 检查是否在安全区域内
            if center_point.distance(self.safety_area) != 0:
                continue

            self.person_frame_count += 1
            # 连续10帧确认
            if self.person_frame_count == 10 and not self.frist_time["liujing_person"]:
                self.alarm_time["liujing_person"] = time_now
                self.frist_time["liujing_person"] = True

        # 计时30秒后报警
        if time_now - self.alarm_time["liujing_person"] > 30 and self.frist_time["liujing_person"]:
            self._send_person_warning(frame, key, 1, time_now, url)
            self.frist_time["liujing_person"] = False

    def _process_person_with_car(self, frame, key, person_boxes, time_now, url):
        """
        处理有车时的人员入侵

        Args:
            frame: 图像帧
            key: 通道ID
            person_boxes: 人员检测框列表
            time_now: 当前时间戳
            url: 报警API地址
        """
        for i in person_boxes:
            center_point = self._get_center_point(i)
            if center_point.distance(self.safety_area) != 0:
                continue

            self.person_frame_count += 1
            if self.person_frame_count == 10 and not self.frist_time["car_person"]:
                self.alarm_time["car_person"] = time_now
                self.frist_time["car_person"] = True

        # 计时10秒后报警
        if time_now - self.alarm_time["car_person"] > 10 and self.frist_time["car_person"]:
            self._send_person_warning(frame, key, 1, time_now, url)
            self.frist_time["car_person"] = False

    def _send_person_warning(self, frame, key, warn_type, time_now, url):
        """
        发送人员入侵报警

        Args:
            frame: 图像帧
            key: 通道ID
            warn_type: 报警类型（1=入侵）
            time_now: 当前时间戳
            url: 报警API地址
        """
        filename = self._save_img(key, "person_safety")
        params = {
            "channel": self._get_channel(key),
            "picture": f"{self.API_BASE}:888/img/{filename}",
            "type": warn_type,
            "warningTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now)),
            "remark": ""
        }
        self._async_post_log(url, params)
        self.alarm_time["person"] = time_now
        self.person_frame_count = 0

    def _check_helmet_alarm(self, frame, key, cls, boxs, time_now, url):
        """
        检查安全帽/劳保服报警

        条件：安全区域内person数量 > helmet数量，连续250帧后报警

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
            time_now: 当前时间戳
            url: 报警API地址
        """
        person_num = helmet_num = 0

        # 统计安全区域内的person数量
        if "person" in cls:
            for i in boxs.get("person", []):
                if self._get_center_point(i).distance(self.safety_area) == 0:
                    person_num += 1

        # 统计安全区域内的helmet数量
        if "helmet" in cls:
            for i in boxs.get("helmet", []):
                if self._get_center_point(i).distance(self.safety_area) == 0:
                    helmet_num += 1

        # person数量大于helmet数量，说明有人未戴安全帽
        if person_num > helmet_num:
            self.helmet_frame_count += 1
            # 连续250帧确认，且报警间隔未到
            if self.helmet_frame_count == 250 and time_now - self.alarm_time["helmet"] > self.alarm_jiange_person:
                filename = self._save_img(key, "helmet")
                params = {
                    "channel": self._get_channel(key),
                    "picture": f"{self.API_BASE}:888/img/{filename}",
                    "type": 0,  # 未戴安全帽
                    "warningTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now)),
                    "remark": ""
                }
                self._async_post_log(url, params)
                self.alarm_time["helmet"] = time_now
                self.helmet_frame_count = 0
        else:
            self.helmet_frame_count = 0

    def _check_safety_line_alarm(self, frame, key, cls, boxs, time_now, url):
        """
        检查安全绳报警

        条件：
        - 检测到person
        - 未检测到safety_clothes
        - 人员在溜井区域内
        - 连续10帧确认后计时10秒

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            boxs: 检测框字典
            time_now: 当前时间戳
            url: 报警API地址
        """
        # 无person或有safety_clothes时重置
        if "person" not in cls or "safety_clothes" in cls:
            if time_now - self.alarm_time["safety_line"] > self.alarm_jiange_person:
                self.line_frame_count = 0
                self.frist_time["safety_line"] = False
            return

        # 报警间隔控制
        if time_now - self.alarm_time["safety_line"] <= self.alarm_jiange_person:
            return

        person_boxes = boxs.get("person", [])
        for i in person_boxes:
            center_point = self._get_center_point(i)
            # 检查是否在溜井区域
            if center_point.distance(self.LIUJING_AREA) != 0:
                continue

            self.line_frame_count += 1
            # 连续10帧确认
            if self.line_frame_count == 10 and not self.frist_time["safety_line"]:
                self.alarm_time["safety_line"] = time_now
                self.frist_time["safety_line"] = True
                break

        # 计时10秒后报警
        if time_now - self.alarm_time["safety_line"] > 10 and self.frist_time["safety_line"]:
            self.frist_time["safety_line"] = False
            filename = self._save_img(key, "safety_line")
            params = {
                "channel": self._get_channel(key),
                "picture": f"{self.API_BASE}:888/img/{filename}",
                "type": 2,  # 未系安全绳
                "warningTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now)),
                "remark": ""
            }
            self._async_post_log(url, params)
            self.alarm_time["safety_line"] = time_now
            self.line_frame_count = 0

    # ==================== 以下为未使用但保留的方法 ====================

    def fullCars(self, frame, key, cls, overline):
        """
        满载车辆拍照（未使用）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
            overline: 是否有界线
        """
        if self.takephoto[key]:
            return
        if ("fullcar" in cls or "emptycar" in cls) and overline:
            url = self.url + "/api/carsLogs/fullcar"
            pyload = {"ip": key}
            requests.post(url, data=json.dumps(pyload), headers=self.headers)
            self.takephoto[key] = True

    def yiwus(self, frame, key, cls):
        """
        异物检测（未使用）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
        """
        if "yiwu" in cls and not self.yiwu[key]:
            self.yiwu[key] = True

    def muds(self, frame, key, cls):
        """
        泥浆检测（未使用）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
        """
        if "mud" in cls and not self.mud[key]:
            logger.info("mud")
            url = self.url + "/api/carsLogs/recording"
            pyload = {"ip": key, "mud": "泥浆"}
            requests.post(url, data=json.dumps(pyload), headers=self.headers)
            self.mud[key] = True

    def waters(self, frame, key, cls):
        """
        水流检测（未使用）

        Args:
            frame: 图像帧
            key: 通道ID
            cls: 检测类别列表
        """
        if "water" in cls and not self.water[key]:
            logger.info("water")
            url = self.url + "/api/carsLogs/recording"
            pyload = {"ip": key, "water": "水"}
            requests.post(url, data=json.dumps(pyload), headers=self.headers)
            self.water[key] = True

    def destroy(self):
        """
        释放资源
        """
        pass

    def _check_car_stay_time(self, key, frame):
        """
        检查车辆长时间停留

        Args:
            key: 通道ID
            frame: 图像帧
        """
        import time
        current_time = time.time()
        
        # 首次检测到车辆，记录开始时间
        if self.car_stay_start_time[key] == 0:
            self.car_stay_start_time[key] = current_time
        
        # 计算停留时间（秒）
        self.car_stay_time[key] = current_time - self.car_stay_start_time[key]
        
        # 停留时间超过600秒，且未触发过报警
        if self.car_stay_time[key] > 600 and not self.car_stay_alarmed[key]:
            logger.info(f"车辆长时间停留报警：通道 {key}，停留时间 {self.car_stay_time[key]:.1f} 秒")
            
            # 保存报警图片
            suffix = "car_stay"
            self.filename = self._save_img(key, suffix)
            
            # 发送报警
            start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.car_stay_start_time[key]))
            end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
            params = {
                "status": 12,  # 潦辆长时间停留
                "channel": self._get_channel(key),
                "img": f"{self.API_BASE}:888/img/{self.filename}",
                "createTime": f"{start_time}---{end_time}"
            }
            self._async_post_log(self.API_WARNING_1, params)
            # 标记已触发报警
            self.car_stay_alarmed[key] = True

    def _reset_car_stay_time(self, key):
        """
        重置车辆停留时间

        Args:
            key: 通道ID
        """
        self.car_stay_time[key] = 0
        self.car_stay_start_time[key] = 0
        self.car_stay_alarmed[key] = False
