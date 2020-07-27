# -*- coding: utf-8 -*-

import scrapy
import json
import re, pdb
import time
import datetime
import os
from urllib.parse import quote, urlencode

from scrapy.exceptions import CloseSpider
from scrapy.utils.project import get_project_settings

from src.items.items import BiddingItem
from src.utils.date_util import match_data, compare
from src.utils.html_util import html_to_plain_text
from src.utils.log_util import init_tml_logger
from src.utils.spider_util import compress_string_and_base64_encode

class BiddingJANGSUZBSpider(scrapy.Spider):
    
    """江苏招标投标公共服务平台"""
    name = 'bidding_jiangsuzb'

    def __init__(self):

        # 采集几天内的数据，设置为1的时候表示采集当天
        self.limit_days = 2

        # 设置一个最大的页数
        self.max_page = 50
        # 招标公告列表页
        self.bidding_index_url='http://api.jszbtb.com/DataSyncApi/HomeTenderBulletin?PageSize=20&CurrentPage={}'
        # 资格预审公告列表页
        self.check_index_url='http://api.jszbtb.com/DataSyncApi/HomeQulifyBulletin?PageSize=20&CurrentPage={}'
        # 招标公告详情url
        self.bidding_detail_url = 'http://api.jszbtb.com/DataSyncApi/TenderBulletin/id/{}'
        # 招标公告详情真实url
        self.bidding_true_url = 'http://www.jszbtb.com/#/bulletindetail/TenderBulletin/{}'
        # 资格预审公告详情url
        self.check_detail_url = 'http://api.jszbtb.com/DataSyncApi/QulifyBulletin/id/{}'
        # 资格预审公告真实url
        self.check_true_url = 'http://www.jszbtb.com/#/bulletindetail/QulifyBulletin/{}'
        

        self.wait_time = 2
        self.headers = get_project_settings().get('HEADERS')
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
            pages = re.findall('totalPage":(\d+),', text, re.DOTALL)[0]
            return pages
        except:
            pages = self.max_page
            return pages

    def start_requests(self):
        """

        :return:
        """


        yield scrapy.Request(url= self.bidding_index_url.format(1),
                                 callback=self.parse_bidding_infos_from_page,
                                 headers=self.headers,
                                 dont_filter=True,
                             meta={'key':'招标公告'}

                                 )

        yield scrapy.Request(url=self.check_index_url.format(1),
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '资格预审公告'}

                             )




    def parse_bidding_infos_from_page(self, response):
        key=response.meta['key']
        nb_pages=self._get_num_of_pages(response.text)
        print(nb_pages)
        nb_pages=2
        self.tml_logger.info("【bidding_jiangsuzb】输入关键词{}获得了{}个网页".format('key', nb_pages))
        for page in range(1, int(nb_pages)+1):
            if key == '招标公告':
                url = self.bidding_index_url.format(page)
            elif key == '资格预审公告':
                url =self.check_index_url.format(page)
            self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页开始请求url: {}".format(key, page, url))
            try:
                yield scrapy.Request(url=url,
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
                self.tml_logger.error("【bidding_jiangsuzb】关键词{}在第{}页请求url：{}时失败，失败原因{}".format('key', page,  url, str(e)))
                continue



    def extract_bidding_infos_from_page(self,response):

        key = response.meta['key']
        page = response.meta['page']
        result = json.loads(response.body)
        datas = result['data']['data']
        self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页，开始抽取列表页内容".format(key, page))
        for data in datas:
            # 去除时间标签中不含时间元素的标签
            url_time = data['create_time']
            # 标题
            url_title = data['bulletinName']
            id=data['id']
            if key=='招标公告':
                detail_url=self.bidding_detail_url.format(id)
                url=self.bidding_true_url.format(id)
            elif key=='资格预审公告':
                detail_url = self.check_detail_url.format(id)
                url = self.check_true_url.format(id)
            self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页，请求网页详情url：{}".format(key, page, detail_url))
            # 判断时间
            url_time = match_data(url_time)
            if self.limit_days!=0:
                if compare(url_time)<=self.limit_days:
                    yield scrapy.Request(url= detail_url,
                                         callback=self.get_content,
                                         headers=self.headers,
                                         dont_filter=True,
                                         meta={
                                             'key': key,
                                             'page': page,
                                            'url_time':url_time,
                                             'url':url,
                                             'title':url_title,
                                         }
                                         )
            else:
                yield scrapy.Request(url= detail_url,
                                         callback=self.get_content,
                                         headers=self.headers,
                                         dont_filter=True,
                                         meta={
                                             'key': key,
                                             'page': page,
                                            'url_time':url_time,
                                             'url':url,
                                             'title':url_title,
                                         }
                                         )




    def get_content(self, response):
            key = response.meta['key']
            page = response.meta['page']
            url = response.meta['url']
            url_time =response.meta['url_time']
            title = response.meta['title']
            json_result=json.loads(response.text)
            bulletincontent=json_result['data']['data'][0]['bulletincontent']
            content=html_to_plain_text(bulletincontent)
            self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页，开始抽取网页：{} 的详情内容".format(key, page, url))
            # time.sleep(self.wait_time)
            self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页，网页：{} 的详情内容开始填充item".format(key, page, url))
            item = BiddingItem()
            item['url'] = url
            item['url_time'] = url_time
            item['source'] = '江苏招标投标公共服务平台'
            html = compress_string_and_base64_encode(content)
            item['origin_length'] = html[0]
            item['compressed_html'] = html[1]
            item['compressed_length'] = html[2]
            url_title = compress_string_and_base64_encode(title)
            item['title_origin_length'] = url_title[0]
            item['title_compressed_html'] = url_title[1]
            item['title_compressed_length'] = url_title[2]
            # self.bidding_digest_db.putSha1Digest(item['url'], item['url_time'])
            self.tml_logger.info("【bidding_jiangsuzb】关键词{}在第{}页，网页：{} 的详情内容item即将提交".format(key, page, url))
            yield item

    # def close(self):
    #     raise CloseSpider()


