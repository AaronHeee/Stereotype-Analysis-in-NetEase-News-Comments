#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# @Time    : 2018/05/11 下午12:56
# @Author  : Shihan Ran
# @Site    :
# @File    : Sentiment.py
# @Software: PyCharm

import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count
import jieba


stop_words = [w.strip() for w in open('./Dict/notWord.txt', 'r', encoding='GBK').readlines()]
stop_words.extend(['\n','\t',' '])


def Sent2Word(sentence):
    """Turn a sentence into tokenized word list and remove stop-word

    Using jieba to tokenize Chinese.

    Args:
        sentence: A string.

    Returns:
        words: A tokenized word list.
    """
    global stop_words

    words = jieba.cut(sentence)
    words = [w for w in words if w not in stop_words]

    return words


def LoadDict():
    """Load Dict form disk

    Returns:
        pos_dict: positive word dict, with word and their extent, for example:
            {'good':5,'awesome':7,...} which means awasome is more positive than good.
            The extent is between 1 and 10.
        neg_dict: negative word dict
        not_dict: not word dict
        degree_dict: degree word dict
    """
    # Sentiment word
    pos_words = open('./Dict/pos_word.txt').readlines()
    pos_dict = {}
    for w in pos_words:
        word, score = w.strip().split(',')
        pos_dict[word] = float(score)

    neg_words = open('./Dict/neg_word.txt').readlines()
    neg_dict = {}
    for w in neg_words:
        word, score = w.strip().split(',')
        neg_dict[word] = float(score)

    Boson = open('./Dict/BosonNLP_sentiment_score.txt', 'r').readlines()
    for w in Boson:
        word, score = w.strip().split(' ')
        if float(score) > 0:
            pos_dict[word] = float(score)
        else:
            neg_dict[word] = float(score)

    # Not word ['不', '没', '无', '非', '莫', '弗', '勿', '毋', '未', '否', '别', '無', '休', '难道']
    not_words = open('./Dict/notDict.txt').readlines()
    not_dict = {}
    for w in not_words:
        word = w.strip()
        not_dict[word] = float(-1)

    # Degree word {'百分之百': 10.0, '倍加': 10.0, ...}
    degree_words = open('./Dict/degreeDict.txt').readlines()
    degree_dict = {}
    for w in degree_words:
        word, score = w.strip().split(',')
        degree_dict[word] = float(score)

    return pos_dict, neg_dict, not_dict, degree_dict


pos_dict, neg_dict, not_dict, degree_dict = LoadDict()


def LocateSpecialWord(pos_dict, neg_dict, not_dict, degree_dict, words):
    """Find the location of Sentiment words, Not words, and Degree words

    The idea is pretty much naive, iterate every word to find the location of Sentiment words,
    Not words, and Degree words, additionally, storing the index into corresponding arrays
    SentiLoc, NotLoc, DegreeLoc.

    Args:
        pos_dict: positive word dict, with word and their extent, for example:
            {'good':5,'awesome':7,...} which means awasome is more positive than good.
            The extent is between 1 and 10.
        neg_dict: negative word dict
        not_dict: not word dict
        degree_dict: degree word dict
        words: The tokenized word list.

    Returns:
        pos_word: positive word location dict, with word and their location in the sentence, for example:
                {'good':1,'awesome':11,...}
        neg_word: negative word dict
        not_word: not word location dict
        degree_word: degree word location dict
    """
    # pos_word = {}
    # neg_word = {}
    # not_word = {}
    # degree_word = {}

    pos_word = []
    neg_word = []
    not_word = []
    degree_word = []

    for index, word in enumerate(words):
        if word in pos_dict:
            # pos_word[index] = pos_dict[word]
            pos_word.append(word)
        elif word in neg_dict:
            # neg_word[index] = neg_dict[word]
            neg_word.append(word)
        elif word in not_dict:
            # not_word[index] = -1
            not_word.append(word)
        elif word in degree_dict:
            # degree_word[index] = degree_dict[word]
            degree_word.append(word)

    return pos_word, neg_word, not_word, degree_word


