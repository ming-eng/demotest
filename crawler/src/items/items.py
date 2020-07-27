# -*- coding: utf-8 -*-

"""
元数据爬取格式
"""
import scrapy


class BiddingItem(scrapy.Item):
    """
    源数据格式
    """
    # 任务字段
    url = scrapy.Field()  # 源地址
    url_time = scrapy.Field()  # 网页时间
    source = scrapy.Field()  # 网页源头

    origin_length = scrapy.Field()  # 源文件长度
    compressed_html = scrapy.Field()  # 源压缩
    compressed_length = scrapy.Field()  # 源压缩长度

    title_origin_length = scrapy.Field()
    title_compressed_html = scrapy.Field()  # 源压缩
    title_compressed_length = scrapy.Field()  # 源压缩长度

    
