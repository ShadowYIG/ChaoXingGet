#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/3/3 10：03
# @Author  : ShadowY
# @File    : ChaoXin.py
# @Software: PyCharm
# @version : 1.5
# 该程序为获取超星学习通的课程资料（视频，ppt）等，直接运行即可使用
"""
1.5 修复新接口无法获取非视频资源问题
1.4 更换新接口，修复二级目录无法下载问题
1.3 新增调用IDM下载选项
1.2 绕过验证码，修复bug
1.1 添加全局变量实现免多次输入，增加强制获取
1.0 实现超星课件，视频下载
"""
import os
import requests
from subprocess import call
import random
import time
import re
import json
import sys
import pprint
from tqdm import tqdm
from urllib import parse
from lxml import etree
import csv
ip = str(random.randint(0, 254))+"."+str(random.randint(0, 254))+"."+str(random.randint(0, 254))+"."+str(random.randint(0, 254))
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.86 Safari/537.36",
    'Referer': 'http://i.mooc.chaoxing.com',
    'X-Forwarded-For': ip,
}

"""请填写该全局变量，以便更好地体验"""
IDM_DIR = r"E:\Internet Download Manager\IDMan.exe"  # idm的路径,如果有就改成自己的，否则不要用idm下载
# 登陆信息，填了可以省略输入
USERNAME = ""  # 用户名
PASSWD = ""  # 密码
"""请填写该全局变量，以便更好地体验"""


def login_cx(username, pwd, fid_name='广州商学院'):
    """
        登陆超星慕课
        :param username: 用户名
        :param pwd： 密码
        :param fid_name: 学校名称
        :return: string 返回cookies
    """
    cx_session = requests.Session()
    # pwd = str(pwd)
    code = ''
    if download_code_img(cx_session):  # 获取验证码图片
        print("验证码已下载到运行目录的checkcode.png")
        code = input("请输入验证码:")
    else:
        print("验证码获取失败")
        return ''
    post_data = {
        'refer_0x001': 'http%3A%2F%2Fi.mooc.chaoxing.com%2Fspace%2Findex.shtml',
        'pid': '1',
        'pidName': '',
        'fid': get_fid(),
        'fidName': fid_name,
        'allowJoin': '0',
        'isCheckNumCode': '1',
        'f': '0',
        'uname': username,
        'password': pwd,
        'numcode': code,
    }
    url_login = "http://passport2.chaoxing.com/login"
    data = cx_session.post(url_login, params=post_data, headers=headers).text  # 提交登陆信息
    if "wrong" in data or "incorrect" in data:
        if "account or passport is wrong" in data:
            print("账号或密码错误")
        elif "captcha is incorrect" in data or '验证码错误' in data:
            print("验证码错误")
        else:
            print(data)
            print("未知错误")
            return False
    elif "账号管理" in data or "personalName" in data:
        print("登陆成功")
        return cx_session
    else:
        print(data)
        print("登陆失败")
        return False


def login_cx_unv(username, pwd, fid_name='广州商学院'):
    """
    超星登陆，绕过验证码
    :param username: 用户名（学号）
    :param pwd: 密码
    :param fid_name: 学校名称
    :return:
    """
    cx_session = requests.Session()
    r = cx_session.get(
        'https://passport2.chaoxing.com/api/login?name={}&pwd={}&schoolid={}&verify=0'.format(username, pwd, get_fid(fid_name)), headers=headers)
    if r.status_code == 403:
        print("网络错误")
        return False
    data = json.loads(r.text)
    if data['result']:
        print("登录成功")
        return cx_session
    else:
        print("登录信息有误")
        return False


def download_code_img(cx_session):
    """
    获取验证码图片
    :return: Boolean
    """
    num = int(time.time())
    url_code = "https://passport2.chaoxing.com/num/code"
    r = cx_session.get(url_code, stream=True)
    if r.status_code == 200:
        open('./checkcode.png', 'wb').write(r.content)  # 将内容写入图片
        return True
    else:
        print("获取验证码失败")
        exit()


