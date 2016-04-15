#!/usr/bin/python3.4
# -*- coding: utf-8 -*-

import os
import configparser


def readConfig(file="config.ini"):
    '''
    :param file: имя файла конфигурации
    :return: список ИС для тестирования, словарь настроек к БД, кол-во ошибок
    '''
    err = 0
    TI = dict()
    ASP = dict()
    LK = dict()
    if os.access(file, os.F_OK):
        # выполняется если найден конфигурационный файл
        fp = open(file, encoding='utf-8', mode='r')
        config_str = fp.read()
        fp.close()
        # удалить признак кодировки
        config_str = config_str.replace(u'\ufeff', '')
        # чтение конфигурационного файла
        Config = configparser.ConfigParser()
        Config.read_string(config_str)
        sections = Config.sections()
        # читаем все секции
        for section in sections:
            i = Config[section]
            # это секция про ИС, их может быть несколько
            if section.count('TI'):
                TI['snd_name'] = i.get('name', fallback='СОЦИНФОРМТЕХ')
                TI['snd_code'] = i.get('mnemonic', fallback='SOCP01711')
                TI['oktmo'] = i.get('OKTMO', fallback='70000000')
                TI['url'] = i.get('URL', fallback='/socportal/')
                TI['adr'] = i.get('address', fallback='')
                TI['port'] = i.get('port', fallback='80')
                TI['servicecode'] = i.get('SERVICE_CODE', fallback='123456789')
                TI['SpravID'] = i.get('SpravID', fallback='1')
                TI['DB_name'] = i.get('DB_name', fallback='')
                TI['DB_address'] = i.get('DB_address', fallback='')
                TI['DB_port'] = i.get('DB_port', fallback='')
                TI['DB_password'] = i.get('DB_password', fallback='111')

            elif section.count('ASP'):
                ASP['url'] = i.get('URL', fallback='/aspnet/')
                ASP['adr'] = i.get('address', fallback='')
                ASP['port'] = i.get('port', fallback='80')
                ASP['servicecode'] = i.get('SERVICE_CODE', fallback='123456789')
                ASP['SpravID'] = i.get('SpravID', fallback='1')
                ASP['DB_name'] = i.get('DB_name', fallback='')
                ASP['DB_address'] = i.get('DB_address', fallback='')
                ASP['DB_port'] = i.get('DB_port', fallback='')
                ASP['DB_password'] = i.get('DB_password', fallback='111')

            elif section.count('LK'):
                LK['url'] = i.get('URL', fallback='/aspnet/')
                LK['adr'] = i.get('address', fallback='')
                LK['port'] = i.get('port', fallback='80')
                LK['servicecode'] = i.get('SERVICE_CODE', fallback='123456789')
                LK['SpravID'] = i.get('SpravID', fallback='1')
                LK['DB_name'] = i.get('DB_name', fallback='')
                LK['DB_address'] = i.get('DB_address', fallback='')
                LK['DB_port'] = i.get('DB_port', fallback='')
                LK['DB_password'] = i.get('DB_password', fallback='111')

        # проверим заполнение сведений об ТИ
        if len(TI.keys()) == 0:
            print('В конфигурационном файле отсутствует обязательная секция о ТИ.')
            err += 1
        else:
            for key in TI.keys():
                if TI[key] == '':
                    print("В секции сведение о TИ параметр %s не должен быть пустой, заполните его в конфигурационном файле %s" % (key, file))
                    err += 1
        # проверим заполнение сведений об АСП
        if len(ASP.keys()) == 0:
            print('В конфигурационном файле отсутствует обязательная секция об АСП.')
            err += 1
        else:
            for key in ASP.keys():
                if ASP[key] == '':
                    print("В секции сведение об АСП параметр %s не должен быть пустой, заполните его в конфигурационном файле %s" % (
                            key, file))
                    err += 1

        if len(LK.keys()) == 0:
            print('В конфигурационном файле отсутствует обязательная секция о ЛК.')
            err += 1
        else:
            for key in LK.keys():
                if LK[key] == '':
                    print("В секции сведение о ЛК параметр %s не должен быть пустой, заполните его в конфигурационном файле %s" % (
                           key, file))
                    err += 1

    # нет конфигурационного файла
    else:
        print("Ошибка! Не найден конфигурационный файл")
        err = 1
    return TI, ASP, LK, err