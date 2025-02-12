# coding: UTF-8
# @Time        : 2018/5/15
# @Author      : Zhankui (Aaron) He
# @File        : Region.py
# @Description : Region Dictionary construction and Regions Detection

import pandas as pd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from qqwry import MQQWry

ID_NUM = 3
WORDPOOL = None
WORD2REGION = None
Q = MQQWry()

def _region_detect(row):
    """ 单句地域探测，由于需要用于多进程，故使用全局变量，写在Region Class外部

    :param row: 单句文本，数据格式：str
    :return: 探测的地域结果，数据格式：list, 数据尺寸:(1, ID_NUM)
    """
    global ID_NUM, WORDPOOL, WORD2REGION
    region_set = set([])
    for word in WORDPOOL:
        if row.find(word) != -1:
            for r in WORD2REGION[word]:
                region_set.add(r)
    r = [region for region in list(region_set)[:ID_NUM]]
    if len(r) < ID_NUM:
        r += [0 for _ in range(ID_NUM - len(r))]
    return r

# def _ip_detect(ip):
#     """ 单个ip明码地理位置探测，写在外部，用于Region Class多进程程序ip_detect()
#
#     :param ip: IP明码，数据格式:str
#     :return: 省份、城市信息，数据格式:tuple (省份，城市)
#     """
#     #淘宝IP地址库接口
#     r = requests.get('http://ip.taobao.com/service/getIpInfo.php?ip=%s' %ip)
#     if  r.json()['code'] == 0 :
#         i = r.json()['data']
#         provin = i['region']    #地区
#         city = i['city']        #城市
#
#         return (provin, city)

def _ip_detect(ip):
    res = Q[ip]
    region = res.country
    return (region[:2], region)


class Region(object):

    def __init__(self, path):
        """ 初始化Region类

        :param path: 地域字典的绝对路径
        """
        self.region2word = {}
        self.word2region = {}
        with open(path, "r") as f:
            for line in f:
                regions = line.strip().split("\t")
                self.region2word[regions[0]] = [r for r in regions]
                for r in regions:
                    if r not in self.word2region:
                        self.word2region[r] = [regions[0]]
                    else:
                        self.word2region[r].append(regions[0])
        self.wordPool = set(self.word2region.keys())

        global WORDPOOL, WORD2REGION
        WORDPOOL = self.wordPool
        WORD2REGION = self.word2region

    def region_detect(self, data, on, id_num = 3):
        """ 在dataFrame中批量添加region探测字段

        :param data: 输入的dataFrame，数据格式：dataFrame，如df_post
        :param on: dataFrame中探测的字段名，数据格式：list，如["post", "title"]
        :param id_num: 探测的region数量，未探测则为0，数据格式：int，默认为3
        :return: 返回已经添加了region探测字段的dataFrame
        """
        global ID_NUM
        ID_NUM = id_num

        rows = [" ".join([row[i] for i in on]) for _, row in data.iterrows()]

        pool = Pool(cpu_count())
        res = pool.map(_region_detect, tqdm(rows))
        pool.close()
        pool.join()

        data = pd.concat([data, pd.DataFrame(data = res, index=data.index, columns=["region_%d" % (i+1) for i in range(id_num)])], axis=1)
        return data

    def ip_detect(self, data, on, nbworker=cpu_count()):
        """ 在dataFrame中批量添加src探测字段

        :param data: 输入的dataFrame，数据格式：dataFrame，如df_post
        :param on: dataFrame中探测的字段名，数据格式：list，通常为["ip"]
        :return:  返回已经添加了src探测字段的dataFrame
        """
        rows = ["".join([str(row[i]) for i in on]) for _, row in data.iterrows()]

        if nbworker > 1:
            pool = Pool(nbworker)
            res = pool.map(_ip_detect, tqdm(rows))
            pool.close()
            pool.join()
        else:
            res = []
            for row in tqdm(rows):
                res.append(_ip_detect(row))

        data = pd.concat([data, pd.DataFrame(data=res, columns=["province", "city"], index=data.index)], axis=1)
        data.loc[data["province"]=="黑龙", "province"] = "黑龙江"
        data.loc[data["province"]=="内蒙", "province"] = "内蒙古"
        return data

if __name__ == "__main__":

    # 初始化Region Class
    path = "./Dict/region_dict/region.txt"
    r = Region(path)

    # 构造输入数据
    text = [
        ["潮汕人很帅，湖北人挺会做生意的！", "171.111.255.255"],
        ["老铁牛逼！", "171.111.255.255"],
        ["我觉得很好吃啊", "171.111.255.255"]
        ]
    df = pd.DataFrame(text, columns=["text", "ip"])
    print(df.head())

    # 单句地域探测
    print(_region_detect("老铁牛逼"))

    # dataFrame中批量添加region字段
    print(r.region_detect(df, on=["text"]))
    print(r.ip_detect(df, on=["ip"]))

    print(_ip_detect("202.104.15.102"))