def get_fid(name='广州商学院'):
    """
        获取fid
        :param name: 学校名称
        :return: str 学校id
    """
    data = requests.get(url='https://passport2.chaoxing.com/org/searchUnis?filter=' + parse.quote(name) + '&product=44')
    if data.status_code == 200:
        msg = json.loads(data.text)
        try:
            print(msg['froms'][0]['schoolid'])
            return msg['froms'][0]['schoolid']
        except:
            print("获取学校代码失败或校名不存在")
            return False
    else:
        print("获取学校代码失败或校名不存在")
        exit()


def get_all_course(cx_session):
    """
        获取所有课程
        :param cx_session session
        :return: list 课程列表
    """
    headers['Content-Encoding'] = 'gzip'
    data = cx_session.get("http://passport2.chaoxing.com/mooc.jsp?v=0&s=d60c1f3cbdcb96cd7210a0ebb66748db", headers=headers).text
    selector = etree.HTML(data)
    infos = selector.xpath("//li[@style='position:relative']")
    course_list = list()
    for info in infos:
        course_id = info.xpath("input/@value")[0]
        class_id = info.xpath("input/@value")[1]
        course_url = info.xpath("div[@class='Mconright httpsClass']//a/@href")[0]
        course_name = info.xpath("div[@class='Mconright httpsClass']//a/@title")[0].replace(u'\xa0', '').replace(' ', '')
        course_list.append({
            'course': course_id,
            'class': class_id,
            'url': course_url,
            'name': course_name
        })
    return course_list


def get_all_chapter_title(cx_session, url, op=0):
    """
        获取章节的标题
        :param cx_session: session
        :param url: 课程链接
        :param op: 选项，-1为获取单元标题，1-n为获取对应单元的课时标题，0为全部课时标题
        :return: list
    """
    data = cx_session.get("https://mooc1-2.chaoxing.com" + url, headers=headers).text
    selector = etree.HTML(data)
    infos = ''
    if op == -1:
        infos = selector.xpath("//div[@class='units']//h2/a/@title")
    elif op == 0:
        infos = selector.xpath("//div[@class='units']//div[@class='leveltwo']//span[@class='articlename']/a/@title")
    else:
        infos = selector.xpath("//div[@class='units'][" + str(op) + "]/div[@class='leveltwo']//span[@class='articlename']/a/@title")
    if infos == '':
        print("获取标题参数错误")
        return False
    re_list = list()
    for info in infos:
        re_list.append(info)
    return re_list


def get_all_chapter(cx_session, url, op=0):
    """
        获取所有章节id
        :param cx_session: session
        :param url: 课程链接
        :param op: 选项 0为全部获取，1-n为某单元
        :return: list 章节信息列表
    """
    data = cx_session.get("https://mooc1-2.chaoxing.com" + url, headers=headers).text
    selector = etree.HTML(data)
    infos = ''
    if op == 0:
        infos = selector.xpath("//div[@class='units']//div[@class='leveltwo']//span[@class='articlename']/a/@href")  # 获取全部课程链接
    else:
        infos = selector.xpath("//div[@class='units'][" + str(op) + "]/div[@class='leveltwo']//span[@class='articlename']/a/@href")  # 获取单个单元课程链接
    chapter_list = list()
    if len(infos) >= 1:
        return False
    for info in infos:
        if info == '':
            return False
        re_data = re.search(r'chapterId=(\d+).*?courseId=(\d+).*?clazzid=(\d+)', info)   # 通过课程链接url获取需要的信息
        chapter_list.append({'chapterId': re_data[1], 'courseId': re_data[2], 'clazzId': re_data[3], 'url': info})

    return chapter_list


