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

import md5

def download_pic(pic):
    class DownloadThread(threading.Thread):
        def __init__(self, p):
            threading.Thread.__init__(self)
            self.pic = p

        def run(self):
            global tmp_path,book
            # img_path = os.path.join(tmp_path, 'Images', pic.split('/')[-1].split('?')[0])
            # if '.' in img_path[-4:-2]:
            md5er = md5.new()
            md5er.update(pic)
            img_path = os.path.join(tmp_path, 'Images', md5er.hexdigest() + '.jpg')
            
            if os.path.isfile(img_path):
                return
            url = self.pic
            try:
                r = requests.get(url, headers=headers)
            except:
                print url + ' load error'
                return
            if r.status_code != 200:
                print pic.split('/')[-1] + 'Error ' + str(r.status_code)
                return
            with open(img_path, 'wb') as f:
                f.write(r.content)
            print img_path + ' downloaded'
            im = Image.open(img_path)
            w, h = im.size
            if h > 1920 :
                im.thumbnail((w * h // 1920, 1920))
                im.save(img_path,'jpeg')
                print img_path + ' resized'

            im.save(img_path,'jpeg')

            if 1080 > w > h and book.coverimg == md5er.hexdigest() + '.jpg':
                print 'Error cover ' + book.coverimg
                book.coverimg = Imgs[1]
                print 'New cover ' + book.coverimg


    t = DownloadThread(pic)
    t.setDaemon(True)
    threads.append(t)
    t.start()

def extract_pic(s):
    # 根据图片 URL 进行下载和重命名

    global book
    try:
        # 处理URL
        pic = s.get('file')
        if not pic.startswith('http'):
            if headers['referer'].startswith('https'):
                pic = 'https://www.lightnovel.cn/' + pic
            else:
                pic = 'http://www.lightnovel.cn/' + pic
    except Exception:
        print 'picture extract error'
        print s
        return ''

    download_pic(pic)
    # image_name = pic.split('/')[-1].split('?')[0]

    # 懒得提取 URL 里面的图片名字，直接 md5 了

    md5er = md5.new()
    md5er.update(pic)
    image_name = md5er.hexdigest() + '.jpg'
    Imgs.append(image_name)

    # 第一个图当封面
    if book.coverimg is None:
        book.coverimg = image_name

    # 返回重命名后的文件名用在电子书里面
    return image_name


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
    # 书名为标题，去除特殊字符
    book.title = filename_escape(soup.find(id="thread_subject").string)
    print book.title

    # 提取所有帖子的用户
    reps = soup.find_all("a", {"class": "xw1"})
    chapter_count = 0
    i0 = reps[0]

    # 判断是否为 LZ，只提取LZ发布的
    for i in reps:
        if i.parent['class'][0] == u'authi':
            if i0 != i:
                break
            else:
                chapter_count += 1

    print(str(chapter_count) + ' chapters')
    book.chapter_count = chapter_count

    # 帖子内容
    contents = soup.find_all("td", {"class": "t_f"})
    raw_contents = [None] * len(contents)
    for i in xrange(chapter_count):

        # pattl 是附件部分，有的作者会把图片放这里
        cp = contents[i].parent.parent.parent
        pattl = None
        if cp['class'][0] == u't_fsz':
            patts = cp.find_all(class_ = "pattl")
            if len(patts) > 0:
                pattl = patts[0]

        # 将帖子图片替换成电子书格式
        for ig in contents[i].find_all("img"):
            new_tag = soup.new_tag('div')
            new_tag.attrs['class'] = 'duokan-image-single center'
            new_tag.append(soup.new_tag(
                'img', src='../Images/' + extract_pic(ig)))
            ig.replace_with(new_tag)
        raw_contents[i] = str(contents[i])

        # 增加 pattl 附件内容
        if pattl:
            for ig in pattl.find_all("img"):
                new_tag = soup.new_tag('div')
                new_tag.attrs['class'] = 'duokan-image-single center'
                new_tag.append(soup.new_tag(
                    'img', src='../Images/' + extract_pic(ig)))
                ig.replace_with(new_tag)
            raw_contents[i] += str(pattl)


        book.Chapters.append(
            Chapter(i, str(i), 'chapter' + str(i) + '.html', remove_edit_mark(raw_contents[i])))

        # 生成页面
        t_chapter = env.get_template('Chapter.html')
        f = open(os.path.join('Text', book.Chapters[i].filename), 'w')
        f.write(t_chapter.render(chapter=book.Chapters[i]))
        f.close()
        Texts.append(book.Chapters[i].filename)

    # 等待图片下载
    for i in threads:
        i.join()
    # 生成 epub
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



    # 打包
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
#读取 cookie 以加载图片
    if not os.path.isfile('LK.cookie'):
        print 'Cookie is needed for login'
        exit(1)
    with open('LK.cookie') as cookie_file:
        headers['cookie'] = cookie_file.readline()[:-1]

    reload(sys)
    sys.setdefaultencoding('utf8')

    thread_url = raw_input('Input post url')
    if len(thread_url) < 5:
# 如果需要下载多页帖子，需要这种格式方便换页
        thread_url = 'http://www.lightnovel.cn/thread-861998-1-1.html'
    headers['referer'] = thread_url
    r = requests.get(thread_url, headers=headers)
    if r.status_code != 200:
        print 'NET ERROR ' + str(r.status_code)
        exit(1)
    text = r.text

# 换页，这里只做两页，应该够了
    if thread_url[-8] == "1":
        thread_p2 = thread_url[0:-8] + "2" + thread_url[-7:]
        r2 = requests.get(thread_p2, headers=headers)
        if r2.status_code != 200:
            print 'NET ERROR ' + str(r2.status_code) + thread_p2
        else:
            text += r2.text
# 开始处理
    soup = BeautifulSoup(text, "html.parser")
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
