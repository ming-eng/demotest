# -*- coding: utf-8 -*-

"""
解析命令文件
    - 获取命令参数
    - 修改或者替换命令
"""

import configparser


def get_crawler_config_from_setting(sections_name, setting_file):
    """获取爬虫配置参数
    """
    config = configparser.RawConfigParser()
    config.read(setting_file)

    return config[sections_name]
