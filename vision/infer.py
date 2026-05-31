import ctypes
import os
import sys

from utils.logger_util import LoggerUtil
from pipeline import PipelineConfig, PipelineRuntime, install_signal_handlers, load_sources
from yoLov8TRT import YoLov8TRT

logger = LoggerUtil.get_logger(__name__)


def main():
    # 先加载运行配置和视频源配置，任何关键文件缺失都直接失败退出，避免服务半启动状态。
    config = PipelineConfig()
    sources = load_sources(config)
    keys = list(sources.keys())

    logger.info(
        "startup source_count=%s engine=%s source_config=%s server_mode=%s",
        len(keys),
        config.engine_path,
        config.source_config_path,
        config.use_server_sources,
    )

    if not os.path.exists(config.plugin_library):
        raise FileNotFoundError(f"plugin 库不存在: {config.plugin_library}")

    ctypes.CDLL(config.plugin_library)
    detector = YoLov8TRT(config.engine_path, keys, sources, config.use_server_sources)
    runtime = PipelineRuntime(detector, config, sources)
    install_signal_handlers(runtime)

    try:
        runtime.start()
        runtime.wait_forever()
    finally:
        runtime.stop()
        detector.destroy()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("服务启动失败: %s", exc)
        sys.exit(1)
