#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
__author__ = 'alexey'

import smev
import sys
import configparser
from xml.dom.minidom import *
import os
import datetime
import  time
import http.client


def service_373(req, IS, name='373'):
    '''Получает ответ от 373 сервиса, подставляет текущую дату в
    исходный файл.
    req: строка запроса (обязательный,в нем меняется время, наименование ИС, КОД, ОКТМО)
    numer: (обязательный, номер для образования имени)
    IS: обязательный, словарь. Сведения об ИС
    ответ сервера в строке или None в случае ошибки
    '''
    # проводим замены
    s = smev.change(req, IS)
    # сохранить запрос
    smev.write_file(s, name)
    # соединяется с веб-сервисом
    con = http.client.HTTPConnection(IS['adr'], IS['port'])
    # пытаемся отправить 1-ю часть и получить guid
    headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "Request"}
    try:
        con.request("POST", IS['url']+"SMEV/Child256.ashx", s.encode('utf-8'), headers=headers)
        result = con.getresponse().read()
        result = result.decode('utf-8')
        status = parseString(result).getElementsByTagName('smev:Status')[0].firstChild.nodeValue
        smev.write_file(result, name)
    except:
        Type, Value, Trace = sys.exc_info()
        print ("Не удалось обратится к методу Request " \
              "(1-я часть запроса), возникли ошибки:")
        print ("Тип:", Type, "Значение:", Value)
        print ("Выполнение будет продолжено")
        result = None
    else:
        # проверим, нет ли ошибки в 1-й части
        if status == u"ACCEPT":
            # нашли что статус ACCEPT
            # получение guid
            # сохранить ответ

            for node in parseString(result).getElementsByTagName('smev:RequestIdRef'):
                guid = node.childNodes[0].nodeValue
            #guid = guid.encode('utf8')
            with open(r"Шаблоны/373-Ping.xml", "r", encoding="utf8") as f:
                s = f.read()
            # проводим замены
            s = smev.change(s,IS)
            # и меняем GUID
            s = s.replace(r"#RequestIdRef#", guid)
            s = s.replace(r"#OriginRequestIdRef#", guid)

            # сохранить запрос
            smev.write_file(s,name)

            # пытаемся отправить 2-ю часть
            headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "Request"}
            try:
                con.request("POST", IS['url']+"SMEV/Child256.ashx", s.encode('utf-8'), headers=headers)
                result = con.getresponse().read()
                result = result.decode('utf-8')
            except:
                Type, Value, Trace = sys.exc_info()
                print ("Не удалось обратится к методу Request" \
                  " (2-я часть запроса), возникли ошибки:")
                print ("Тип:", Type, "Значение:", Value)
                print ("Выполнение будет продолжено")
                result = None
            else:
                # сохранить ответ
                smev.write_file(result,name)
    # если не нашли статус ACCEPT, то сразу попадаем сюда
    con.close()
    return result

def ok_373(IS):
    '''Получает ОК пример для 373 сервиса'''
    # образец
    good_result = dict(codeKind="21", docDatKind="2000-01-01",
                       docDataCiv="1970-01-01", endDate="2010-01-01",
                       fNameCiv="Иван", fNameKind="Иван", iNameCiv="Иванов",
                       iNameKind="Иванов", mNameCiv="Иванович",
                       mNameKind="Иванович", monthsNumber="3",
                       nameOrganizationFrom="ФСС-1",
                       nameOrganizationTo="ФСС-2", nbDoc="00",
                       obtainingGrants2="true", regionFrom="01",
                       regionTo="02", sbDoc="00", seriesNumber="0000000000",
                       snils="000-000-000 00", startDate="2000-01-01")
    with open('Шаблоны/373-OK_Request.xml', mode='r', encoding="utf-8") as f:
        result = service_373(f.read(), IS, '373_ok')
    error = 0
    if result:
        an = parseString(result).getElementsByTagName('ResponseDocument').item(0)
    else:
        an = None
    if an == None:
        # пришел пустой
        error += 1
        print("Тест RESULT. Пришел пустой ответ")
    else:
        # не пустой, анализируем его
        for key in good_result.keys():
            bad = an.getAttribute(key)
            if good_result[key] != bad:
                print("Образец: Ключ=%s, значение=%s" % (key, good_result[key]))
                # уникод
                #print("Получено: Ключ=%s, значение=%s" % (key, an.getAttribute(key).encode("utf8")))
                print("Получено: Ключ=%s, значение=%s" % (key, an.getAttribute(key)))
                error += 1
    if error > 0:
        print("!!!  Тест RESULT. Ошибка!")
    else:
        print("Тест RESULT. Ошибок нет")
    return error


