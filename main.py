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
            global tmp_path
            img_path = os.path.join(tmp_path, 'Images', pic.split('/')[-1])
            if os.path.isfile(img_path):
                return
            url = self.pic
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                print pic.split('/')[-1] + 'Error ' + str(r.status_code)
                return
            with open(img_path, 'wb') as f:
                f.write(r.content)
            print pic.split('/')[-1] + ' downloaded'
            im = Image.open(img_path)
            w, h = im.size
            if h > 1920:
                im.thumbnail((w * h // 1920, 1920))
                im.save(img_path,'jpeg')
                print pic.split('/')[-1] + ' resized'

    t = DownloadThread(pic)
    t.setDaemon(True)
    threads.append(t)
    t.start()

def extract_pic(s):
    # print(s)
    global book
    try:
        pic = s.get('file')
        if not pic.startswith('http'):
            if headers['referer'].startswith('https'):
                pic = 'https://www.lightnovel.cn/' + pic
            else:
                pic = 'http://www.lightnovel.cn/' + pic
    except Exception:
        print 'picture not loaded'
        return ''

    Imgs.append(pic.split('/')[-1])
    download_pic(pic)
    if book.coverimg is None:
        book.coverimg = pic.split('/')[-1]
    return pic.split('/')[-1]


def epub(soup):
    global tmp_path, book, threads
    basepath = os.getcwd() + os.sep + 'epub'
    # 准备目录
    if os.path.isdir('tmp'):
        c = raw_input('tmp dir exists, continue?(N) Y|N')
        if c != 'Y' and c != 'y':
            raw_input('Please delete tmp dir before retry')
            exit(1)
        else:
            os.chdir('tmp')
    else:
        os.mkdir('tmp')
        os.chdir('tmp')
        os.mkdir('Text')
        os.mkdir('Images')

    tmp_path = os.getcwd()

    def filename_escape(s):
        return re.subn(r'[/\\:\*\?\"<>\|\.]', '', s, 0)[0]

    book = Book()
    book.title = filename_escape(soup.find(id="thread_subject").string)
    print book.title
    reps = soup.find_all("a", {"class": "xw1"})
    chapter_count = 0
    i0 = reps[0]
    for i in reps:
        if i0 != i:
            break
        else:
            chapter_count += 1
    print(str(chapter_count) + ' chapters')
    book.chapter_count = chapter_count

    contents = soup.find_all("td", {"class": "t_f"})
    for i in xrange(chapter_count):
        for ig in contents[i].find_all("img"):
            new_tag = soup.new_tag('div')
            new_tag.attrs['class'] = 'duokan-image-single center'
            new_tag.append(soup.new_tag(
                'img', src='../Images/' + extract_pic(ig)))
            ig.replace_with(new_tag)
        book.Chapters.append(
            Chapter(i, str(i), 'chapter' + str(i) + '.html', remove_edit_mark(str(contents[i]))))
        # 生成页面
        t_chapter = env.get_template('Chapter.html')
        f = open(os.path.join('Text', book.Chapters[i].filename), 'w')
        f.write(t_chapter.render(chapter=book.Chapters[i]))
        f.close()
        Texts.append(book.Chapters[i].filename)
    # toc.ncx
    t_toc = env.get_template('toc.ncx')

    f = open('toc.ncx', 'w')
    f.write(t_toc.render(book=book))
    f.close()
    # content.opf

    t_content = env.get_template('content.opf')
    f = open('content.opf', 'w')
    f.write(t_content.render(book=book, Texts=Texts, Imgs=Imgs))
    f.close()

    # contents.html
    t_contents = env.get_template('Contents.html')
    f = open(os.path.join('Text', 'Contents.html'), 'w')
    f.write(t_contents.render(chapters=book.Chapters))
    f.close()

    t_cover = env.get_template('Cover.html')
    f = open(os.path.join('Text', 'Cover.html'), 'w')
    f.write(t_cover.render(coverpic=book.coverimg))
    f.close()

    t_title = env.get_template('Title.html')
    with open(os.path.join('Text', 'Title.html'), 'w') as f:
        f.write(t_title.render(book_name=book.title))
    for i in threads:
        i.join()
    with zipfile.ZipFile('../' + book.title + '.epub', 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(basepath, 'files' + os.sep + 'mimetype'),
                'mimetype', compress_type=zipfile.ZIP_STORED)
        z.write(os.path.join(basepath, 'files' + os.sep + 'container.xml'), '/META-INF/container.xml',
                compress_type=zipfile.ZIP_STORED)
        z.write(os.path.join(basepath, 'files' + os.sep + 'style.css'), '/OEBPS/Styles/style.css',
                compress_type=zipfile.ZIP_STORED)
        for dir_path, dir_names, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                f = os.path.join(dir_path, filename)
                z.write(f, 'OEBPS//' + f[len(os.getcwd()) + 1:])
    # shutil.copy(book.title + '.epub', '../')
    os.chdir('../')
    # shutil.rmtree(os.path.join(basepath, 'tmp'))
    if os.path.isdir('tmp'):
        shutil.rmtree('tmp')

env = Environment(loader=PackageLoader('epub', 'templates'))
Texts = []
Imgs = []
book = Book()
threads = []
tmp_path = ''

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

if __name__ == '__main__':
    if not os.path.isfile('LK.cookie'):
        print 'Cookie is needed for login'
        exit(1)
    with open('LK.cookie') as cookie_file:
        headers['cookie'] = cookie_file.readline()[:-1]

    reload(sys)
    sys.setdefaultencoding('utf8')

    thread_url = raw_input('Input post url')
    if len(thread_url) < 5:
        thread_url = 'http://www.lightnovel.cn/thread-861998-1-1.html'
    headers['referer'] = thread_url
    r = requests.get(thread_url, headers=headers)
    if r.status_code != 200:
        print 'NET ERROR ' + str(r.status_code)
        exit(1)
    soup = BeautifulSoup(r.text, "html.parser")
    try:
        epub(soup)
    except Exception as e:
        open("res.html","w").write(r.text)
        raise
    else:
        pass
    finally:
        pass
    print 'Done!'