def force_get_all_chapter(cx_session, url, op=0):
    """
        强制获取所有章节id，即使章节被锁也可以获取（beta版）
        :param cx_session: session
        :param url: 课程链接
        :param op: 选项 0为全部获取，1-n为某单元
        :return: list 章节信息列表
    """
    match = re.search(r'courseId=(\d+).*?clazzid=(\d+)', url)  # 从url中获取课程id
    course_id = ''
    try:
        course_id = match[1]
        clazz_id = match[2]
    except KeyError:
        return False
    data = cx_session.get("https://mooc1-2.chaoxing.com/course/" + course_id + ".html", headers=headers).text
    selector = etree.HTML(data)
    infos = ''
    if op == 0:
        infos = selector.xpath("//div[@class='cell']//a[@class='wh wh1']/@href")  # 获取全部课程链接
    else:
        infos = selector.xpath("//div[@class='p20 btdwh btdwh1 fix'][" + str(op) + "]//ul[@class='mt10']//a[@class='wh wh1']/@href")  # 获取单个单元课程链接
    chapter_list = list()
    for info in infos:
        re_data = re.search(r'courseId=(\d+)&knowledgeId=(\d+)', info)  # 通过课程链接url获取需要的信息
        url = "/mycourse/studentstudy?chapterId=" + re_data[2] + "&courseId=" + re_data[1] + "&clazzid=" + clazz_id
        chapter_list.append({'chapterId': re_data[2], 'courseId': re_data[1], 'clazzId': clazz_id, 'url': url})
    pprint.pprint(chapter_list)
    return chapter_list


def get_all_objectid_by_json(cx_session, clazz_id, op):
    """
        获取某个单元所有下载objectid
        :param cx_session: session
        :param clazz_id: 课程链接
        :param op: 选项 0为全部获取，1-n为某单元
        :return: list objectid
    """
    print(clazz_id)
    # need_type = '.type(video)'
    need_type = ''
    url = 'http://mooc1-api.chaoxing.com/gas/clazz?id=' + clazz_id + '&fields=id,bbsid,classscore,allowdownload,isstart,chatid,name,state,isthirdaq,information,discuss,visiblescore,begindate,course.fields(id,infocontent,name,objectid,classscore,bulletformat,imageurl,privately,teacherfactor,unfinishedJobcount,jobcount,state,knowledge.fields(id,name,indexOrder,parentnodeid,status,layer,label,begintime,attachment.fields(id,type,objectid,extension,name)'+need_type+'))&view=json'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.17 Safari/537.36',
        'contentType': 'utf-8',
        'Accept-Language': 'zh_CN',
        'Host': 'mooc1-api.chaoxing.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    res = cx_session.get(url, headers=headers)
    info_json = json.loads(res.text)['data'][0]['course']['data'][0]['knowledge']['data']
    dl_list = list()
    for i in range(len(info_json)):
        if info_json[i]['label'][0:len(str(op))] == str(op):  # 仅要所选章节
            datas = info_json[i]['attachment']['data']
            for data in datas:
                try:
                    extension = data['extension']
                    object_id = data['objectid']
                    dl_list.append({
                        'ext': extension,
                        'id': object_id,
                    })
                except KeyError:
                    pass

    return dl_list


def get_download_info(cx_session, object_id_list, types):
    """
    获取下载文件的信息
    :param cx_session:
    :param objectid_list: 对象id列表
    :param types: 一个类型列表，如['mp4','pdf],全部则为all
    :return:
    """
    url = "https://mooc1-2.chaoxing.com/ananas/status/"
    dl_list = list()
    for object_id in object_id_list:
        print(object_id)
        res = cx_session.get(url+str(object_id['id']), headers=headers)
        print(res.text)
        dl_info = json.loads(res.text)
        filename = dl_info['filename']
        dl_link = dl_info['download']
        object_size = dl_info['length']
        extension = object_id['ext']
        if ('all' in types) or (extension in types):
            dl_list.append({
                    'id': str(object_id['id']),
                    'size': object_size,
                    'ext': extension,
                    'name': filename,
                    'link': dl_link
                })
    return dl_list