def nofound_373(IS):
    '''Пример для данные не найдены'''
    error = 0
    good_notfound = dict(DataNotFound="")
    with open('Шаблоны/373-NOFOUND_Request.xml', mode='r', encoding="utf-8") as f:
        result = service_373(f.read(), IS, '373_nofound')
    if result:
        an = parseString(result).getElementsByTagName('smev:AppData').item(0)
    else:
        an = None
    if an == None:
        # пришел пустой
        error += 1
        print("Тест NOFOUND. Пришел пустой ответ")
    else:
        # не пустой, анализируем его
        for key in good_notfound.keys():
            bad = an.getAttribute(key)
            if good_notfound[key] != bad:
                print ("Образец: Ключ=%s, значение=%s" % (key, good_notfound[key]))
                print ("Получено: Ключ=%s, значение=%s" % (key, an.getAttribute(key)))
                error += 1
    if error > 0:
        print ("!!!  Тест NOFOUND. Ошибка!")
    else:
        print ("Тест NOFOUND. Ошибок нет")
    return error


def error_data_373(IS):
    '''Пример для ошибка в дате'''
    # Образец ошибка в дате
    good_error1 = dict(
        value=r"ERR_LOAD_REQUEST_DATA: Ошибка загрузки данных из запроса к СМЭВ-сервису: Ошибка загрузки даты рождения: в docDataCiv дата должна быть в формате dd.MM.yyyy")
    with open('Шаблоны/373-ERROR1_Request.xml', mode='r', encoding="utf-8") as f:
        result = service_373(f.read(), IS, '373_err_data')
    error = 0
    if result == None:
        # пришел пустой
        error += 1
        print ("Тест Error Data. Пришел пустой ответ")
    else:
        # не пустой, анализируем его
        for key in good_error1.keys():
            bad = parseString(result).getElementsByTagName('value')[0].firstChild.nodeValue
            if good_error1[key] != bad:
                print ("Образец: Ключ=%s, значение=%s" % (key, good_error1[key]))
                print ("Получено: Ключ=%s, значение=%s" % (key, bad))
                error += 1
    if error > 0:
        print ("!!!  Тест Error1 (не правильная дата). Ошибка!")
    else:
        print ("Тест (не правильная дата). Ошибок нет")
    return error


def error_guid_373(IS):
    # Образец для не найден GUID
    good_error2 = dict(
        value=r"Ответ на асинхронный запрос c message.OriginRequestIdRef = d6ac87b8-a063-47d9-b201-9f0e2dd2de39 не найден в системе")
    with open('Шаблоны/373-ERROR2_Request.xml', mode='r', encoding="utf-8") as f:
        result = service_373(f.read(), IS, '373_err_guid')
    error = 0
    if result == None:
        # пришел пустой
        error += 1
        print ("Тест Error2. Пришел пустой ответ")
    else:
        # не пустой, анализируем его
        for key in good_error2.keys():
            try:
                bad = parseString(result).getElementsByTagName('value')[0].firstChild.nodeValue
                if good_error2[key] != bad:
                    print ("Образец: Ключ=%s, значение=%s" % (key, good_error2[key]))
                    print ("Получено: Ключ=%s, значение=%s" % (key, bad))
                    error += 1
            except:
                print('Ошибка при получении примера с неправильным GUID')
                error +=1
    if error > 0:
        print ("!!!  Тест Error GUID. Ошибка!")
    else:
        print ("Тест Error GUID. Ошибок нет")
    return error


def test_373(IS):
    err = 0
    start = time.time()
    print("Автоматическое тестирование 373 сервиса")
    print("********************************************")
    err += smev.get_wsdl(IS, url=IS['url']+"SMEV/Child256.ashx", name='373.wsdl')
    err += ok_373(IS)
    err += nofound_373(IS)
    err += error_data_373(IS)
    err += error_guid_373(IS)
    return err
