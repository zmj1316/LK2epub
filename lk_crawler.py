# -*- coding: utf-8 -*-
import sys
import os
import shutil
import zipfile
import threading
import requests
import re
import uuid
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader
from PIL import Image
import opencc
cc = opencc.OpenCC('t2s')
from utils import *
import time

i = 0
import subprocess

cos = []

with open('test_titles_luru.txt','r') as st:
    for line in st.readlines():
        th,title = line.split('\t')
        if 'tid=' in th:
            r = re.match(r'.+tid=(\d+)&.+',th)
            th = 'thread-%s-1-1.html' % r.group(1)
        if len(cos) > 5:
            for i in cos:
                i.wait()

        if not '--------' in title:
            thread_url = 'https://www.lightnovel.cn/' + th
            cos.append(subprocess.Popen(['python','thread_to_epub.py',thread_url]))

            # info = threadInfo(thread_url)
            # headers = getHeaders(thread_url)
            # req = requests.get(thread_url, headers=headers,verify=False)
            # if req.status_code == 200:
            #     web_page = req.text
            #     info.page = 2
            #     thread_url2 = info.get_url()
            #     headers2 = getHeaders(thread_url2)
            #     req2 = requests.get(thread_url2, headers=headers2,verify=False)
            #     if req2.status_code == 200:
            #         web_page += req2.text
            #     with open('output/%d.html' % info.index,'wb') as out:
            #         out.write(web_page.encode('utf-8','ignore'))
            #     time.sleep(1)