def get_all_chapter_link(cx_session, chapter_list, types):
    """
        获取所有章节的文件下载连接
        :param cx_session: session
        :param chapter_list: 章节列表
        :param types: 一个类型列表，如['mp4','pdf],全部则为all
        :return: list 所有下载路径信息
    """
    time.sleep(1.5)  # 这里延迟1.5秒避免被封
    all_dl_link = list()
    for item in chapter_list:
        links = get_one_chapter_link(cx_session, item['courseId'], item['clazzId'], item['chapterId'], types)  # 获取单课时的下载链接
        if not links:  # 如果本章无信息则跳过
            continue
        for link in links:
            all_dl_link.append(link)
    return all_dl_link


def get_one_chapter_link(cx_session, courseId, clazzid, knowledgeid, types):
    """
        获取单个章节的文件下载连接
        :param cx_session: session
        :param courseId: 课程id
        :param clazzid: 课室id
        :param knowledgeid: 知识点id，同chapterid
        :param types: 一个类型列表，如['mp4','pdf],全部则为all
        :return: list 下载路径
    """
    url = "https://mooc1-2.chaoxing.com/knowledge/cards"
    params = {
        'clazzid': clazzid,
        'courseid': courseId,
        'knowledgeid': knowledgeid,
        'num': '0',
        'ut': 's',
        'cpi': '0',
        'v': '20160407 - 1'
    }
    headers['Accept-Encoding'] = 'gzip, deflate, br'  # 不知道为什么不加encoding获取会失败，估计是它有检测
    data = cx_session.get(url, headers=headers, params=params).text
    match = re.search('"attachments":(.*?)]', data)
    if not match:
        return False
    data_dict = json.loads(match.group().replace('"attachments":', ""))  # 将获取到的json文本转为字典
    data_list = list()
    for item in data_dict:
        try:  # 发现部分内嵌图片只定义了objectid的跳过不下载，在这加个异常处理
            doc_type = item['type']
        except KeyError:
            continue
        if item['type'] == 'workid':  # 小测题目跳过下载
            continue
        object_id = item['property']['objectid']  # 下载地址依据此id
        object_hsize = item['property']['hsize']  # 以MB为单位的大小
        object_size = item['property']['size']
        extension = item['property']['type'].replace('.', '')
        object_name = item['property']['name']  # 根据数据中该文件名包括扩展名
        if ('all' in types) or (extension in types) or (doc_type in types):
            data_list.append({
                'type': doc_type,
                'id': object_id,
                'hsize': object_hsize,
                'size': object_size,
                'ext': extension,
                'name': object_name
            })
    return data_list


def download_file_mgr(cx_session, dl_list, dst='', op=0, idm=0):
    """
        下载文件管理者
        :param cx_session: session
        :param dl_list: 需要下载的课程列表
        :param dst: 保存的目录，仅为目录，不需要文件名
        :param op: 0不分开保存 1分扩展名保存
        :param idm: 0不使用idm下载 1使用idm下载
        :return: boolean 下载结果
    """
    '''此处预留多文件断点下载代码,先注释，因为懒所以先不做了'''
    # with open('downloadTemp.csv', "wt", newline="") as wf:
    #     writer = csv.writer(wf)
    #     writer.writerow(['type', 'id', 'hsize', 'size', 'ext', 'name'])
    #     for item in dl_list:
    #         writer.writerow([item['type'], item['id'], item['hsize'], item['size'], item['ext'], item['name']])

    url = "http://d0.ananas.chaoxing.com/download/"
    url_list = ''
    if dst != '' and (dst[:-1] != '/' or dst[:-1] != '\\'):
        dst = dst + '\\'
    if dst == '':
        dst = sys.path[0] + '\\download\\'
    if op == 1:  # 分目录保存
        url_list = [{'url': url + dl_list[i]['id'], 'dst': (dst + dl_list[i]['ext'] + '\\'), 'name': dl_list[i]['name'], 'size':  dl_list[i]['size']} for i in range(len(dl_list))]
    else:  # 不分目录保存
        url_list = [{'url': url + dl_list[i]['id'], 'dst': dst, 'name': dl_list[i]['name'], 'size': dl_list[i]['size']} for i in range(len(dl_list))]
    count = len(url_list)  # 用于计数
    if idm == 1:
        for dl in url_list:
            call([IDM_DIR, '/d', dl['url'], '/p', dl['dst'], '/f', dl['name'], '/n', '/a'])
        call([IDM_DIR, '/s'])
    else:
        for dl in url_list:
            count -= 1
            if not os.path.exists(dl['dst']):  # 创建对应目录
                os.makedirs(dl['dst'])
            print("\n正在下载第%d个【%s】  共%d个文件，还剩%d个文件，已下载完成%d个文件" % (len(url_list)-count, dl['name'], len(url_list), count, len(url_list)-count-1))
            if down_from_url(cx_session, dl['url'], dl['dst'] + dl['name'], dl['size']) == int(dl['size']):  # 下载文件
                print("\n下载完成第%d个【%s】\n"%(len(url_list)-count, dl['name']))
        print("\n已完成全部下载任务，下载根目录为%s\n" % dst)


