# -*- coding: utf-8 -*-

import zlib
import datetime
import base64
import re

def compress_string_and_base64_encode(content):
    """
    进行需求的转换编码与压缩格式
    - content：需要编码压缩的字符串

    返回：
        原始长度，压缩的网页，压缩的网页长度
    """
    origin_length = str(len(content))
    compressed_html = str(base64.b64encode(zlib.compress(content.encode())).decode())
    compressed_length = str(len(compressed_html))
    return origin_length, compressed_html, compressed_length

