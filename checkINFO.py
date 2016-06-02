#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
import hashlib
import http.client
import sys
import logging
import time
import os
import xml.etree.ElementTree as ET

"""
Отправляет запросы в статый и новый инфосервис, результаты собирает в папки.
Выполняет сравнение
"""
old = 'Сравнение/old/'
new = 'Сравнение/new/'
# шаблон для запроса
with open("Шаблоны/RequestInfo409.xml", mode='r', encoding='utf-8') as f:
    templateRequest409 = f.read()
with open("Шаблоны/RequestInfo.xml", mode='r', encoding='utf-8') as f:
    templateRequest = f.read()
# Для старого сервиса
headers409 = {"Content-Type": "text/xml; charset=utf-8",
           "SOAPAction": "http://socit.ru/GetInfo409",
           "Connection": "Keep-Alive"}
headers = {"Content-Type": "text/xml; charset=utf-8",
              "SOAPAction": "http://socit.ru/GetInfo",
              "Connection": "Keep-Alive"}

log_file = r'logs/Сравнение_' + time.strftime(r'%Y.%m.%d') + r'.log'
logging.basicConfig(filename=log_file, filemode='a', level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')


def sendJam(con, snils, year='', flag='old'):
    """
    """
    # делаем код безопасности
    m = hashlib.md5()
    m.update(b'JeminySyst')
    m.update(snils.encode('utf-8'))
    if flag=='new':
        # вставляю код безопасности в шаблон
        req = templateRequest409.replace("#authCode#", m.hexdigest())
    elif flag=='old':
        req = templateRequest.replace("#authCode#", m.hexdigest())
    # вставляю СНИЛС
    req = req.replace("#SNILS#", snils)
    req = req.replace("#YEAR#", year)
    try:
        if flag=='new':
            con.request("POST", '/atn2/webext/smev/infoservice.asmx', req.encode('utf-8'), headers=headers409)
        elif flag =='old':
            con.request("POST", '/socportal/SMEV/InfoService.asmx', req.encode('utf-8'), headers=headers)
        result = con.getresponse().read()
        result = result.decode('utf-8')
    except:
        Type, Value, Trace = sys.exc_info()
        print("Не удалось обратится к методу Request (1-я часть запроса), возникли ошибки:")
        print("Тип:", Type, "Значение:", Value)
        print("Выполнение будет продолжено")
        result = None
    return result


def send(flag):
    # Получить список всех файлов со СНИЛС
    logging.debug("Создается список файлов со СНИЛС")
    fileList = os.listdir('Сравнение/nps')
    sT = time.time()
    # Подготовка соедиения с ТУ
    if flag=='new':
        con = http.client.HTTPConnection('192.168.0.117', 80)
    elif flag=='old':
        con = http.client.HTTPConnection('192.168.0.3', 2121)
    # Перебирать их по одному
    for f in fileList:
        s = time.time()
        # подготовим папку для результата
        if flag == 'new':
            name = 'Сравнение/new/' + f
        elif flag == 'old':
            name = 'Сравнение/old/' + f
        if os.access(name, os.F_OK) == False:
            os.mkdir(name)
            logging.info("Каталог для архивов был создан: " + name)
        # Читать файл, преобразовать его содержимое в список
        snilsList = open('Сравнение/nps/' + f, 'r').read().splitlines()
        # Берем СНИЛС из списка
        for snils in snilsList:
            # Отправить запрос
            logging.debug('Отправляю запрос на СНИЛС %s' % snils)
            res = sendJam(con, snils=snils, year='2013', flag=flag)
            if res:
                with open(name + '/' + snils, 'w') as fp:
                    fp.write(res)
        logging.info('Набор %s отправили за %s сек' % (f, time.time() - s))
        #exit(1)
    logging.info('Все наборы отправили за %s сек' % (time.time() - sT))
    con.close()


def parseJam(xml):
    """
     <PaymentItem>
              <name>Заявки на получение льгот на оплату жилья и ЖКУ</name>
              <sumTotal>1167.74</sumTotal>
              <sumTotalComment>1167,74 = 1167,74</sumTotalComment>
              <sum1>1167.74</sum1>
              <sum1Comment>50% скидка по оплате водоотведения: 45,08; 50% скидка по оплате газа: 69,63; 50% скидка по оплате жил.площади: 272,73; 50% скидка по оплате тепловой энергии: 591,56; 50% скидка по оплате холодного водоснабжения: 89,86; 50% скидка по оплате электрической энергии: 96,60; 50% скидка по оплате электрической энергии МОП: 2,28</sum1Comment>
              <sum2>0</sum2>
              <sum3>0</sum3>
              <sum4>0</sum4>
              <sum5>0</sum5>
              <sum6>0</sum6>
              <sum7>0</sum7>
              <sum8>0</sum8>
              <sum9>0</sum9>
              <sum10>0</sum10>
              <sum11>0</sum11>
              <sum12>0</sum12>
            </PaymentItem>
    :param xml:
    :return:
    """
    #xml = '''<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><GetInfo409Response xmlns="http://socit.ru/"><GetInfo409Result><Snils>031-736-164 30</Snils><viplInfo><year>2014</year><payments><PaymentItem><name>Заяв.на ежем.ден.комп.на прод.товар(в т.ч.по суду)</name><sumTotal>705.39</sumTotal><sumTotalComment>705,39 = 705,39</sumTotalComment><sum1>705.39</sum1><sum1Comment>Ежем.ден.комп.на приоб.прод.тов.инв.по суду(210,212,214,591,592): 705,39</sum1Comment><sum2>0</sum2><sum3>0</sum3><sum4>0</sum4><sum5>0</sum5><sum6>0</sum6><sum7>0</sum7><sum8>0</sum8><sum9>0</sum9><sum10>0</sum10><sum11>0</sum11><sum12>0</sum12></PaymentItem><PaymentItem><name>Заявки на получение льгот на оплату жилья и ЖКУ</name><sumTotal>279.18</sumTotal><sumTotalComment>279,18 = 279,18</sumTotalComment><sum1>279.18</sum1><sum1Comment>50% скидка по оплате жил.площади: 279,18</sum1Comment><sum2>0</sum2><sum3>0</sum3><sum4>0</sum4><sum5>0</sum5><sum6>0</sum6><sum7>0</sum7><sum8>0</sum8><sum9>0</sum9><sum10>0</sum10><sum11>0</sum11><sum12>0</sum12></PaymentItem><PaymentItem><name>Итого</name><sumTotal>984.57</sumTotal><sumTotalComment>984,57 = 984,57</sumTotalComment><sum1>984.57</sum1><sum2>0</sum2><sum3>0</sum3><sum4>0</sum4><sum5>0</sum5><sum6>0</sum6><sum7>0</sum7><sum8>0</sum8><sum9>0</sum9><sum10>0</sum10><sum11>0</sum11><sum12>0</sum12></PaymentItem></payments></viplInfo></GetInfo409Result></GetInfo409Response></soap:Body></soap:Envelope>'''
    result = list()
    tags = ('name', 'sumTotal', 'sumTotalComment', 'sum1', 'sum2', 'sum3', 'sum4', 'sum5', 'sum6', 'sum7', 'sum8', 'sum9',
            'sum10', 'sum11', 'sum12')
    root = ET.fromstring(xml)
    for case in root.iter('{http://socit.ru/}PaymentItem'):
        res = dict()
        for tag in tags:
            res[tag] = case.find('{http://socit.ru/}%s' % tag).text
        result.append(res)
    return result


def checkJam(good, bad):
    res = 0
    tags = (
    'name', 'sumTotal', 'sumTotalComment', 'sum1', 'sum2', 'sum3', 'sum4', 'sum5', 'sum6', 'sum7', 'sum8', 'sum9',
    'sum10', 'sum11', 'sum12')
    if good is None and bad is None:
        res = 1
    else:
        if len(good) != len(bad):
            print('Разница по длине')
            res = 1
        else:
            for i in range(0, len(good)):
                for tag in tags:
                    if good[i][tag]!=bad[i][tag]:
                        res = 1
                        print('Не соответствует номер %s, значение тега %s' % (i, tag))
                        print('bad =', bad[i][tag])
                        print('good=', good[i][tag])
                        break
    return res


def checkAll():
    # Сравнение
    logging.debug("Создается список файлов со СНИЛС")
    fileList = os.listdir('Сравнение/nps')
    # Перебирать их по одному
    for f in fileList:
        snilsList = open('Сравнение/nps/' + f, 'r').read().splitlines()
        # Берем СНИЛС из списка
        for snils in snilsList:
            try:
                # читаем его из файл
                with open(os.path.join('Сравнение', 'new', f, snils)) as fp:
                    xml = fp.read()
                good = parseJam(xml)
                with open(os.path.join('Сравнение', 'old', f, snils)) as fp:
                    xml = fp.read()
                bad = parseJam(xml)
            except:
                print('Не смогли прочитать из файла', snils)
                continue

            if checkJam(good, bad):
                print('% s Ошибка' % snils)
                exit(1)
            else:
                print('%s Соответствует' % snils)



if __name__ == '__main__':
    #send(flag='old')
    # Для Андрея Фирсанова
    # Сравнить
    checkAll()

    exit(0)