def down_used_idm(idm_dir, url_list, save_dir):
    for ul in url_list:
        call([idm_dir, '/d', ul, '/p', save_dir, '/n', '/a'])
    call([idm_dir, '/s'])


def down_from_url(cx_session, url, dst, size):
    """
        单文件断点下载
        :param cx_session: session
        :param url: 下载地址
        :param dst: 存储路径
        :param size: 文件大小
        :return: int  返回文件大小
    """
    # 这两句不知道为啥获取出来的容量有问题的，用这个大小下载的文件打不开，可能官方为了反爬虫返回错误的大小
    # response = requests.get(url, stream=True, headers=hd)  # stream=True参数读取大文件
    # file_size = int(response.headers['content-length'])  # content-length属性获取文件的总容量
    file_size = int(size)  # 直接使用它json里面的文件大小
    if os.path.exists(dst):
        first_byte = os.path.getsize(dst)  # 获取本地已经下载的部分文件的容量
    else:
        first_byte = 0
    if first_byte >= file_size:
        return file_size
    header = {
        "Range": f"bytes={first_byte}-{file_size}",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.86 Safari/537.36"
    }
    p_bar = tqdm(total=file_size, initial=first_byte, unit='B', unit_scale=True, desc=dst)
    req = requests.get(url, headers=header, stream=True)  # 请求文件
    print(req)
    with open(dst, 'ab') as f:
        for chunk in req.iter_content(chunk_size=1024):  # 循环读取每次读取一个1024个字节
            if chunk:
                f.write(chunk)
                p_bar.update(1024)
    p_bar.close()
    return file_size


