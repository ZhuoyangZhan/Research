import os
import pandas  as pd
import json
import re  
import gc
import jieba
import pickle
import jieba.posseg as pseg
import numpy as np
import jieba.analyse
import gensim
import time
import math

data = pd.read_excel('数据整理0319.xlsx', sheetname ='Sheet1',header = 1)
data.columns = ['沟通时间','沟通内容','句子','dovish','neutral','hawkish', 'positive','static','negative', 'none'] 
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
            if (len(word) >= 2) and\
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

#过滤短语
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
        print('Checked: %2s' % idx)
phrases = phrases_cache
print('Finish filtering phrases, remaining phrases amount: %2d' % len(phrases))

#统计短语属性
MP = {'dovish','neutral','hawkish'}
EC = {'positive','static','negative'}
phrases_lookup = {}
MPEC_lookup = {'dovish':[],'neutral':[],'hawkish':[],'positive':[],'static':[],'negative':[]}
MP_lookup = {}
count = 0
for phrase in phrases:
    for tag in MPEC_lookup:
        prob = phrases[phrase][3][tag] / phrases[phrase][0]
        if prob > 0.5:
            count += 1
            MPEC_lookup[tag].append(phrase)
            if phrase not in phrases_lookup:
                phrases_lookup[phrase] = [tag]
            else:
                phrases_lookup[phrase].append(tag)
print('Remained words with inclination: %2s' % count)


#统计演讲属性
speech = {}
for phrase in phrases:
    if phrase in phrases_lookup:
        dates = phrases[phrase][2]
        inclination = phrases_lookup[phrase]
        for date in dates:
            if date not in speech:
                speech[date] = {'MP':{'dovish':{},'neutral':{},'hawkish':{}},\
                                'EC':{'positive':{},'static':{},'negative':{}}}
                for tag in inclination:
                    if tag in MP:
                        if phrase not in speech[date]['MP'][tag]:
                            speech[date]['MP'][tag][phrase] = 1
                        else :
                            speech[date]['MP'][tag][phrase] += 1
                    else:
                        if phrase not in speech[date]['EC'][tag]:
                            speech[date]['EC'][tag][phrase] = 1
                        else :
                            speech[date]['EC'][tag][phrase] += 1

            else:
                for tag in inclination:
                    if tag in MP:
                        if phrase not in speech[date]['MP'][tag]:
                            speech[date]['MP'][tag][phrase] = 1
                        else :
                            speech[date]['MP'][tag][phrase] += 1
                    else:
                        if phrase not in speech[date]['EC'][tag]:
                            speech[date]['EC'][tag][phrase] = 1
                        else :
                            speech[date]['EC'][tag][phrase] += 1
                            
#计算指数
indicator = {}
for date in speech:
    MP_ = speech[date]['MP']
    EC_ = speech[date]['EC']
    all_phrases = list(MP_['dovish'].keys())+list(MP_['neutral'].keys())+list(MP_['hawkish'].keys())+\
                  list(EC_['positive'].keys())+list(EC_['static'].keys())+list(EC_['negative'].keys())
    chosen_phrase = []
    chosen_phrase_dict  = {'dovish':[],'neutral':[],'hawkish':[],'positive':[],'static':[],'negative':[]}
    for phrase in all_phrases:
        valid = 1
        for word in all_phrases:
            if (phrase in word) and (phrase != word):
                valid = 0
        if valid == 1:
            chosen_phrase.append(phrase)
            
    P_MP = {'dovish':0,'neutral':0,'hawkish':0}
    P_EC = {'positive':0,'static':0,'negative':0}
    for phrase in chosen_phrase:
        belong_tag = phrases_lookup[phrase][0]
        chosen_phrase_dict[belong_tag] = phrase
        if belong_tag in MP:
            prob = phrases[phrase][-1][belong_tag]/phrases[phrase][0]
            occurrence = MP_[belong_tag][phrase]
            P_MP[belong_tag] += prob * occurrence
        else:
            prob = phrases[phrase][-1][belong_tag]/phrases[phrase][0]
            occurrence = EC_[belong_tag][phrase]
            P_EC[belong_tag] += prob * occurrence
    P_mp = P_MP['dovish'] + P_MP['neutral'] + P_MP['hawkish']
    P_ec = P_EC['positive'] + P_EC['static'] + P_EC['negative']
    try:
        P_hawkish = P_MP['hawkish']/P_mp
        P_neutral = P_MP['neutral']/P_mp
        P_dovish = P_MP['dovish']/P_mp
    except:
        P_hawkish = 0
        P_neutral = 0
        P_dovish = 0
    try:
        P_positive = P_EC['positive']/P_ec
        P_static = P_EC['static']/P_ec
        P_negative = P_EC['negative']/P_ec  
    except:
        P_positive = 0
        P_static = 0
        P_negative = 0
    I_MP = P_hawkish - P_dovish
    I_EC = P_positive - P_negative
    indicator[date] = {'P_hawkish':P_hawkish, 'P_neutral':P_neutral, 'P_dovish':P_dovish, 'I_MP':I_MP, \
                       'P_positive':P_positive, 'P_static':P_static, 'P_negative':P_negative, 'I_EC':I_EC,'phrases':chosen_phrase_dict}
    
#构建演讲表格
chart = []
for date in indicator:
    P_hawkish = indicator[date]['P_hawkish']
    P_neutral = indicator[date]['P_neutral']
    P_dovish = indicator[date]['P_dovish']
    P_positive = indicator[date]['P_positive']
    P_static = indicator[date]['P_static']
    P_negative = indicator[date]['P_negative']
    I_MP = indicator[date]['I_MP']
    I_EC = indicator[date]['I_EC']
    
    phrases_ = indicator[date]['phrases']
    chart.append([date, P_hawkish, P_neutral, P_dovish, I_MP, P_positive, P_static, P_negative, I_EC, phrases_])
df = pd.DataFrame(chart)
df.columns = ['演讲日期','P_hawkish', 'P_neutral', 'P_dovish','I_MP','P_positive', 'P_static', 'P_negative','I_EC','出现且概率大于0.5且最长的短语']
df.to_csv('短语统计0319_指数.csv',encoding='gbk')

#构建短语表格
chart = []
for phrase in phrases:
    content = phrases[phrase]
    if phrase in phrases_lookup:
        inclination = phrases_lookup[phrase][0]
    else:
        inclination = 'none'
    line = [phrase, content[0], content[2], inclination]
    chart.append(line)
df = pd.DataFrame(chart)
df.columns = ['短语','合计出现次数','出现时间', '短语属性']
df.to_csv('短语统计0319_短语.csv',encoding='gbk')
    
        
