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
import numpy as np
import jieba.analyse
from time import time
from gensim import corpora, models, similarities
import gensim
import time
import math
from gensim import utils, matutils
from numpy import dot, zeros, ones, dtype, float32 as REAL, double, array
from collections import Counter

#读取数据
data = pd.read_excel('数据整理0312.xlsx', sheetname ='Sheet1',header = 1)
data.columns = ['沟通时间','沟通内容','句子','dovish','neutral','hawkish', 'positive','static','negative', 'none', 'n-gram', 'frequence'] 
data = data.fillna(value='NA')
data_dict = data.to_dict(orient='records')

#语料预处理、分词
corpus = []
lookup = {'dovish':[],'neutral':[],'hawkish':[], 'positive':[],'static':[],'negative':[], 'none':[]}
for index, i in enumerate(data_dict):
    #提取时间
    if i['沟通时间'] != 'NA':
        time = str(i['沟通时间']).split(' ')[0]
        
    #句子分词
    sentences = [[tuple(p) for p in list(pseg.cut(sentence))] for sentence in re.split('，|；|,|；',i['句子'])]
    
    #态度
    altitude_category = {'dovish':0,'neutral':0,'hawkish':0, 'positive':0,'static':0,'negative':0, 'none':0}
    for tag in ['dovish','neutral','hawkish', 'positive','static','negative', 'none']:
        if i[tag] != 'NA':
            lookup[tag].append(index)
            altitude_category[tag] += 1
            
    corpus.append((sentences, time, altitude_category))
    
#提取短语
max_n = 20
phrases = {}
for line_id, corpora in enumerate(corpus):
    time = corpora[1]
    category = corpora[2]
    #print(category)
    for sentence in corpora[0]:   
        for word_id, word_pair in enumerate(sentence):
            word = word_pair[0]
            pos = word_pair[1]
            if (len(word) >= 3) and\
               (pos not in 'm'):
                if word not in phrases:
                    phrases[word] = [1, [word_pair], [time], category.copy()]
                else:
                    phrases[word][0] += 1
                    phrases[word][2].append(time)
                    for tag in category:
                        phrases[word][3][tag] += category[tag]
            if (pos not in {'uj','x','uv','ul','c','u'}) and\
               (word not in {'将','从','这次','到','中','上'}):
                for n in range(2, max_n+1):
                    try:
                        phrase = [(word,pos)]
                        valid = 1
                        for position in range(1,n):
                            phrase.append((sentence[word_id+position][0],sentence[word_id+position][1]))
                            if position == n-1:
                                if sentence[word_id+position][1] in {'uj','uv','ul','m','c','p','zg','r','d'} or\
                                   sentence[word_id+position][0] in {'是','会','有','要','。','、','“','”','？'}:
                                    valid = 0
                        if valid is 1:
                            phrase_str = ''.join([w[0] for w in phrase])
                            if phrase_str not in phrases:
                                phrases[phrase_str] = [1, phrase, [time], category.copy()]
                            else:
                                phrases[phrase_str][0] += 1
                                phrases[phrase_str][2].append(time)
                                for tag in category:
                                    phrases[phrase_str][3][tag] += category[tag]
                    except Exception as E:
                        #print(E)
                        pass
print('Finish generating phrases, phrases amount: %2d' % len(phrases))

phrases_cache = {}
for idx, phrase in enumerate(phrases):
    if phrases[phrase][0] >= 2:
        valid = 1
        if len(phrases[phrase][1]) >= 5: 
            for tag in phrases:
                if (phrase is not tag) and (phrase in tag) and (len(set(phrases[phrase][1])&set(phrases[tag][1])) != len(set(phrases[phrase][1])) - 1):
                    valid = 0
        
        else:
            for tag in phrases:
                if len(phrases[tag][1]) >= 5:
                    if (phrase is not tag) and (phrase in tag):
                        if (phrases[phrase][0] == phrases[tag][0]) and (phrases[phrase][0] <= 3):
                            valid = 0
        #                #print(phrase, tag)
        
        if valid is 1:
            phrases_cache[phrase] = phrases[phrase]
    if idx % 1000 == 0:
        print(idx)
phrases = phrases_cache
print('Finish filtering phrases, remaining phrases amount: %2d' % len(phrases))

#统计
MP = {'dovish','neutral','hawkish'}
EC = {'positive','static','negative'}
phrases_lookup = {}
MPEC_lookup = {'dovish':[],'neutral':[],'hawkish':[],'positive':[],'static':[],'negative':[]}
MP_lookup = {}
for phrase in phrases:
    for tag in MPEC_lookup:
        prob = phrases[phrase][3][tag] / phrases[phrase][0]
        if prob > 0.5:
            MPEC_lookup[tag].append(phrase)
            if phrase not in phrases_lookup:
                phrases_lookup[phrase] = [tag]
            else:
                phrases_lookup[phrase].append(tag)
#构建表格
chart = []
for phrase in phrases:
    content = phrases[phrase]
    line = [phrase, content[0],content[-1]]
    chart.append(line)
df = pd.DataFrame(chart)
df.columns = ['短语','合计出现次数','出现时间']
df.to_csv('短语统计0312.csv',encoding='gbk')
        