def user_select_func():
    """
        用于管理用户选项并调用对应程序以及生成用户选项菜单
    """
    err_time = 0  # 错误次数，错误超过三次则退出程序
    user_name = ""
    user_pwd = ""
    if not USERNAME and not PASSWD:  # 如果没设置全局变量则输入
        user_name = input("请输入用户名(学号)：")
        user_pwd = input("请输入密码：")
    else:
        user_name = USERNAME
        user_pwd = PASSWD
    code = input("请问是否输入校名？不输入则默认{广州商学院}【y/n】:")
    school = '广州商学院'
    while code not in ['y', 'Y', 'n', 'N']:
        err_time += 1
        if err_time > 3:
            return False
        print("输入错误，请重新输入\n")
        code = input("请问是否输入校名？不输入则默认{广州商学院}【y/n】:")
    if code == 'y' or code == 'Y':
        school = input('你的校名是：')
    # cx = login_cx(user_name, user_pwd, school)
    cx = login_cx_unv(user_name, user_pwd, school)  # 修改为免验证码登陆
    err_time = 0
    while not cx:
        err_time += 1
        if err_time > 3:
            return False
        print("登陆失败，请重新登陆")
        user_name = input("请输入用户名(学号)：")
        user_pwd = input("请输入密码：")
        # cx = login_cx(user_name, user_pwd, school)
        cx = login_cx_unv(user_name, user_pwd, school)  # 修改为免验证码登陆
    # 初始化信息
    course_list = ''
    unit_list = ''
    chapter_id_list = ''
    op = 1
    course_id = ''
    class_id = ''
    unit = ''
    course_url = ''
    # 死循环让用户选择，以达到返回目录的作用
    while 1:
        time.sleep(1)  # 这里延迟一秒避免被封
        if op == 1:  # 选项为1则输出课程名
            err_time = 0
            # 获取课程信息
            while course_list == '':  # 学生课程不存在才获取
                course_list = get_all_course(cx)
                if not course_list:
                    err_time += 1
                    if err_time > 3:
                        return False
                    print("获取学生课程失败")
                    continue
                else:
                    pass
            # 获取成功，输出信息
            for i, item in enumerate(course_list):
                print("【%d】%-20s" % (i + 1, item['name']), end='')
                if i % 4 == 0:
                    print('')
            print('【0】退出', end='')
            # 用户输入编号
            code = -1
            err_time = 0
            code = eval(input("\n请输入课程编号："))
            while code < 0 or code > len(course_list):
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入")
                code = eval(input("\n请输入课程编号："))
            if code == 0:
                return True
            else:
                # 对信息赋值，以便后面使用
                course_id = course_list[code-1]['course']
                class_id = course_list[code - 1]['class']
                course_url = course_list[code - 1]['url']
                op = 2
        elif op == 2 and course_id != '' and class_id != '' and course_url != '':  # 到达第二级，选择单元
            err_time = 0
            # 获取单元信息
            while unit_list == '':
                unit_list = get_all_chapter_title(cx, course_url, -1)
                if not unit_list:  # 获取不到再次尝试
                    err_time += 1
                    if err_time > 3:
                        return False
                    unit_list = get_all_chapter_title(cx, course_url, -1)
            # 获取成功
            for i, item in enumerate(unit_list):
                print("【%d】%-20s" % (i + 1, item), end='')
                if i % 4 == 0:
                    print('')
            print('【999】所有单元            【0】退出            【-1】返回上一级', end='')
            # 用户输入编号
            code = -2
            err_time = 0
            code = eval(input("\n请输入单元编号："))
            while code < -1 or code > len(unit_list):
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入")
                code = eval(input("\n请输入单元编号："))
            if code == 0:
                return True
            elif code == -1:
                op = 1
                course_id = ''
                class_id = ''
                course_url = ''
                continue  # 重置数据及循环使返回上一级
            else:  # 直接获取所有单元的数据，进入下一个op
                if code == 999:
                    flag = 0
                else:
                    flag = code
                # chapter_id_list = get_all_chapter(cx, course_url, flag)
                # print("开始获取单元数据")
                # force = 0
                # err_time = 0
                # while not chapter_id_list:
                #     err_time += 1
                #     if err_time > 3:
                #         code = input("请问是否尝试强制获取数据【y/n】：")
                #         err_time = 0
                #         while code not in ['y', 'Y', 'n', 'N']:
                #             err_time += 1
                #             if err_time > 3:
                #                 return False
                #             print("输入错误，请重新输入\n")
                #             code = input("请问是否指定文件下载路径【y/n】：")
                #         if code == 'y' or code == 'Y':
                #             force = 1
                #         else:
                #             return False  # 不强制获取则直接退出
                #         break
                #     chapter_id_list = get_all_chapter(cx, course_url, flag)
                #     print("获取单元数据失败，5秒后尝试再次获取")
                #     time.sleep(5)

                # force = 1
                #
                # if force == 1:  # 强制获取数据
                #     err_time = 0
                #     print("开始强制获取单元数据")
                #     chapter_id_list = force_get_all_chapter(cx, course_url, flag)
                #     while not chapter_id_list:
                #         err_time += 1
                #         if err_time > 3:
                #             return False
                #         chapter_id_list = force_get_all_chapter(cx, course_url, flag)
                #         print("强制获取单元数据失败，5秒后尝试再次获取")
                #         time.sleep(5)
                #     print("强制获取单元数据成功")
                # else:
                #     print("获取单元数据成功")

                force = 2
                if force == 2:  # 强制获取数据
                    err_time = 0
                    print("开始获取单元数据")
                    chapter_id_list = get_all_objectid_by_json(cx, class_id, flag)
                    while not chapter_id_list:
                        err_time += 1
                        if err_time > 3:
                            return False
                        chapter_id_list = get_all_objectid_by_json(cx, class_id, flag)
                        print("获取单元数据失败，5秒后尝试再次获取")
                        time.sleep(5)
                    print("获取单元数据成功")
                else:
                    print("获取单元数据成功")

                op = 3
        elif op == 3:  # 选择下载的类型

            code = input("请问是否指定文件类型，默认为所有类型【y/n】：")
            err_time = 0
            str_type = 'all'
            while code not in ['y', 'Y', 'n', 'N']:
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入\n")
                code = input("请问是否指定文件类型【y/n】:")
            if code == 'y' or code == 'Y':
                str_type = input('请输入你指定的类型以、分割，如：mp4、pdf ：')
            # 输入完成，开始分割
            types = list()
            if '、' in str_type:
                types = str_type.split('、')
            else:
                types.append(str_type)

            code = input("请问是否指定文件下载路径【y/n】：")
            dst = ''
            err_time = 0
            while code not in ['y', 'Y', 'n', 'N']:
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入\n")
                code = input("请问是否指定文件下载路径【y/n】：")
            if code == 'y' or code == 'Y':
                dst = input('请输入你指定的路径：')

            code = input("请问是否自动分类存放【y/n】：")
            class_fict = 0
            err_time = 0
            while code not in ['y', 'Y', 'n', 'N']:
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入\n")
                code = input("请问是否自动分类存放【y/n】：")
            if code == 'y' or code == 'Y':
                class_fict = 1

            # 获取所有下载地址信息
            print("共%d个课时，开始获取所有下载路径信息，预计用时%d秒" % (len(chapter_id_list), len(chapter_id_list) * 3))
            # all_dl_link = get_all_chapter_link(cx, chapter_id_list, types)
            all_dl_link = get_download_info(cx, chapter_id_list, types)
            err_time = 0
            while not all_dl_link:
                err_time += 1
                if err_time > 3:
                    return False
                all_dl_link = get_download_info(cx, chapter_id_list, types)
                print("获取获取所有下载路径失败，即将尝试再次获取")
            print("获取获取所有下载路径成功")

            # 判断是否使用idm
            code = input("请问是否使用idm下载【y/n】：")
            idm_dl = 0
            err_time = 0
            while code not in ['y', 'Y', 'n', 'N']:
                err_time += 1
                if err_time > 3:
                    return False
                print("输入错误，请重新输入\n")
                code = input("请问是否使用idm下载【y/n】：")
            if code == 'y' or code == 'Y':
                idm_dl = 1

            # 开始下载
            print('共%d个文件，即将开始下载' % len(all_dl_link))
            download_file_mgr(cx, all_dl_link, dst, class_fict, idm_dl)
            op = 1
            return False


if __name__ == '__main__':
    user_select_func()

    '''下面用于测试的，已注释'''
    # cx = login_cx("", "")
    # course_list = get_all_course(cx)
    # get_all_chapter(cx, course_list[len(course_list)-1]['url'])
    # data_list = get_one_chapter_link(cx, "207215442", "14459526", "275290728", ["mp4", "pdf"])
    # print(data_list)
    # chapter_list = force_get_all_chapter(cx, "/studentcourse?courseId=207215442&clazzid=14459526&vc=1&cpi=83039959&enc=7fced922a1fc1e5c4a67138050d1bd33", 2)
    # print(chapter_list)
    # link_list = get_all_chapter_link(cx, chapter_list,  ["mp4", "pdf"])
    # print(link_list)
    # download_file_mgr(cx, data_list, '', 1)
    # # get_one_chapter_link(cx, "207215442", "14459526", "216929258", ["mp4", "pdf"])
