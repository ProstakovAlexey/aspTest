#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
__author__ = 'alexey'

import sys
import http.client
import time
from xml.dom.minidom import *
import os
import configparser
import urllib.request
import datetime
import smev


def readConfig(file="config.ini"):
    '''
    :param file: имя файла конфигурации
    :return: словарь c гражданами и кол-во ошибок
    '''
    err = 0
    if os.access(file, os.F_OK):
        # выполняется если найден конфигурационный файл
        with open(file, encoding='utf-8', mode='r') as f:
            config_str = f.read()
        # удалить признак кодировки
        config_str = config_str.replace(u'\ufeff', '')
        Config = configparser.ConfigParser()
        Config.read_string(config_str)
        sections = Config.sections()
        # пример заполнения сведений от ИС
        parents = list()
        for section in sections:
            i = Config[section]
            if section.count('Citizen'):
                # Каждого гражданина мы храним в словаре
                parent = dict()
                parent['lastName'] = i.get('famil', fallback="")
                parent['firstName'] = i.get('name', fallback="")
                parent['middleName'] = i.get('otch', fallback="")
                parent['birthday'] = i.get('drog', fallback="")
                parent['test'] = i.get('test', fallback='1005')
                parent['documentType'] = i.get('documentype', fallback="")
                parent['series'] = i.get('series', fallback="")
                parent['number'] = i.get('number', fallback="")
                parent['md5'] = i.get('md5', fallback="")
                # Добавляем гражданина в список
                parents.append(parent)
    else:
        print("Ошибка! Не найден конфигурационный файл")
        err = 1
    return parents, err


def equal_1005(good, bad):
    """Сравнивает словарь образец и результат. Если есть отличия, то выдает их как текстовое сообщение"""
    err = ''
    # порядок проверки
    tags = ['lastName', 'firstName', 'middleName', 'birthday', 'documentType',
            'series', 'number', 'exist', 'paySource', 'dateEnd',
            'cardExist', 'TransCardNum']
    for key in tags:
        if good[key] != bad[key]:
            err += 'Поле %s. Образец=%s, результат=%s\n' % (key, good[key], bad[key])
    return err


def print_1005(res):
    """ Печатает ответ от 1005 сервиса в понятном виде.
    вход - res  XML c ответом, не пустая!
    """
    sh = dict(lastName='Фамилия',
              firstName='Имя',
              middleName='Отчество',
              birthday='Дата рождения',
              documentType='Наименование ДУЛ',
              series='Серия',
              number='Номер',
              exist='Получает льготу',
              paySource='Источник финансирования',
              dateEnd='Дата окончания',
              cardExist='Получает в виде транспортной карты',
              TransCardNum='Номер карты')
    result = dict(lastName='',
              firstName='',
              middleName='',
              birthday='',
              documentType='',
              series='',
              number='',
              exist='',
              paySource='',
              dateEnd='',
              cardExist='',
              TransCardNum='')
    # порядок печати
    tags = ['lastName', 'firstName', 'middleName','birthday', 'documentType',
                 'series', 'number', 'exist', 'paySource', 'dateEnd',
                 'cardExist', 'TransCardNum']
    # перебираем элементы словаря
    for key in tags:
        # ищем каждый в ответе
        try:
            tag = parseString(res).getElementsByTagName(key)
            tag = tag[0].firstChild.nodeValue
        except:
            tag = ''
        result[key] = tag

        # проверим, получает ли он льготу?
        if key == 'exist' and tag == '0':
            print("Транспортную льготу не получает")
            # выход из цикла, больше печатать нет смысла
            break
        print("%s: %s" % (sh[key], tag))
    return result


def service_1005(req, IS, name):
    '''Получает ответ от 1005 сервиса, подставляет текущую дату в
    исходный файл.
    req: строка запроса (обязательный)
    IS: обязательный, словарь. Из него получается адрес, порт
    name: обязательный, префикс для образования имени.
    ответ сервера в строке или None в случае ошибки
    '''
    # сохранить запрос
    smev.write_file(req, name)
    # соединяется с веб-сервисом
    con = http.client.HTTPConnection(IS['adr'], IS['port'])

    # пытаемся отправить 1-ю часть и получить guid
    headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "Transport"}
    try:
        con.request("POST", IS['url']+"/SMEV/Transport.ashx", req.encode('utf-8'), headers=headers)
        result = con.getresponse().read()
        result = result.decode('utf-8')
    except:
        Type, Value, Trace = sys.exc_info()
        print("Не удалось обратится к методу Transport , возникли ошибки:")
        print("Тип:", Type, "Значение:", Value)
        print("Выполнение будет продолжено")
        result = None
    else:
        # проверим, нет ли ошибки
        smev.write_file(result, name)
    con.close()
    return result


def test_1005(IS):
    err = 0
    terr = 0
    print("Получение документации 1005-сервиса")
    print("*******************************************")
    # Загрузка настроек из конфигурационного файла
    Parents, Errors = readConfig("config_1005.ini")
    if Errors == 0:
        print("Загрузили конфигурационный файл")
    else:
        print("При загрузке конфигурационного файла возникли ошибки")
        exit(1)
    start = time.time()
    # получение WSDL
    url = '/Socportal/SMEV/Transport.ashx'
    #print ("Пытаемся получить WSDL по адресу:",\
    #       'http://%s:%s%s?wsdl' % (IS['adr'], IS['port'], url))
    errMsg = smev.get_wsdl(IS, url)
    if errMsg:
        print(errMsg)
        terr += 1
    # Перебираем всех тестовых родителей
    with open('Шаблоны/Request_1005.xml', mode='r', encoding='utf-8') as f:
        shablon = f.read()
    for parent in Parents:
        req = smev.change(shablon, parent)
        req = smev.change(req, IS)
        print("Отправляем запрос на гражданина: %s (%s)" %
              (parent['lastName'], parent['test']))
        # возвращает XML от сервера
        result = service_1005(req, IS, parent['test'])
        # пытаемся напечатать ответ в понятном виде
        if result:
            if parent['md5']:
                err = smev.check(result, parent['test'], parent['md5'])
                if err > 0:
                    print('Ошибка!!! Не совпадает контрольная суммму блока smev:MessageData.')
            else:
                print('****************************')
                print_1005(result)
                print('****************************')
        else:
            print("ОШИБКА! Ответ не получен")
            err =1
        terr += err
    post = {
            "date": datetime.datetime.now(),
            "name": "Тестирование 1005 сервиса",
            "data":
                {
                    "Итого": time.time() - start
                },
            "errors": terr,
            "address": 'http://%s:%s%sSMEV/Transport.ashx' % (IS['adr'], IS['port'], IS['url'])
        }
    print("Все запросы и ответы сохранены в папке Результаты")
    return post
