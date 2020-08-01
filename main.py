# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os,io
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
import hashlib
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

cc = opencc.OpenCC('t2s')

isTCH = False

if sys.version > '3':
    def raw_input(ss):
        return input(ss)

    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


def md5_hash(ss):
    md5er = hashlib.md5()
    if sys.version < '3':
        md5er.update(ss)
    else:
        md5er.update(ss.encode())
    return md5er.hexdigest()


class Chapter(object):
    def __init__(self, n, title, filename, contents):
        self.title = title
        self.filename = filename
        self.contents = contents
        self.id = n


class Book(object):
    def __init__(self):
        self.title = "BookTitle"
        self.author = "??"
        self.chapter_count = 0
        self.Chapters = []
        self.introduction = '介绍'
        self.coverimg = None
        self.uuid = uuid.uuid1()
        self.date = ''


def remove_edit_mark(s):
    s1 = re.sub(r'''<i class="pstatus">.+?</i><br/>''', " ", s)
    s2 = re.sub(r'''<td class="t_f" .+?>''', " ", s1)
    s3 = re.sub(r"</td>", " ", s2)
    s4 = re.subn(r"</?a.*>",'',s3)[0]
    return s4

def download_pic(pic):
    class DownloadThread(threading.Thread):
        def __init__(self, p):
            threading.Thread.__init__(self)
            self.pic = p

        def run(self):
            global tmp_path,book
            # img_path = os.path.join(tmp_path, 'Images', pic.split('/')[-1].split('?')[0])
            # if '.' in img_path[-4:-2]:
            img_path = os.path.join(tmp_path, 'Images', md5_hash(pic) + '.jpg')
            
            if os.path.isfile(img_path):
                return
            url = self.pic
            try:
                r = requests.get(url, headers=image_headers,timeout=30,verify=False)
            except:
                print(url + ' load error')
                return
            if r.status_code != 200:
                print(pic.split('/')[-1] + 'Error ' + str(r.status_code))
                return
            # if len(r.content) < 100:
            #   print pic.split('/')[-1] + 'Size Too Small!'
            #   return
            with open(img_path, 'wb') as f:
                f.write(r.content)
            # print 'get ' + url
            print(url + ' downloaded')
            im = Image.open(img_path)

            im = im.convert("RGB")
            w, h = im.size
            # if len(im.split()) == 4:
            #     print('png detected')
            if h > 4096 :
                im.thumbnail((w * h // 4096, 4096))
                im.save(img_path,'jpeg')
                print(url + ' resized')

            im.save(img_path,'jpeg')

            if 900 > w > h and book.coverimg == md5_hash(pic) + '.jpg':
                print('Error cover ' + book.coverimg)
                book.coverimg = Imgs[1]
                print('New cover ' + book.coverimg)


    t = DownloadThread(pic)
    t.setDaemon(True)
    threads.append(t)
    t.start()

def extract_pic(s):
    # 根据图片 URL 进行下载和重命名

    global book
    try:
        # 处理URL

        tag = 'file'

        pic = s.get(tag)
        if pic is None or len(pic) < 5:
            tag = 'src'
            pic = s.get(tag)
        if not pic.startswith('http'):
            if headers['referer'].startswith('https'):
                pic = 'https://www.lightnovel.cn/' + pic
            else:
                pic = 'http://www.lightnovel.cn/' + pic
    except Exception:
        print('picture extract error\t' + str(s))
        return ''

    download_pic(pic)
    # image_name = pic.split('/')[-1].split('?')[0]

    # 懒得提取 URL 里面的图片名字，直接 md5 了

    image_name = md5_hash(pic) + '.jpg'
    Imgs.append(image_name)

    # 第一个图当封面
    if book.coverimg is None:
        book.coverimg = image_name

    s[tag] = '../Images/' + image_name
    s['class'] = 'duokan-image-single center'
    # 返回重命名后的文件名用在电子书里面
    return image_name


def epub(soup):
    global tmp_path, book, threads, isTCH
    basepath = os.getcwd() + os.sep + 'template'

    def filename_escape(s):
        return re.subn(r'[/\\:\*\?\"<>\|\.]', '', s, 0)[0]

    book = Book()
    # 书名为标题，去除特殊字符
    book.title = filename_escape(soup.find(attrs={"class","article-title"}).string)

    # 准备目录
    if os.path.isdir(book.title):
        os.chdir(book.title)
    else:
        os.mkdir(book.title)
        os.chdir(book.title)
        os.mkdir('Text')
        os.mkdir('Images')
    if sys.version < '3':
        tmp_path = os.getcwdu()
    else:
        tmp_path = os.getcwd()

    # print book.title
    if '繁' in book.title:
        print('triditional chinese detected')
        isTCH = True


    raw_contents = []
    # 帖子内容
    contents = soup.find_all(attrs={"class": "article-content"})
    book.chapter_count = len(contents)
    for i in xrange(book.chapter_count):
        # 将帖子图片替换成电子书格式
        for ig in contents[i].find_all("img"):
            extract_pic(ig)
        raw_contents.append(str(contents[i]))

        if isTCH:
            # print raw_contents[i]
            try:
                raw_contents[i] = cc.convert(raw_contents[i])
            except Exception as e:
                with open('error.log','ab') as o:
                    o.write(raw_contents[i].encode('utf-8'))
        book.Chapters.append(
            Chapter(i, 'Chapter' + str(i), 'chapter' + str(i) + '.html', ((raw_contents[i]))))

    # 生成页面
    t_chapter = env.get_template('Chapter.html')
    f = open(os.path.join('Text', book.Chapters[0].filename), 'wb')
    f.write(t_chapter.render(chapter=book.Chapters[0]).encode('utf-8'))
    f.close()
    Texts.append(book.Chapters[0].filename)

    # 等待图片下载
    for i in threads:
        i.join()
    # 生成 epub
    # toc.ncx
    t_toc = env.get_template('toc.ncx')

    f = open('toc.ncx', 'wb')
    f.write(t_toc.render(book=book).encode('utf-8'))
    f.close()
    # content.opf

    t_content = env.get_template('content.opf')
    f = open('content.opf', 'wb')
    f.write(t_content.render(book=book, Texts=Texts, Imgs=Imgs).encode('utf-8'))
    f.close()

    # contents.html
    t_contents = env.get_template('Contents.html')
    f = open(os.path.join('Text', 'Contents.html'), 'wb')
    f.write(t_contents.render(chapters=book.Chapters).encode('utf-8'))
    f.close()

    t_cover = env.get_template('Cover.html')
    f = open(os.path.join('Text', 'Cover.html'), 'wb')
    f.write(t_cover.render(coverpic=book.coverimg).encode('utf-8'))
    f.close()

    t_title = env.get_template('Title.html')
    with open(os.path.join('Text', 'Title.html'), 'wb') as f:
        f.write(t_title.render(book_name=book.title).encode('utf-8'))



    # 打包
    with zipfile.ZipFile('../' + book.title + '.epub', 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(basepath, 'files' + os.sep + 'mimetype'),
                'mimetype', compress_type=zipfile.ZIP_STORED)
        z.write(os.path.join(basepath, 'files' + os.sep + 'container.xml'), '/META-INF/container.xml',
                compress_type=zipfile.ZIP_STORED)
        z.write(os.path.join(basepath, 'files' + os.sep + 'style.css'), '/OEBPS/Styles/style.css',
                compress_type=zipfile.ZIP_STORED)
        if sys.version < '3':
            for dir_path, dir_names, filenames in os.walk(os.getcwdu()):
                for filename in filenames:
                    f = os.path.join(dir_path, filename)
                    z.write(f, 'OEBPS//' + f[len(os.getcwdu()) + 1:])
        else:
            for dir_path, dir_names, filenames in os.walk(os.getcwd()):
                for filename in filenames:
                    f = os.path.join(dir_path, filename)
                    z.write(f, 'OEBPS//' + f[len(os.getcwd()) + 1:])
    os.chdir('../')
    if os.path.isdir(book.title):
        shutil.rmtree(book.title)

env = Environment(loader=PackageLoader('template', 'templates'))
Texts = []
Imgs = []
book = Book()
threads = []
tmp_path = ''

headers = {
    'dnt': '1',
    'accept-encoding': 'gzip, deflate, br',
    'user-agent': ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36"),
    'accept': ("text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"),
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,en-US;q=0.6',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests':'1',
}

image_headers = {
    'dnt': '1',
    'accept-encoding': 'gzip, deflate, sdch',
    'user-agent': ("Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
                   " AppleWebKit/537.36 (KHTML, like Gecko)"
                   " Chrome/48.0.2564.109 Safari/537.36"),
    'accept': (",image/webp,*/*;q=0.8"),
    'cookie': ''
}

if __name__ == '__main__':
#读取 cookie 以加载图片
    # if not os.path.isfile('LK.cookie'):
    #     print('Cookie is needed for login')
    #     exit(1)
    # with open('LK.cookie') as cookie_file:
    #     headers['cookie'] = cookie_file.readline()[:-1]

    if sys.version < '3':
        reload(sys)
        sys.setdefaultencoding('utf8')

    thread_url = raw_input('Input post url').strip()
    headers['referer'] = 'https://www.lightnovel.us/'
    r = requests.get(thread_url, headers=headers,verify=False)
    text = r.text
    try:
        if r.status_code != 200:
            raise Exception('NET ERROR ' + str(r.status_code))

        soup = BeautifulSoup(text, "html.parser")
        epub(soup)
    except Exception as e:
        if sys.version < '3':
            open("res.html","w").write(r.text)
        else:
            open("res.html","w",encoding='utf-8').write(r.text)
        raise
    else:
        pass
    finally:
        pass