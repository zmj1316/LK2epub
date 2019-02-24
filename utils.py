# -*- coding: utf-8 -*-
import re
import requests
from bs4 import BeautifulSoup

def addCookieToHeaders(headers):
    with open('LK.cookie') as cookie_file:
        headers['cookie'] = cookie_file.readline()[:-1]
    return headers


def getHeaders(referer):
    headers = {
        'dnt': '1',
        'accept-encoding': 'gzip, deflate, sdch',
        'user-agent': ("Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
                    " AppleWebKit/537.36 (KHTML, like Gecko)"
                    " Chrome/48.0.2564.109 Safari/537.36"),
        'accept': ("text/html,application/xhtml+xml,application/xml;q=0.9"
                ",image/webp,*/*;q=0.8"),
        'cookie': ''
    }
    headers['referer'] = referer
    headers = addCookieToHeaders(headers)
    return headers

class threadInfo:
    def __init__(self, thread_url):
        m = re.match(r'(https?)://(.+lightnovel.+)/(thread|forum)-(\d+)-(\d+).+', thread_url)
        assert(m)
        self.http = m.group(1)
        self.torf = m.group(3)

        self.is_https = self.http == 'https'
        self.is_thread = self.torf == 'thread'
        self.is_forum = self.torf == 'forum'
        self.index = int(m.group(4))
        self.page = int(m.group(5))

    def __str__(self):
        return 'is_https: {}, is_thread: {}, is_forum: {}, index: {}, page: {} '.format(self.is_https,self.is_thread,self.is_forum,self.index,self.page)

    def get_http(self):
        return 'https' if self.is_https else 'http'

    def get_url(self):
        return '{}://www.lightnovel.cn/{}-{}-{}{}.html'.format(self.http,self.torf,self.index,self.page,'-1' if self.is_thread else '')


class thread_page_content:
    def __init__(self,thread_url):
        self.thread_url = thread_url
        headers = getHeaders(thread_url)
        self.req = requests.get(thread_url, headers=headers,verify=False)
        assert(self.req.status_code == 200)
        self.content = self.req.text
        # self.soup = BeautifulSoup(self.content, "html.parser")
        self.soup = BeautifulSoup(self.content, "html5lib")


    def start_parse(self):
        soup = self.soup
        self.subject = soup.find(id="thread_subject").string
        self.users = soup.find_all("a", {"class": "xw1"})
        self.layers = soup.find_all("td", {"class": "t_f"})
        self.isTCH = '繁' in self.subject

def debug(node):
    with open('%s.html' % node.name,'w') as log:
        log.write(node.encode('utf-8'))

class forum_page_content(thread_page_content):
    def __init__(self, thread_url):
        thread_page_content.__init__(self,thread_url)

    
    def start_parse(self):
        try:
            soup = self.soup
            thread_list = soup.find(id="threadlisttableid").find_all('tbody')
            normal_thread_list = []
            for i in thread_list:
                if 'id' in i.attrs and 'normalthread' in i['id']:
                    a = i.tr.th.find_all('a',recursive=False)[1]
                    url = a['href']
                    title = a.string
                    normal_thread_list.append((url.encode('gbk','ignore'),title.encode('gbk','ignore')))
                    print title.encode('gbk','ignore')

            self.normal_thread_list = normal_thread_list


            return True
        except Exception as e:
            print e
            debug(self)
            return False

# try:   
# aaa = forum_page_content('https://www.lightnovel.cn/forum-4-1.html')
# aaa.start_parse()
# except Exception as e:
#     with open('debug.html','w') as log:
#         log.write(aaa.content.encode('utf-8'))
#         raise e