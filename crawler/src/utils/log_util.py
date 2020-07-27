# -*- coding: utf-8 -*-

"""
设置日志格式与日志存储方式
"""

from datetime import datetime
import os
import logging
import re
import sys,pdb,time

from logging.handlers import RotatingFileHandler
from scrapy.utils.project import get_project_settings

def init_tml_logger(logger_name,logger_level=logging.DEBUG):
    """
    - Function: 获取tml logger，将日志写入logstash
    - Parmns: type: 数据结果类型
    - Return:
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    dir = get_project_settings().get('LOG_DIR') + logger_name + "/" + time.strftime('%Y-%m-%d', time.localtime())
    if not os.path.isdir(dir):
        os.makedirs(dir)
    path = os.path.join(dir, '%s.log'%logger_name)
    # 本地的日志
    fh = RotatingFileHandler(path,
                             maxBytes=100 * 1024 * 1024,
                             backupCount=5)
    fh.setLevel(logger_level)
    formatter = logging.Formatter("%(asctime)s - %(funcName)s  - %(lineno)d  - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger
