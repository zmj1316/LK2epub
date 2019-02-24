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


info = threadInfo('https://www.lightnovel.cn/forum-4-1.html')

result = open('test_titles_luru.txt','wb')
for i in xrange(280,281):
    info.page = i
    f = forum_page_content('https://www.lightnovel.cn/forum.php?mod=forumdisplay&fid=173&filter=typeid&typeid=367')
    if f.start_parse():
        for pair in f.normal_thread_list:
            result.write('%s\t%s\n' % pair)
    else:
        break
