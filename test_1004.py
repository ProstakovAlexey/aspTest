#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
__author__ = 'alexey'

import sys
import http.client
import time
import datetime
from xml.dom.minidom import *
import os
import configparser
import urllib.request
import smev

def readConfig(file="config.ini"):
    '''
    :param file: имя файла конфигурации
    :return: список словарей с людьми; кол-во ошибок
    '''
    err = 0
    if os.access(file, os.F_OK):
        # выполняется если найден конфигурационный файл
        config_str = open(file, encoding='utf-8', mode='r').read()
        # удалить признак кодировки
        config_str = config_str.replace(u'\ufeff', '')
        Config = configparser.ConfigParser()
        Config.read_string(config_str)
        sections = Config.sections()
        # словарь людей для теста. Уникальный ключ - имя теста. Значение - список людей
        parents = dict()
        for section in sections:
            i = Config[section]
            if section.count('human'):
                # Каждого гражданина мы храним в словаре
                parent = dict()
                parent['famil'] = i.get('famil', fallback=None)
                parent['name'] = i.get('name', fallback=None)
                parent['otch'] = i.get('otch', fallback=None)
                parent['drog'] = i.get('drog', fallback=None)
                parent['md5'] = i.get('md5', fallback=0)
                test = i.get('test', fallback= 'None')
                # Добавляем человека в словарь
                # Проверим, есть ли такой человек
                if test in parents:
                    # такой есть
                    parents[test].append(parent)
                else:
                    # такого нет
                    parents[test] = list()
                    parents[test].append(parent)
    else:
        print("Ошибка! Не найден конфигурационный файл")
        err = 1
    return parents, err


def changePers(s, humans):
    """ Проводит замены персональных данных
    :param s: входная строка для замен
    :param d: cписок словарей
    :return: строка с заменами
    """
    insert = ""
    info ="<FIOVariants>\n"
    for human in humans:
        info += "                  <FIO>\n"
        if human['famil']:
            info +="                    <LastName>%s</LastName>\n" % human['famil']
        else:
            info +="                    <LastName/>\n"
        if human['name']:
            info +="                    <FirstName>%s</FirstName>\n" % human['name']
        else:
            info +="                    <FirstName/>\n"
        if human['otch']:
            info +="                    <MiddleName>%s</MiddleName>\n" % human['otch']
        else:
            info +="                    <MiddleName/>\n"
        info +="                  </FIO>\n"
    info +="                </FIOVariants>\n"
    if human['drog']:
        info +="                <BirthDate>%s</BirthDate>" % human['drog']
    else:
        info +="                <BirthDate/>"
    insert += info
    s = s.replace('#INSERT#', insert)
    return s


def service_1004(req, IS, name='1004'):
    '''Получает ответ от сервиса.
    req: строка запроса
    IS: обязательный, словарь. Наименование ИС, мнемоника, ОКТМО
    numer: (обязательный, номер для образования имени)
    ответ сервера в строке или None в случае ошибки
    result: возвращает XML ответ сервиса.
    '''
    # сохранить запрос
    smev.write_file(req, name)
    # соединяется с веб-сервисом
    con = http.client.HTTPConnection(IS['adr'], IS['port'])
    # пытаемся отправить 1-ю часть и получить guid
    headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "ManyChildren"}
    try:
        con.request("POST", IS['url']+"SMEV/ResidencePermit.ashx", req.encode('utf-8'), headers=headers)
        result = con.getresponse().read()
        result = result.decode('utf-8')
    except:
        Type, Value, Trace = sys.exc_info()
        print("Не удалось обратится к методу Request (1-я часть запроса), возникли ошибки:")
        print("Тип:", Type, "Значение:", Value)
        print("Выполнение будет продолжено")
        result = None
    else:
        # проверим, нет ли ошибки в 1-й части
        smev.write_file(result, name)
    con.close()
    return result


def test_1004(IS):
    print("Получение документации 1004-сервиса")
    print("*******************************************")
    # чтение файла конфигурации
    humans, Errors = readConfig('config_1004.ini')
    if Errors == 0:
        print("Загрузили конфигурационный файл")
    else:
        print("При загрузке конфигурационного файла возникли ошибки")
        exit(1)
    err = 0
    start = time.time()
    # получение WSDL
    adr = IS['url']+"SMEV/ResidencePermit.ashx"
    errMsg = smev.get_wsdl(IS, adr, '1004.wsdl')
    if errMsg:
        print(errMsg)
        err +=1
    # отправляем запросы
    shablon = open('Шаблоны/Request_1004.xml', mode='r', encoding='utf-8').read()
    # по списку людей
    for test in humans.keys():
        print("Обрабатываем пример", test)
        req = smev.change(shablon, IS)
        req = changePers(req, humans[test])
        result = service_1004(req, IS, test)
        if humans[test][0]['md5']:
                err1 = smev.check(result, test, humans[test][0]['md5'])
                if err1 > 0:
                    print('Ошибка!!! Не совпадает контрольная суммму блока smev:MessageData.')
                    err += err1
    post = {
            "date": datetime.datetime.now(),
            "name": "Тестирование 1004 сервиса",
            "comment": IS['comment'],
            "version": IS['version'],
            "data":
                {
                    "Итого": time.time() - start
                },
            "errors": err,
            "address": 'http://%s:%s%sSMEV/ResidencePermit.ashx' % (IS['adr'], IS['port'], IS['url'])
            }
    return post