def ScoreSent(pos_word, neg_word, not_word, degree_word, words):
    """Compute the sentiment score of this sentence

    Iterate each word, the Score can be computed as
    Score = Score + W * (SentiDict[word]), where W is the weight depends on
    Not words and Degree words, SentiDict[word] is the labeled extent number of sentiment word.
    When we are doing our iteration, W should change when there exists Not words or Degree words
    between one sentiment word and next sentiment word.

    Args:
        pos_word: positive word location dict, with word and their location in the sentence, for example:
                {'good':1,'awesome':11,...}
        neg_word: negative word dict
        not_word: not word location dict
        degree_word: degree word location dict
        words: The tokenized word list.

    Returns:
        score: The sign of sentiment score, +1 or -1
    """
    W = 1
    score = 0

    # The location of sentiment words
    pos_locs = list(pos_word.keys())
    neg_locs = list(neg_word.keys())
    not_locs = list(not_word.keys())
    degree_locs = list(degree_word.keys())

    posloc = -1  # How many words you've detected
    negloc = -1

    # iterate every word, i is the word index ("location")
    for i in range(0, len(words)):
        # if the word is positive
        if i in pos_locs:
            posloc += 1
            # update sentiment score
            score += W * float(pos_word[i])

            if posloc < len(pos_locs)-1:
                # if there exists Not words or Degree words between
                # this sentiment word and next sentiment word
                # j is the word index ("location")
                for j in range(pos_locs[posloc], pos_locs[posloc+1]):
                    # if there exists Not words
                    if j in not_locs:
                       W *= -1
                    # if there exists degree words
                    elif j in degree_locs:
                       W *= degree_word[j]
                    # else:
                    #     W *= 1

        # if the word is negative
        elif i in neg_locs:
            negloc += 1
            score += (-1) * W * float(neg_word[i])

            if negloc < len(neg_locs) - 1:
               for j in range(neg_locs[negloc], neg_locs[negloc + 1]):
                  if j in not_locs:
                     W *= -1
                  elif j in degree_locs:
                     W *= degree_word[j]
                  # else:
                  #     W = 1

    # print(numpy.sign(score)*numpy.log(abs(score)))
    return np.sign(score)

def SentiFeatures(text):
    """To find the sentiment score of news corresponding to a stock

    Retrieves rows pertaining to the given keys from the Table instance
    represented by big_table.  Silly things may happen if
    other_silly_variable is not None.

    Args:
        text: An string.

    Returns:
        text_score: Compute the average sentiment score of text
        PosWord: The number of positive words in text
        NegWord: The number of negative words in text
    """

    global pos_dict, neg_dict, not_dict, degree_dict

    words = Sent2Word(text)
    pos_word, neg_word, not_word, degree_word = LocateSpecialWord(pos_dict, neg_dict, not_dict, degree_dict, words)
    # text_score = ScoreSent(pos_word, neg_word, not_word, degree_word, words)

    PosWord = len(pos_word)
    NegWord = len(neg_word)

    text_score = 1 if PosWord > NegWord else -1

    return text_score, PosWord, NegWord, pos_word, neg_word

class Sentiment(object):

    def __init__(self):
        self.record = {}

    def add_word(self, src, dist, polar, word):
        key = (src, dist, polar)
        if key in self.record:
            if word in self.record[key]:
                self.record[key][word] += 1
            else:
                self.record[key][word] = 1
        else:
            self.record[key] = {word: 1}

    def reset_record(self):
        self.record = {}

    def output_record(self, src=None, dist=None, polar=None):
        if src is not None and dist is None:
            for key in self.record.keys():
                if src == key[0]:
                    for word in self.record[key].keys():
                        print("%s ==> %s - sentiment %2d -- word %s -- frequency %d" % (src, key[1], key[2], word, self.record[key][word]) )

    def table_record(self):
        """ 将 self.record 字典作为DataFrame表返回

        :return: 字段为src, dist, polar, word, freq的DataFrame表格，字段含义依次为：
            用户所在地、用户评论目的地、评论情感极性、情感词、词频
        """
        res = []
        for key in self.record.keys():
            for word in self.record[key].keys():
                freq = self.record[key][word]
                res.append([key[0], key[1], key[2], word, freq])
        return pd.DataFrame(res, columns=["src", "dist", "polar", "word", "freq"])

    def sentiment_detect(self, data, on, srcs=None, dists=None):

        """ 在dataFrame中批量添加"polar", "pos-words", "neg-words"字段

        分别代表该条评论的情感极性、正向词汇个数、反向词汇个数
        另外维护一个本地成员self.record，用来记录src->dist的评价词汇词频

        :param data: 输入的dataFrame，数据格式：dataFrame，如df_post
        :param on: dataFrame中探测的字段名，数据格式：list，通常为["content"]
        :param srcs: dataFrame中表示评论用户所在地的字段名，数据格式：list,通常为["src"]
        :param dists: dataFrame中表示被评论地区的字段名，数据格式：list,通常为["region_1", "region_2",...]
        :return:  返回已经添加了polar, pos-words, neg-words探测字段的dataFrame
        """

        rows = [" ".join([row[i] for i in on]) for _, row in data.iterrows()]

        pool = Pool(cpu_count())
        results = pool.map(SentiFeatures, rows)
        pool.close()
        pool.join()

        res = []
        for i, (_, row) in enumerate(data.iterrows()):
            res.append(results[i][:3])

            if (srcs and dists) is not None:
                for s in srcs:
                    src = row[s]
                    for r in results[i][3]:
                        for d in dists:
                            dist = row[d]
                            if dist:
                                self.add_word(src, dist, 1, r)

                    for r in results[i][4]:
                        for d in dists:
                            dist = row[d]
                            if dist:
                                self.add_word(src, dist, -1, r)

        data = pd.concat([data, pd.DataFrame(data = res, index=data.index, columns=["polar", "pos-words", "neg-words"])], axis=1)

        return data