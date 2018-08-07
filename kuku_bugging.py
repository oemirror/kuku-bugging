# coding: utf-8

from bs4 import BeautifulSoup
import requests
import urllib
import re
import os
import shutil
import time
import json



D_PATH = os.path.join(os.path.abspath("."),"img")   #本地保存目录
C_SERVER = "http://comic.kukudm.com/" #应用服务器地址
P_SERVER = "http://n.1whour.com/"   #图片服务器地址，会变！

OVERWRITE_FLAG = True   #文件名冲突是否覆盖
RETRY_COUNT = 10   # 重试次数
RETRY_TIME_WAIT=1 #重试等待时间

GET_INFO_TYPE = "INFO" # INFO ： 更新资源最新页号    IMG  ：下载资源

PAGE_MIN = 0  #页面编号 最小值
PAGE_MAX = 0  #页面编号 最大值
DOWN_COMIC = "HUNTER"
COMIC_LIST = {}

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
    response = requests.get(targetUrl)
#     if response.status_code == 200:
#         print("HTML SUCCESS")
#     else:
#         print("HTML ERROR")
#         print(response)
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
        print(comic_info)
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
def getComic(html, get_info_type):
    soup = BeautifulSoup(html.text,'lxml')
    cDds = soup.find_all('dd')
        
    for cDd in cDds:
        tmp = cDd.contents[2]
        cTitle = cDd.contents[0].text
        cHref = tmp["href"]
        cU = int(cHref.split("/")[-2])
        if cU > PAGE_MIN and cU <= PAGE_MAX :
            print(cTitle)
            dirName = makeDir(cTitle)
            while True :
#                 print(cHref)
                nextFlag,cHref = getImg(cHref,dirName)
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
    print("imgurl : " +imgurl + " ====> fileName :  " + fileName)
    err_cnt = 0
    while True and err_cnt < RETRY_COUNT:
        try :
            urllib.request.urlretrieve(imgurl, fileName) # 下载图片    
            break            
        except Exception as e :
            if err_cnt <= RETRY_COUNT : 
                err_cnt += 1
                print("[RETRY] DOWNLOAD <" +imgurl+"> FAIL! RETRY NOW  " +str(err_cnt)+" . ")        
                time.sleep(RETRY_TIME_WAIT)
            else :
                print("[ERROR] DOWNLOAD <" +imgurl+"> FAIL!")                    
                print(e)

# 获取图片地址
def getImg(cHref,dirName):
    html = getHtml(cHref)
    nextFlag = True #是否有下一页
    # 正则获取图片地址
    reg = r'SRC=\'(.+?\.jpg)\''
    imgre = re.compile(reg)
    imglist = imgre.findall(html.text)
    # print(imglist)    
    imgurl = imglist[0];
    imgurl = imgurl.split("+")[-1][1:]  #针对动态JS拼接的URL 做处理
    # 下载图片
    imgurl = P_SERVER+imgurl  #截取变量部分替换为 图片服务器地址
    fileName = os.path.join(dirName,imgurl.split("/")[-1])
    makeFile(imgurl,fileName)
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
    print("zip file success !")    
    
def unpack_archive(cTitle):
    zipfilename = os.path.join(D_PATH,cTitle+'.zip')
    print(zipfilename)
    flag = os.path.exists(zipfilename)
    print(flag)
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
    print("ALL END!!!")

