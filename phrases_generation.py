import os
import pandas  as pd
import json
import re  
import gc
import jieba
import pickle
import string
import timeit
import jieba.posseg as pseg
from sklearn.decomposition import PCA
import numpy as np
import jieba.analyse
from time import time
from collections import defaultdict
from urllib import parse,request
from gensim import corpora, models, similarities
import gensim
import time
import math
from six import iteritems
from six.moves import xrange
from gensim import utils, matutils
from numpy import dot, zeros, ones, dtype, float32 as REAL, double, array
from collections import Counter

#读取数据
data = pd.read_excel('数据整理.xlsx', sheetname = None)
data_dict = data.to_dict(orient='records')

#语料预处理、分词
corpus = []
for i in data_dict:
    #提取时间
    nan = data_dict[1]['沟通时间']
    if i['沟通时间'] is not nan:
        time = str(i['沟通时间']).split(' ')[0]
        
    #句子分词
    sentences = [[tuple(p) for p in list(pseg.cut(sentence))] for sentence in re.split('，|；|,|；',i['句子'])]
    corpus.append((sentences, time))
    
#提取短语
max_n = 10
phrases = {}
for corpora in corpus:
    for sentence in corpora[0]:   
        for word_id, word_pair in enumerate(sentence):
            word = word_pair[0]
            pos = word_pair[1]
            if pos not in {'uj','x','uv','ul','c'}:
                for n in range(2, max_n+1):
                    try:
                        phrase = [(word,pos)]
                        valid = 1
                        for position in range(1,n):
                            phrase.append((sentence[word_id+position][0],sentence[word_id+position][1]))
                            if position == n-1:
                                if sentence[word_id+position][1] in {'uj','x','uv','ul','m','c','p'}:
                                    valid = 0
                        if valid is 1:
                            phrase_str = ''.join([w[0] for w in phrase])
                            if phrase_str not in phrases:
                                phrases[phrase_str] = (1, phrase, [corpora[1]])
                            else:
                                phrases[phrase_str] = (phrases[phrase_str][0]+1, phrase, phrases[phrase_str][2]+[corpora[1]])
                    except Exception as E:
                        #print(E)
                        pass
print('Finish generating phrases')

#筛选短语
phrases_cache = {}
for phrase in phrases:
    if phrases[phrase][0] > 1:
        if len(phrases[phrase][1]) >= 5:
            valid = 0
            for tag in phrases:
                if (phrase is not tag) and (phrase in tag):
                    valid = 1
            if valid is 0:
                phrases_cache[phrase] = phrases[phrase]
        else:
            phrases_cache[phrase] = phrases[phrase]
phrases = phrases_cache
print('Finish filtering phrases')
        
