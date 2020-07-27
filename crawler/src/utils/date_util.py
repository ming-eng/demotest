import  re
import datetime


def match_data(text):
    data_text=re.findall('\d{4}-\d{2}-\d{2}',text)
    if data_text:
        return  data_text[0]


def compare(urltime):
    begin_day = datetime.datetime.now()
    d = datetime.datetime.strptime(urltime, '%Y-%m-%d')
    delta =  begin_day- d
    return  delta.days


