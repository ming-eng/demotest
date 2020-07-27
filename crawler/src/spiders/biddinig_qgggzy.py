# -*- coding: utf-8 -*-

import scrapy
import json
import re, pdb
import time
import datetime
import os
from urllib.parse import quote, urlencode

from scrapy.exceptions import CloseSpider
from scrapy.settings.default_settings import RETRY_TIMES
from scrapy.utils.project import get_project_settings

from src.items.items import BiddingItem
from src.utils.date_util import match_data, compare
from src.utils.html_util import html_to_plain_text
from src.utils.log_util import init_tml_logger
from src.utils.spider_util import compress_string_and_base64_encode


class BiddingJANGSUZBSpider(scrapy.Spider):
    """全国公共资源交易平台"""
    name = 'bidding_qgggzy'


    def __init__(self):

        # 采集几天内的数据，设置为1的时候表示采集当天
        self.limit_days = 2

        # 设置一个最大的页数
        self.max_page = 50
        # 招标公告列表页
        self.bidding_post_url = 'http://deal.ggzy.gov.cn/ds/deal/dealList_find.jsp'

        self.end_day = datetime.datetime.now().strftime('%Y-%m-%d')
        delta_day =3

        self.begin_day = (datetime.datetime.now() - datetime.timedelta(days=delta_day)).strftime('%Y-%m-%d')


        self.wait_time = 2
        self.headers = {
                        'Origin': 'http://deal.ggzy.gov.cn',
                        'Referer': 'http://deal.ggzy.gov.cn/ds/deal/dealList.jsp',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
                        }
        self.tml_logger = init_tml_logger("bidding_qgggzy")
        self.bat_folder = get_project_settings().get('BAT_FOLDER')
        self.zip_folder = get_project_settings().get('ZIP_FOLDER')

        # 建立保存文件
        if os.path.exists(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER'))) == False:
            os.makedirs(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER')))
        if os.path.exists(self.bat_folder) == False:
            os.makedirs(self.bat_folder)
        if os.path.exists(self.zip_folder) == False:
            os.makedirs(self.zip_folder)

    def _get_num_of_pages(self, response):
        try:
            pages =json.loads(response.text).get('ttlpage')
            return pages
        except:
            pages = self.max_page
            return pages

    def start_requests(self):
        """
        :return:
        """
        post_data={
            'TIMEBEGIN_SHOW': self.begin_day,
            'TIMEEND_SHOW': self.end_day,
            'TIMEBEGIN': self.begin_day,
            'TIMEEND': self.end_day,
            'SOURCE_TYPE': '1',
            'DEAL_TIME': '06',
            'DEAL_CLASSIFY': '01',
            'DEAL_STAGE': '0100',
            'DEAL_PROVINCE': '0',
            'DEAL_CITY': '0',
            'DEAL_PLATFORM': '0',
            'BID_PLATFORM': '0',
            'DEAL_TRADE': '0',
            'isShowAll': '1',
            'PAGENUMBER': '1',
            'FINDTXT':'',
        }
        yield scrapy.FormRequest(url=self.bidding_post_url,
                                 formdata= post_data,
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '省平台',
                                   'SOURCE_TYPE':str(1)}


                             )
        post_data = {
            'TIMEBEGIN_SHOW': self.begin_day,
            'TIMEEND_SHOW': self.end_day,
            'TIMEBEGIN': self.begin_day,
            'TIMEEND': self.end_day,
            'SOURCE_TYPE': '2',
            'DEAL_TIME': '06',
            'DEAL_CLASSIFY': '01',
            'DEAL_STAGE': '0100',
            'DEAL_PROVINCE': '0',
            'DEAL_CITY': '0',
            'DEAL_PLATFORM': '0',
            'BID_PLATFORM': '0',
            'DEAL_TRADE': '0',
            'isShowAll': '1',
            'PAGENUMBER': '1',
            'FINDTXT': '',
        }
        yield scrapy.FormRequest(url=self.bidding_post_url,
                                 formdata=post_data,
                                 callback=self.parse_bidding_infos_from_page,
                                 headers=self.headers,
                                 dont_filter=True,
                                 meta={'key': '省平台',
                                       'SOURCE_TYPE':str(2)}

                                 )


    def parse_bidding_infos_from_page(self, response):
        key = response.meta['key']
        SOURCE_TYPE=response.meta['SOURCE_TYPE']
        nb_pages = self._get_num_of_pages(response)
        self.tml_logger.info("【bidding_qgggzy】输入关键词{}获得了{}个网页".format('key', nb_pages))
        for page in range(1, int(nb_pages) + 1):
            url = self.bidding_post_url.format(page)
            self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页开始请求url: {}".format(key, page, url))
            try:
                post_data = {
                    'TIMEBEGIN_SHOW': self.begin_day,
                    'TIMEEND_SHOW': self.end_day,
                    'TIMEBEGIN': self.begin_day,
                    'TIMEEND': self.end_day,
                    'SOURCE_TYPE':  SOURCE_TYPE,
                    'DEAL_TIME': '06',
                    'DEAL_CLASSIFY': '01',
                    'DEAL_STAGE': '0100',
                    'DEAL_PROVINCE': '0',
                    'DEAL_CITY': '0',
                    'DEAL_PLATFORM': '0',
                    'BID_PLATFORM': '0',
                    'DEAL_TRADE': '0',
                    'isShowAll': '1',
                    'PAGENUMBER':str(page),
                    'FINDTXT': '',
                }
                yield scrapy.FormRequest(url=self.bidding_post_url,
                                         formdata=post_data,
                                         callback=self.extract_bidding_infos_from_page,
                                         headers=self.headers,
                                         dont_filter=True,
                                         meta={
                                             'key': key,
                                             'page': page
                                         }

                                         )

            except Exception as e:
                print(e)
                self.tml_logger.error(
                    "【bidding_qgggzy】关键词{}在第{}页请求url：{}时失败，失败原因{}".format('key', page, url, str(e)))
                continue

    def extract_bidding_infos_from_page(self, response):
        key = response.meta['key']
        page = response.meta['page']
        datas=json.loads(response.text).get('data')
        self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页，开始抽取列表页内容".format(key, page))
        for data in datas:
            #判断是否为空字典

            # 去除时间标签中不含时间元素的标签
            url_time = data['timeShow']
            # 标题
            url_title = data['title']
            #获取url
            url=data['url']
            detail_url='http://www.ggzy.gov.cn/information/html/b/'
            index=0
            for u in url.split('/')[6:]:
                index+=1

                if index!=5:
                    detail_url+=u+'/'
                else:
                    detail_url += u
            self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页，请求网页详情url：{}".format(key, page, detail_url))
            # 判断时间
            url_time = match_data(url_time)
            if self.limit_days != 0:
                if compare(url_time) <= self.limit_days:
                    yield scrapy.Request(url=detail_url,
                                         callback=self.get_content,
                                         headers=self.headers,
                                         dont_filter=True,
                                         meta={
                                             'key': key,
                                             'page': page,
                                             'url_time': url_time,
                                             'url':  detail_url,
                                             'title': url_title,
                                         }
                                         )
            else:
                yield scrapy.Request(url=detail_url,
                                     callback=self.get_content,
                                     headers=self.headers,
                                     dont_filter=True,
                                     meta={
                                         'key': key,
                                         'page': page,
                                         'url_time': url_time,
                                         'url': detail_url,
                                         'title': url_title,
                                     }
                                     )

    def get_content(self, response):
        key = response.meta['key']
        page = response.meta['page']
        url = response.meta['url']
        url_time = response.meta['url_time']
        title = response.meta['title']
        content = html_to_plain_text(response.text)
        self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页，开始抽取网页：{} 的详情内容".format(key, page, url))
        self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页，网页：{} 的详情内容开始填充item".format(key, page, url))
        item = BiddingItem()
        item['url'] = url
        item['url_time'] = url_time
        item['source'] = '全国公共资源交易平台'
        html = compress_string_and_base64_encode(content)
        item['origin_length'] = html[0]
        item['compressed_html'] = html[1]
        item['compressed_length'] = html[2]
        url_title = compress_string_and_base64_encode(title)
        item['title_origin_length'] = url_title[0]
        item['title_compressed_html'] = url_title[1]
        item['title_compressed_length'] = url_title[2]
        # self.bidding_digest_db.putSha1Digest(item['url'], item['url_time'])
        self.tml_logger.info("【bidding_qgggzy】关键词{}在第{}页，网页：{} 的详情内容item即将提交".format(key, page, url))
        yield item

    # def close(self):
    #     raise CloseSpider()


