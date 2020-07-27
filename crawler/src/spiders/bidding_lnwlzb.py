# -*- coding: utf-8 -*-
import math

import scrapy
import json
import re, pdb
import time
import datetime
from urllib.parse import quote, urlencode
from scrapy.utils.project import get_project_settings
from src.items.items import BiddingItem
from src.utils.date_util import compare
from src.utils.html_util import html_to_plain_text
from src.utils.log_util import init_tml_logger
from src.utils.spider_util import compress_string_and_base64_encode

import os

class BiddingCCGPSpider(scrapy.Spider):
    """辽宁省网联招标投标综合服务平台
    """
    name = 'bidding_lnwlzb'
    # crawler_settings = get_crawler_config_from_setting(name, get_project_settings().get('SCRAPY_CONFIG_FPATH'))

    def __init__(self):
        """"""

        #政府采购列表页
        self.gov_url='http://www.lnwlzb.com/EpointWebBuilder_lngc/jyxxInfoAction.action?cmd=getInfolist&fbdate=&jyfrom=&ywtype=&xxtype=&title=&pageSize=10&pageIndex={}'

        # 采集几天内的数据，设置为1的时候表示采集当天
        self.limit_days = 2
        # 设置一个最大的页数
        self.max_page = 50


        self.headers = {
                'pragma': "no-cache",
                'accept-encoding': "gzip, deflate",
                'accept-language': "zh-CN,zh;q=0.9",
                'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36",
                'content-type': "application/json;charset=utf-8",
                'accept': "application/json, text/javascript, */*; q=0.01",
                'cache-control': "no-cache",
                'x-requested-with': "XMLHttpRequest",
                'cookie': "JSESSIONID=CC1DC68DD50AB48580A71BBFCC7360D5",
                'connection': "keep-alive",
                'referer': "http://www.lnwlzb.com/tradeinfo.html",

    }
        self.wait_time = 2
        self.tml_logger = init_tml_logger("bidding")
        self.bat_folder = get_project_settings().get('BAT_FOLDER')
        self.zip_folder = get_project_settings().get('ZIP_FOLDER')

        #建立保存文件
        if os.path.exists(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER'))) == False:
            os.makedirs(os.path.join(get_project_settings().get('SAVE_DIGEST_FOLDER')))
        if os.path.exists(self.bat_folder ) == False:
            os.makedirs(self.bat_folder )
        if os.path.exists(self.zip_folder ) == False:
            os.makedirs(self.zip_folder )


    def _get_num_of_pages(self, text):
        try:
            json_text=json.loads(text)
            text=json_text.get("custom")
            pages = re.findall('\\"TotalNum\\": (\d+),', text)[0]
            num = math.ceil(int(pages) / 10)
            return num + 1
        except:
            return 2000

    def start_requests(self):
        """

        :return:
        """
        yield scrapy.Request(url= self.gov_url.format(1),
                                 callback=self.parse_bidding_infos_from_page,
                                 headers=self.headers,
                                 dont_filter=True,
                             meta={'key':'不限'}

                                 )


    def parse_bidding_infos_from_page(self, response):
        key=response.meta['key']
        nb_pages=self._get_num_of_pages(response.text)
        self.tml_logger.info("【bidding_ccgp】输入关键词{}获得了{}个网页".format('key', nb_pages))
        nb_pages=2
        for page in range(1, int(nb_pages)+1):
            import time
            time.sleep(self.wait_time)
            url = self.gov_url.format(str(page))
            self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页开始请求url: {}".format(key, page, url))
            yield scrapy.Request(url=self.gov_url.format(1),
                                 callback=self.extract_bidding_infos_from_page,
                                 headers=self.headers,
                                 dont_filter=True,
                                 meta={'key': '政府采购',
                                       'page': page})



    def extract_bidding_infos_from_page(self,response):

        key = response.meta['key']
        page = response.meta['page']
        result = json.loads(response.body)
        custom=result['custom']
        result = json.loads(custom)
        datas=result.get('Table')
        self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页，开始抽取列表页内容".format(key, page))
        for data in datas:
            #时间
            create_time = data['date']
            #标题
            bulletinName=data['title']
            url=data['infourl']
            if 'http' not in url:
                url='http://www.lnwlzb.com'+url
            self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页，请求网页详情url：{}".format(key, page, url))
            if self.limit_days!=0:
                yield scrapy.Request(url= url,
                                     callback=self.get_content,
                                     headers=self.headers,
                                     dont_filter=True,
                                     meta={
                                         'key': key,
                                         'page': page,
                                         'url_time':create_time,
                                         'url':url,
                                         'title':bulletinName,
                                     }
                                     )
            else:
                if compare(create_time)<self.limit_days:
                    yield scrapy.Request(url=url,
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
        url_time =response.meta['url_time']
        title = response.meta['title']
        content=html_to_plain_text(response.text)
        self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页，开始抽取网页：{} 的详情内容".format(key, page, url))
        time.sleep(self.wait_time)
        self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页，网页：{} 的详情内容开始填充item".format(key, page, url))
        item = BiddingItem()
        item['url'] = url
        item['url_time'] = url_time
        item['source'] = '辽宁省网联招标投标综合服务平台'
        html = compress_string_and_base64_encode(content)
        item['origin_length'] = html[0]
        item['compressed_html'] = html[1]
        item['compressed_length'] = html[2]
        url_title = compress_string_and_base64_encode(title)
        item['title_origin_length'] = url_title[0]
        item['title_compressed_html'] = url_title[1]
        item['title_compressed_length'] = url_title[2]
        # self.bidding_digest_db.putSha1Digest(item['url'], item['url_time'])
        self.tml_logger.info("【bidding_ccgp】关键词{}在第{}页，网页：{} 的详情内容item即将提交".format(key, page, url))
        yield item
        #
