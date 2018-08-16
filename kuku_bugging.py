# coding: utf-8

from bs4 import BeautifulSoup
import requests
import urllib
import re
import os
import shutil
import time
import json
import logging


D_PATH = os.path.join(os.path.abspath("."),"img")   #本地保存目录
C_SERVER = "http://comic.kukudm.com/" #应用服务器地址
P_SERVER = "http://n.1whour.com/"   #图片服务器地址，会变！

OVERWRITE_FLAG = True   #文件名冲突是否覆盖
RETRY_COUNT = 10   # 重试次数
RETRY_TIME_WAIT=1 #重试等待时间

GET_INFO_TYPE = "IMG" # INFO ： 更新资源最新页号    IMG  ：下载资源

PAGE_MIN = 0  #页面编号 最小值
PAGE_MAX = 0  #页面编号 最大值
DOWN_COMIC = "HZW"  #下载资源TAG
COMIC_LIST = {}

logger = logging.getLogger(__name__)
logger.setLevel(level = logging.INFO)
handler = logging.FileHandler("log_kuku_bugging.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console = logging.StreamHandler()
logger.addHandler(handler)
logger.addHandler(console)

"""
{"HZW": {"url": "http://comic2.kukudm.com/comiclist/4/index.htm", "page_min": 0, "page_max": 64716,"desc":"海贼王"}, 
"GIANT": {"url": "http://comic2.kukudm.com/comiclist/2359/index.htm", "page_min": 0, "page_max": 64424,"desc":"GIANT"},
 "HUNTER": {"url": "http://comic2.kukudm.com/comiclist/146/index.htm", "page_min": 58889, "page_max": 64496,"desc":"猎人"}, 
 "GQW": {"url": "http://comic.kukudm.com/comiclist/380/index.htm", "page_min": 0, "page_max": 11256,"desc":"滚球王"},
 "JOJO": {"url": "http://comic.kukudm.com/comiclist/1312/index.htm", "page_min": 0, "page_max": 64404,"desc":"JOJO第七季"},
 "YW": {"url": "http://comic.kukudm.com/comiclist/346/index.htm", "page_min": 0, "page_max": 64502,"desc":"妖尾"}, 
 "HFLY": {"url": "http://comic.kukudm.com/comiclist/2039/index.htm", "page_min": 0, "page_max": 64755,"desc":"火凤燎原"}}
"""

# 模拟浏览器
def getHtml(targetUrl):
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = {'User-Agent': user_agent}
    err_cnt = 0
    while True and err_cnt < RETRY_COUNT:
        try :
            response = requests.get(targetUrl)   
            break            
        except Exception as e :
            if err_cnt <= RETRY_COUNT : 
                err_cnt += 1
                logger.info("[RETRY] REQUEST GET <" +targetUrl+"> FAIL! RETRY NOW  " +str(err_cnt)+" . ")        
                time.sleep(RETRY_TIME_WAIT)
            else :
                logger.info("[ERROR] REQUEST GET <" +targetUrl+"> FAIL!")                    
                logger.info(e)    
        
#     if response.status_code == 200:
#         logger.info("HTML SUCCESS")
#     else:
#         logger.info("HTML ERROR")
#         logger.info(response)
    response.encoding='gbk'  
    html = response
    return html

# 下载全部图片，暂时不用
def getAllImg(html):
    reg = r'src="(.+?\.jpg)"'
    imgre = re.compile(reg)
    imglist = imgre.findall(html.text)
    x = 0
    for imgurl in imglist:
        imgurl = "http:"+imgurl
        #通过urlretrieve函数把数据下载到本地的D:\\images，所以你需要创建目录
        urllib.request.urlretrieve(imgurl, os.path.join(D_PATH,"%s.jpg") % x)
        x = x + 1


# 创建目录
def makeDir(fileName):
    dirName = os.path.join(D_PATH,fileName)
    if not os.path.isdir(dirName):
        os.mkdir(dirName)
    return dirName


# 更新ComicList.json文件
def getComicInfo():
    for comic_name in COMIC_LIST:
        comic_info = COMIC_LIST[comic_name]
        logger.info(comic_info)
        targetUrl = comic_info["url"]
        html = getHtml(targetUrl)

        soup = BeautifulSoup(html.text,'lxml')
        cDds = soup.find_all('dd')
        cDd = cDds[-1]
        tmp = cDd.contents[2]
        cHref = tmp["href"]
        cU = int(cHref.split("/")[-2])
        COMIC_LIST[comic_name]["page_max"] = cU       
    dict_to_json_write_file()      
                        
# 获取资源地址
def getComic(html,):
    soup = BeautifulSoup(html.text,'lxml')
    cDds = soup.find_all('dd')
    for cDd in cDds:
        tmp = cDd.contents[2]
        cTitle = cDd.contents[0].text.replace(":","")
        cHref = tmp["href"]
        cU = int(cHref.split("/")[-2])
        if cU > PAGE_MIN and cU <= PAGE_MAX :
            logger.info(cTitle)
            idx = 0
            dirName = makeDir(cTitle)
            while True :
#                 logger.info(cHref)
                idx += 1 
                nextFlag,cHref = getImg(cHref,dirName,cU,idx)
                if not nextFlag:
                    make_archive(cTitle)            
                    COMIC_LIST[DOWN_COMIC]["page_min"] = cU
                    dict_to_json_write_file()    
                    break

# 下载文件                    
def makeFile(imgurl,fileName):
    if not OVERWRITE_FLAG and os.path.isfile(fileName):
        fileName = fileName[:-4]+"_n."+fileName.split(".")[-1]  #重名图片 加后缀 _n
    imgurl=urllib.parse.quote(imgurl,safe='/:?=.') # 中文字符转换
    logger.info("imgurl : " +imgurl + " ====> fileName :  " + fileName)
    err_cnt = 0
    while True and err_cnt < RETRY_COUNT:
        try :
            urllib.request.urlretrieve(imgurl, fileName) # 下载图片    
            break            
        except Exception as e :
            if err_cnt <= RETRY_COUNT : 
                err_cnt += 1
                logger.info("[RETRY] DOWNLOAD <" +imgurl+"> FAIL! RETRY NOW  " +str(err_cnt)+" . ")        
                time.sleep(RETRY_TIME_WAIT)
            else :
                logger.info("[ERROR] DOWNLOAD <" +imgurl+"> FAIL!")                    
                logger.info(e)

# 流式下载文件
def makeFileStream(imgurl,fileName):
    requests.packages.urllib3.disable_warnings()
    if not OVERWRITE_FLAG and os.path.isfile(fileName):
        fileName = fileName[:-4]+"_n."+fileName.split(".")[-1]  #重名图片 加后缀 _n
    imgurl=urllib.parse.quote(imgurl,safe='/:?=.') # 中文字符转换
    logger.info("imgurl : " +imgurl + " ====> fileName :  " + fileName)
    err_cnt = 0
    while True and err_cnt < RETRY_COUNT:
        try :
            file_size = -1 #文件总大小
            requests.packages.urllib3.disable_warnings()
            while True:
                lsize = get_local_file_exists_size(fileName)
                r1 = requests.get(imgurl, stream=True, verify=False)
                file_size = int(r1.headers['Content-Length'])
                logger.info("lsize : %s ,  file_size : %s ",lsize,file_size)
                if lsize == file_size:
                    break
                webPage = get_file_obj(imgurl, lsize)
                try:
                    file_obj = open(fileName, 'ab+')
                except Exception as e:
                    logger.info("打开文件: %s 失败", fileName )
                    break
                try:
                    for chunk in webPage.iter_content(chunk_size=10 *1024):
                        if chunk:
                            lsize = get_local_file_exists_size(fileName)
                            file_obj.write(chunk)
                        else:
                            break
                except Exception as e:
                    time.sleep(RETRY_TIME_WAIT)
                file_obj.close()
                webPage.close()
    
            break            
        except Exception as e :
            if err_cnt <= RETRY_COUNT : 
                err_cnt += 1
                logger.info("[RETRY] DOWNLOAD <" +imgurl+"> FAIL! RETRY NOW  " +str(err_cnt)+" . ")        
                time.sleep(RETRY_TIME_WAIT)
            else :
                logger.info("[ERROR] DOWNLOAD <" +imgurl+"> FAIL!")                    
                logger.info(e)

# 获取当前文件大小
def get_local_file_exists_size(local_path):
    try:
        lsize = os.stat(local_path).st_size
    except:
        lsize = 0
    return lsize
 
# 流式下载文件 
def get_file_obj(down_link, offset):
    webPage = None
    try:
        headers = {'Range': 'bytes=%d-' % offset}
        # logger.info(headers)
        webPage = requests.get(down_link, stream=True, headers=headers, timeout=120, verify=False)
        status_code = webPage.status_code
        if status_code in [200, 206]:
            webPage = webPage
        elif status_code == 416:
            logger.info("文件数据请求区间错误 : %s , status_code : %s ",down_link, status_code)
        else:
            logger.info("链接有误: %s ，status_code ：%s", down_link, status_code)
    except Exception as e:
        logger.info("无法链接 ：%s , exception : %s",down_link, e)
    finally:
        return webPage

# 获取图片地址
def getImg(cHref,dirName,cU,idx):
    html = getHtml(cHref)
    nextFlag = True #是否有下一页
    # 正则获取图片地址
    reg = r'SRC=\'(.+?)\''
    #正则表达式 不区分大小写
    # imgre = re.compile(reg,flags=re.IGNORECASE)
    imgre = re.compile(reg)
    imglist = imgre.findall(html.text)
    # logger.info(imglist)    
    imgurl = imglist[0];
    imgurl = imgurl.split("+")[-1][1:]  #针对动态JS拼接的URL 做处理
    # 下载图片
    imgurl = P_SERVER+imgurl  #截取变量部分替换为 图片服务器地址
    fileName = DOWN_COMIC+"_"+str(cU)+"_"+("%03d" % idx)+".jpg"
    fileName = os.path.join(dirName,fileName)
    # fileName = os.path.join(dirName,imgurl.split("/")[-1])
    makeFile(imgurl,fileName)
    # makeFileStream(imgurl,fileName)
    #是否有下一页判断
    soup = BeautifulSoup(html.text,'lxml')
    aObj = soup.find('img',attrs={"src":"/images/d.gif"}).parent
    if aObj["href"] == "/exit/exit.htm": #没有下一页就停止循环
        nextFlag = False
    if nextFlag:
        imgurl = C_SERVER+aObj["href"]
    return nextFlag,imgurl

# 压缩/解压
def make_archive(cTitle):
    comicDir = os.path.join(D_PATH,cTitle,".")
    shutil.make_archive(comicDir,'zip',comicDir)
    shutil.rmtree(comicDir)
    logger.info("zip file success !")    
    
def unpack_archive(cTitle):
    zipfilename = os.path.join(D_PATH,cTitle+'.zip')
    logger.info(zipfilename)
    flag = os.path.exists(zipfilename)
    logger.info(flag)
    if flag :
        shutil.unpack_archive(zipfilename,os.path.join(D_PATH,'.'+cTitle))
    return flag

# JSON
def json_file_to_dict():
    with open('COMIC_LIST.json', 'r', encoding='utf-8') as f:
        dict = json.load(fp=f)
        return dict        
        
def dict_to_json_write_file():
    with open('COMIC_LIST.json', 'w', encoding='utf-8') as f:
        json.dump(COMIC_LIST, f)  
    
    
    
if __name__ == '__main__':    
    COMIC_LIST = json_file_to_dict()
    if GET_INFO_TYPE == "INFO":
        getComicInfo()
    elif GET_INFO_TYPE == "IMG":
        comic_info = COMIC_LIST[DOWN_COMIC]
        targetUrl = comic_info["url"]
        PAGE_MIN = comic_info["page_min"]
        PAGE_MAX = comic_info["page_max"]
        html = getHtml(targetUrl)
        getComic(html)
    logger.info("ALL END!!!")

