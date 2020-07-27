# -*- coding: utf-8 -*-


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
    """北京市政府采购网"""
    name = 'bidding_bjszfcg'


    def __init__(self):

        # 采集几天内的数据，设置为1的时候表示采集当天
        self.limit_days = 2

        # 设置一个最大的页数
        self.max_page = 50
        #市级信息公告
        self.gkzbgg_url = 'http://www.ccgp-beijing.gov.cn/xxgg/sjzfcggg/index_{}.html'
        #区级信息公告
        self.qjzfcggg_url='http://www.ccgp-beijing.gov.cn/xxgg/qjzfcggg/index_{}.html'



        self.end_day = datetime.datetime.now().strftime('%Y-%m-%d')
        delta_day =3

        self.begin_day = (datetime.datetime.now() - datetime.timedelta(days=delta_day)).strftime('%Y-%m-%d')


        self.wait_time = 2
        self.headers = {
                        'Origin': 'http://deal.ggzy.gov.cn',
                        'Referer': 'http://deal.ggzy.gov.cn/ds/deal/dealList.jsp',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
                        }
        self.tml_logger = init_tml_logger("bidding_bjszfcg")
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
            pages =re.findall('createPageHTML\((.*?)\);	',response.text)[0].split(',')[0]
            return pages
        except:
            pages = self.max_page
            return pages

    def start_requests(self):
        """
          #公开招标公告
        self.gkzbgg_url = 'http://www.ccgp-jiangsu.gov.cn/ggxx/gkzbgg/index_{}.html'
        #资格审查公告
        self.zgysgg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/zgysgg/index_{}.html'
        #邀请招标公告
        self.yqzbgg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/yqzbgg/index_{}.html'
        #竞争谈判
        self.jztbgg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/jztbgg/index_{}.html'
        #竞争切磋
        self.jzqsgg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/jzqsgg/'
        #单一来源
        self.dylygg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/dylygg/'
        #询价公告
        self.xjgg_url='http://www.ccgp-jiangsu.gov.cn/ggxx/xjgg/'
        #中标公告
        self.zbgg_url ='http://www.ccgp-jiangsu.gov.cn/ggxx/zbgg/'
        # 成交公告
        self.cgcjgg_url ='http://www.ccgp-jiangsu.gov.cn/ggxx/cgcjgg/'
        :return:
        """
        yield scrapy.Request(url= self.gkzbgg_url .format(1),
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '市级信息公告',
                                   'source_url':self.gkzbgg_url})
        yield scrapy.Request(url=self.qjzfcggg_url.format(1),
                             callback=self.parse_bidding_infos_from_page,
                             headers=self.headers,
                             dont_filter=True,
                             meta={'key': '区级信息公告',
                                   'source_url':self.qjzfcggg_url})


    def parse_bidding_infos_from_page(self, response):
        key = response.meta['key']
        source_url=response.meta['source_url']
        nb_pages = self._get_num_of_pages(response)
        print(nb_pages)
        nb_pages=2
        self.tml_logger.info("【bidding_jszfcg】输入关键词{}获得了{}个网页".format('key', nb_pages))
        for page in range(1, int(nb_pages) + 1):
            url=source_url.format(1)
            self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页开始请求url: {}".format(key, page, url))
            try:
                yield scrapy.Request(url=url,
                                     callback=self.extract_bidding_infos_from_page,
                                     headers=self.headers,
                                     dont_filter=True,
                                     meta={
                                         'key': key,
                                         'page': page
                                     })


            except Exception as e:
                print(e)
                self.tml_logger.error(
                    "【bidding_jszfcg】关键词{}在第{}页请求url：{}时失败，失败原因{}".format('key', page, url, str(e)))
                continue

    def extract_bidding_infos_from_page(self, response):
        key = response.meta['key']
        page = response.meta['page']
        self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页，开始抽取列表页内容".format(key, page))
        css_text = response.xpath('//*[@class="xinxi_ul"]')
        datas = []
        for trs in css_text:
            tds = trs.xpath('./li')
            for index, td in enumerate(tds):
                data = {}
                data['title']= td.xpath('./a//text()').extract_first().strip()
                data['href']= td.xpath('./a/@href').extract_first()
                data['create_time']=td.xpath('./span/text()').extract()[0].strip()
                datas.append(data)

        for data in datas:
            #判断是否为空字典

            # 去除时间标签中不含时间元素的标签
            url_time = data['create_time']
            # 标题
            url_title = data['title']
            #获取url
            url=data['href']

            if key=='区级信息公告':
                detail_url=url = 'http://www.ccgp-beijing.gov.cn/xxgg/qjzfcggg/' + url.replace('./', '').replace('../', '')
            else:
                detail_url = url = 'http://www.ccgp-beijing.gov.cn/xxgg/sjzfcggg/' + url.replace('./', '').replace(
                    '../', '')



            self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页，请求网页详情url：{}".format(key, page, detail_url))
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
        self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页，开始抽取网页：{} 的详情内容".format(key, page, url))
        self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页，网页：{} 的详情内容开始填充item".format(key, page, url))
        item = BiddingItem()
        item['url'] = url
        item['url_time'] = url_time
        item['source'] = '北京市政府采购网'
        html = compress_string_and_base64_encode(content)
        item['origin_length'] = html[0]
        item['compressed_html'] = html[1]
        item['compressed_length'] = html[2]
        url_title = compress_string_and_base64_encode(title)
        item['title_origin_length'] = url_title[0]
        item['title_compressed_html'] = url_title[1]
        item['title_compressed_length'] = url_title[2]
        # self.bidding_digest_db.putSha1Digest(item['url'], item['url_time'])
        self.tml_logger.info("【bidding_jszfcg】关键词{}在第{}页，网页：{} 的详情内容item即将提交".format(key, page, url))
        yield item




