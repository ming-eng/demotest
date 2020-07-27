# -*- coding: utf-8 -*-
import math

import scrapy
import json
import re, pdb
import time
import datetime
from urllib.parse import quote, urlencode
from scrapy.utils.project import get_project_settings

import os

from src.items.items import BiddingItem
from src.utils.date_util import compare
from src.utils.html_util import html_to_plain_text
from src.utils.log_util import init_tml_logger
from src.utils.spider_util import compress_string_and_base64_encode


class BiddingCCGPSpider(scrapy.Spider):
    """贵州招标投标采购网爬虫 """
    name = 'bidding_gzzb'


    def __init__(self):

        self.Count_url='http://hndzzbtb.hndrc.gov.cn/services/hl/getCount?response=application/json&day=&sheng=x1&qu=&xian=&title=&timestart=&timeend=&categorynum={}'
        self.List_url = 'http://ztb.guizhou.gov.cn/api/trade/search?pubDate=all&region=5200&industry=all&prjType=all&noticeType={}&noticeClassify=all&pageIndex={}&args='
        #招标公告
        self.bidding_categorynum='affiche'
        # 中标公告
        self.win_categorynum='publicity'
        # 采集几天内的数据，设置为1的时候表示采集当天
        self.limit_days = 2
        # 设置一个最大的页数
        self.max_page = 50

        self.headers = {
            'accept': "application/json, text/javascript, */*; q=0.01",
            'referer': "http://hndzzbtb.hndrc.gov.cn/002/tradePublic.html",
            'x-requested-with': "XMLHttpRequest",
            'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36",
            'cache-control': "no-cache",

    }

        self.wait_time = 2
        self.tml_logger = init_tml_logger("bidding_gzzb")
        self.bat_folder = get_project_settings().get('BAT_FOLDER')
        self.zip_folder = get_project_settings().get('ZIP_FOLDER')

        # 建立保存文件
        if os.path.exists(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER'))) == False:
            os.makedirs(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER')))
        if os.path.exists(self.bat_folder) == False:
            os.makedirs(self.bat_folder)
        if os.path.exists(self.zip_folder) == False:
            os.makedirs(self.zip_folder)

    def _get_num_of_pages(self, text):
        try:
            pages=json.loads(text).get('totalPage')
            return pages + 1
        except:
            return 2000

    def start_requests(self):
        """

        :return:
        """
        yield scrapy.Request(url=self.List_url.format(self.bidding_categorynum,1),
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '招标公告',
                                   'categorynum':self.bidding_categorynum}

                             )

        yield scrapy.Request(url=self.List_url.format(self.win_categorynum, 1),
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '中标公告',
                                   'categorynum': self.win_categorynum}

                             )

    def parse_bidding_infos_from_page(self, response):
        key = response.meta['key']
        bidding_categorynum=response.meta['categorynum']
        nb_pages = self._get_num_of_pages(response.text)
        self.tml_logger.info("【bidding_gzzb】输入关键词{}获得了{}个网页".format('key', nb_pages))
        for page in range(1, int(nb_pages) + 1):
            import time
            time.sleep(self.wait_time)
            url = self.List_url.format(bidding_categorynum,str(page))
            self.tml_logger.info("【bidding_gzzb】关键词{}在第{}页开始请求url: {}".format(key, page, url))
            yield scrapy.Request(url=url,
                                 callback=self.extract_bidding_infos_from_page,
                                 headers=self.headers,
                                 dont_filter=True,
                                 meta={'key': key,
                                       'page': page})

    def extract_bidding_infos_from_page(self, response):

        key = response.meta['key']
        page = response.meta['page']
        result = json.loads(response.body)
        datas = result.get('data')
        for data in datas:
            # 时间
            create_time = data['PubDate']
            # # 标题
            bulletinName = data['Title']
            id=data['Id']
            url = 'http://ztb.guizhou.gov.cn/trade/bulletin/?id={}'.format(id)
            self.tml_logger.info("【bidding_gzzb】关键词{}在第{}页，请求网页详情url：{}".format(key, page, url))
            detail_url='http://ztb.guizhou.gov.cn/api/trade/{}'.format(id)
            if self.limit_days!=0:
                yield scrapy.Request(url= detail_url,
                                     callback=self.get_content,
                                     headers=self.headers,
                                     dont_filter=True,
                                     meta={
                                         'key': key,
                                         'page': page,
                                         'url_time': create_time,
                                         'url': url,
                                         'title': bulletinName,
                                     }
                                     )
            else:
                if compare(create_time)<=self.limit_days:
                    yield scrapy.Request(url=detail_url,
                                         callback=self.get_content,
                                         headers=self.headers,
                                         dont_filter=True,
                                         meta={
                                             'key': key,
                                             'page': page,
                                             'url_time': create_time,
                                             'url': url,
                                             'title': bulletinName,
                                         }
                                         )


    def get_content(self, response):
        key = response.meta['key']
        page = response.meta['page']
        url = response.meta['url']
        url_time = response.meta['url_time']
        title = response.meta['title']
        json_result = json.loads(response.text)
        bulletincontent = json_result['Content']
        content = html_to_plain_text(bulletincontent)
        self.tml_logger.info("【bidding_gzzb】关键词{}在第{}页，开始抽取网页：{} 的详情内容".format(key, page, url))
        self.tml_logger.info("【bidding_gzzb】关键词{}在第{}页，网页：{} 的详情内容开始填充item".format(key, page, url))
        item = BiddingItem()
        item['url'] = url
        item['url_time'] = url_time
        item['source'] = '贵州省招标投标服务平台'
        html = compress_string_and_base64_encode(content)
        item['origin_length'] = html[0]
        item['compressed_html'] = html[1]
        item['compressed_length'] = html[2]
        url_title = compress_string_and_base64_encode(title)
        item['title_origin_length'] = url_title[0]
        item['title_compressed_html'] = url_title[1]
        item['title_compressed_length'] = url_title[2]
        # self.bidding_digest_db.putSha1Digest(item['url'], item['url_time'])
        self.tml_logger.info("【bidding_gzzb】关键词{}在第{}页，网页：{} 的详情内容item即将提交".format(key, page, url))
        yield item
        #
