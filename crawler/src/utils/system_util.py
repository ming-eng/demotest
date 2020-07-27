# -*- coding: utf-8 -*-

import os
import datetime
import time
import re


def time_with_underline_serialize():
    """
    时间序列化,返回当前时间诸如2019_01_01_00_00_00
    """
    ser_time = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    return ser_time

