# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re
import pypyodbc
import os, sys
import hashlib
import http.client
import service_1009
import config
import smev


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])


def delTI():
        """Удаляет загруженные ранее записи для 1009 сервиса по списку людей"""
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД АСП")
            exit(1)
        cur = conTI.cursor()
        cur.execute("delete SMEV_SERVICE_PERMIT where F2_id in (1432605, 1462895)")
        conTI.commit()
        conTI.close()


def checkTI(people):
        """Возвращает сколько записей в таблице для 1009 найдено по человеку"""
        DB = TI
        count = 0
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД АСП")
            exit(1)
        cur = conTI.cursor()
        try:
            cur.execute("select count(id) from SMEV_SERVICE_PERMIT where F2_id in (select id from F2 where famil=? and imja=? and OTCH=?)",
                        (people['famil'], people['name'], people['otch']))
            count = cur.fetchone()[0]
        except:
            print('При получении записей для %s %s %s скриптом возникли ошибки'
                  % (people['famil'], people['name'], people['otch']))
        conTI.close()
        return count


class case4(unittest.TestCase):
    """Проверяет сервис 1009 - путевки в лагеря. Делает две выгрузки, проверяет данные перед каждой."""
    @staticmethod
    def setUpClass():
        # очистить папки
        dirList = ('fig/4/', 'Результаты/')
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)


    def setUp(self):
        self.base_url = addr
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.driver.get(self.base_url+'Login.aspx')
        self.verificationErrors = []
        self.accept_next_alert = True
        self.goMainASP()


    def goMainASP(self):
        """ Входит в главное меню АСП"""
        driver = self.driver
        # проверка что это логин
        name = driver.find_element_by_id("tdUserName").text
        self.assertEqual('Имя', name, 'При входе на странице логина не удалось найти текст Имя')
        passw = driver.find_element_by_id("tdPassword").text
        self.assertEqual('Пароль', passw, 'При входе на странице логина не удалось найти текст Пароль')
        # вводим sa и без пароля
        user = driver.find_elements_by_id("tbUserName")[0]
        user.clear()
        user.send_keys("sa")
        passw = driver.find_elements_by_id("tbPassword")[0]
        passw.clear()
        # войти
        driver.find_element_by_css_selector("#lbtnLogin > img").click()


    def clearCheck(self, driver, idList):
        """ Убирает все галочки согласно списку
        :param driver: веб драйвер
        :param idList: список id галочек
        :return:
        """
        for ID in idList:
            checkBox = driver.find_element_by_id(ID)
            if checkBox.is_selected():
                # если выбран, снимаю
                checkBox.click()


    def test_1_kp(self):
        """Направляет запрос на контрольные примеры"""
        err = service_1009.test_1009(TI)
        self.assertEqual(err, 0, 'При выполнении контрольных примеров к 1009 сервису возникли ошибки. %s' % TI['adr'])


    def test_2_ask1009(self):
        """Направляет запрос на тестового человека по путевкам в лагеря. Ожидаю пустой ответ.
        Выделение путевки в санаторный оздоровительный лагерь, СНИЛС 222-222-222-31 - 2 путевки
        1. выделана с 10.06.2014
        2. выделена с 10.08.2015
        Т.к. выгрузку за 2015г не делали, должна быть только одна путевка."""

        # очищаю имеющееся по ФИО
        fioList = (dict(famil='Тестовая', name='Путевка', otch='Лагерь'),
                   dict(famil='Тестов', name='Путевка', otch='Лагерь'))
        delTI()
        # проверим, что очистилось нормально
        for i in (0,1):
            people = fioList[i]
            print('Тест №2. Проверяю для', people['famil'], people['name'], people['otch'])
            count = checkTI(people)
            self.assertEqual(count, 0,
                         'Ожидали, что для %s %s %s будут удалены данные 1009 сервиса, но остально %s строк' %
                         (people['famil'], people['name'], people['otch'], count))
        with open('Шаблоны/Request_1009.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        parent = dict()
        parent['famil'] = ""
        parent['name'] = ""
        parent['otch'] = ""
        parent['snils'] = "222-222-222-31"
        parent['drog'] = ""
        name = '222-222-222-31(1)'
        obr = 'Образцы/' + name + '.xml'
        req = smev.change(shablon, parent)
        req = smev.change(req, TI)
        print("Отрабатываем пример", name)
        res = service_1009.service_1009(req, TI, name)
        # вытащим из нее строку между тегов <smev:MessageData>
        answ = res[res.find('<smev:MessageData>'):res.rfind('</smev:MessageData>')]
        # сравнить с образцом
        with open(obr, mode='r', encoding='utf-8') as f:
            good = f.read()
        self.assertEqual(good, answ, 'Первый ответ 1009 сервиса не совпадает с образцом %s' % obr)


    def test_3_load_2014(self):
        """ Выгружает ПКУ для 1009 сервиса за 2014г."""
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU', 'ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для СМЭВ
        driver.find_element_by_id('ctl00_cph_CB_PKU_SMEV').click()
        # снимаю галочки со всех сервисов
        checkIdList = ('ctl00_cph_CB_s360', 'ctl00_cph_CB_s361', 'ctl00_cph_CB_s373', 'ctl00_cph_CB_s409',
                    'ctl00_cph_CB_s510', 'ctl00_cph_CB_s1000', 'ctl00_cph_CB_s1001', 'ctl00_cph_CB_s1003',
                    'ctl00_cph_CB_s1004', 'ctl00_cph_CB_s1005', 'ctl00_cph_CB_s1007', 'ctl00_cph_CB_s1009')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на 1009
        driver.find_element_by_id('ctl00_cph_CB_s1009').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_wdtS_s1009')
        p.click()
        p.send_keys('01012014')
        # установливаю период по
        p = driver.find_element_by_id('igtxtctl00_cph_wdtPO_s1009')
        p.click()
        p.send_keys('31122014')
        # проверить, что установлены путевки
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "option[value=\"Выделение путевки в санаторный оздоровительный лагерь\"]"),
                        'Не правильно установлен вид социальной поддержки для 1009. Вручную поставьте только Выделение путевки в санаторный оздоровительный лагерь')
        # перейти на выгрузку с помощью веб-сервиса
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td1').click()
        # запускает отправка в 1009
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ для 1009")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ для 1009 возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ СМЭВ+ПГУ. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для СМЭВ прошла не успешно')
        # проверяю на ТИ, что загрузилась одна строка
        fioList = (dict(famil='Тестовая', name='Путевка', otch='Лагерь'),
                   dict(famil='Тестов', name='Путевка', otch='Лагерь'))
        for i in (0,1):
            people = fioList[i]
            count = checkTI(people)
            self.assertEqual(count, 1, 'Ожидали, что для %s %s %s будет 1 строка, но оказалось %s строк' %
                        (people['famil'], people['name'], people['otch'], count))


    def test_4_ask1009(self):
        """Направляет запрос на тестового человека по путевкам в лагеря. Ожидаю данные за 2014г.
        Выделение путевки в санаторный оздоровительный лагерь, СНИЛС 222-222-222-31 - 2 путевки
        1. выделана с 10.06.2014
        2. выделена с 10.08.2015
        Т.к. выгрузку за 2015г не делали, должна быть только одна путевка."""

        with open('Шаблоны/Request_1009.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        parent = dict()
        parent['famil'] = ""
        parent['name'] = ""
        parent['otch'] = ""
        parent['snils'] = "222-222-222-31"
        parent['drog'] = ""

        name = '222-222-222-31(2)'
        obr = 'Образцы/' + name + '.xml'
        req = smev.change(shablon, parent)
        req = smev.change(req, TI)
        print("Отрабатываем пример", name)
        res = service_1009.service_1009(req, TI, name)
        # вытащим из нее строку между тегов <smev:MessageData>
        answ = res[res.find('<smev:MessageData>'):res.rfind('</smev:MessageData>')]
        # сравнить с образцом
        with open(obr, mode='r', encoding='utf-8') as f:
            good = f.read()
        self.assertEqual(good, answ, 'Второй ответ 1009 сервиса не совпадает с образцом %s' % obr)


    def test_5_load_2015(self):
        """ Выгружает ПКУ для 1009 сервиса за 2015г."""
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU', 'ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для СМЭВ
        driver.find_element_by_id('ctl00_cph_CB_PKU_SMEV').click()
        # снимаю галочки со всех сервисов
        checkIdList = ('ctl00_cph_CB_s360', 'ctl00_cph_CB_s361', 'ctl00_cph_CB_s373', 'ctl00_cph_CB_s409',
                       'ctl00_cph_CB_s510', 'ctl00_cph_CB_s1000', 'ctl00_cph_CB_s1001', 'ctl00_cph_CB_s1003',
                       'ctl00_cph_CB_s1004', 'ctl00_cph_CB_s1005', 'ctl00_cph_CB_s1007', 'ctl00_cph_CB_s1009')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на 1009
        driver.find_element_by_id('ctl00_cph_CB_s1009').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_wdtS_s1009')
        p.click()
        p.send_keys('01012015')
        # установливаю период по
        p = driver.find_element_by_id('igtxtctl00_cph_wdtPO_s1009')
        p.click()
        p.send_keys('31122015')
        # проверить, что установлены путевки
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR,
                                                "option[value=\"Выделение путевки в санаторный оздоровительный лагерь\"]"),
                        'Не правильно установлен вид социальной поддержки для 1009. Вручную поставьте только Выделение путевки в санаторный оздоровительный лагерь')
        # перейти на выгрузку с помощью веб-сервиса
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td1').click()
        # запускает отправка в 1009
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ для 1009")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ для 1009 возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ СМЭВ+ПГУ. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для СМЭВ прошла не успешно')
        # проверяю на ТИ, что загрузилась одна строка
        # проверяю на ТИ, что загрузилась одна строка
        people = dict(famil='Тестов', name='Путевка', otch='Лагерь')
        count = checkTI(people)
        print('После второй загрузки, есть %s строк' % count)
        self.assertEqual(count, 2,
                         'Ожидали, что для 222-222-222-31 будет 2 строка в данных 1009 сервиса, но оказалось %s строк' % count)


    def test_6_ask1009(self):
        """Направляет запрос на тестового человека по путевкам в лагеря. Ожидаю данные за 2014г. и 2015г.
        Выделение путевки в санаторный оздоровительный лагерь, СНИЛС 222-222-222-31 - 2 путевки
        1. выделана с 10.06.2014
        2. выделена с 10.08.2015"""

        with open('Шаблоны/Request_1009.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        parent = dict()
        parent['famil'] = ""
        parent['name'] = ""
        parent['otch'] = ""
        parent['snils'] = "222-222-222-31"
        parent['drog'] = ""

        name = '222-222-222-31(3)'
        obr = 'Образцы/' + name + '.xml'
        req = smev.change(shablon, parent)
        req = smev.change(req, TI)
        print("Отрабатываем пример", name)
        res = service_1009.service_1009(req, TI, name)
        # вытащим из нее строку между тегов <smev:MessageData>
        answ = res[res.find('<smev:MessageData>'):res.rfind('</smev:MessageData>')]
        # сравнить с образцом
        with open(obr, mode='r', encoding='utf-8') as f:
            good = f.read()
        self.assertEqual(good, answ, 'Третий ответ 1009 сервиса не совпадает с образцом %s' % obr)


    def test_7_load_2014_15(self):
        """ Выгружает ПКУ для 1009 сервиса за 2014 и 2015г. Ожидается что не будет суммирования с предыдущими, их заменят"""
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU', 'ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для СМЭВ
        driver.find_element_by_id('ctl00_cph_CB_PKU_SMEV').click()
        # снимаю галочки со всех сервисов
        checkIdList = ('ctl00_cph_CB_s360', 'ctl00_cph_CB_s361', 'ctl00_cph_CB_s373', 'ctl00_cph_CB_s409',
                       'ctl00_cph_CB_s510', 'ctl00_cph_CB_s1000', 'ctl00_cph_CB_s1001', 'ctl00_cph_CB_s1003',
                       'ctl00_cph_CB_s1004', 'ctl00_cph_CB_s1005', 'ctl00_cph_CB_s1007', 'ctl00_cph_CB_s1009')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на 1009
        driver.find_element_by_id('ctl00_cph_CB_s1009').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_wdtS_s1009')
        p.click()
        p.send_keys('01012014')
        # установливаю период по
        p = driver.find_element_by_id('igtxtctl00_cph_wdtPO_s1009')
        p.click()
        p.send_keys('31122015')
        # проверить, что установлены путевки
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR,
                                                "option[value=\"Выделение путевки в санаторный оздоровительный лагерь\"]"),
                        'Не правильно установлен вид социальной поддержки для 1009. Вручную поставьте только Выделение путевки в санаторный оздоровительный лагерь')
        # перейти на выгрузку с помощью веб-сервиса
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td1').click()
        # запускает отправка в 1009
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ для 1009")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ для 1009 возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ СМЭВ+ПГУ. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для СМЭВ прошла не успешно')
        # проверяю на ТИ, что загрузилась одна строка
        people = dict(famil='Тестов', name='Путевка', otch='Лагерь')
        count = checkTI(people)
        print('После 3-й загрузки, есть %s строк' % count)
        self.assertEqual(count, 2,
                         'Третья выгрузка. Ожидали, что для 222-222-222-31 будет 2 строка в данных 1009 сервиса, но оказалось %s строк' % count)


    def test_8_ask1009(self):
        """Направляет запрос на тестового человека по путевкам в лагеря. Ожидаю данные за 2014г. и 2015г.
        Выделение путевки в санаторный оздоровительный лагерь, СНИЛС 222-222-222-31 - 2 путевки
        1. выделана с 10.06.2014
        2. выделена с 10.08.2015
        Т.к. выгрузку за 2015г не делали, должна быть только одна путевка."""

        with open('Шаблоны/Request_1009.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        parent = dict()
        parent['famil'] = ""
        parent['name'] = ""
        parent['otch'] = ""
        parent['snils'] = "222-222-222-31"
        parent['drog'] = ""

        name = '222-222-222-31(4)'
        obr = 'Образцы/' + '222-222-222-31(3)' + '.xml'
        req = smev.change(shablon, parent)
        req = smev.change(req, TI)
        print("Отрабатываем пример", name)
        res = service_1009.service_1009(req, TI, name)
        # вытащим из нее строку между тегов <smev:MessageData>
        answ = res[res.find('<smev:MessageData>'):res.rfind('</smev:MessageData>')]
        # сравнить с образцом
        with open(obr, mode='r', encoding='utf-8') as f:
            good = f.read()
        self.assertEqual(good, answ, '4-й ответ 1009 сервиса не совпадает с образцом %s' % obr)


    def test_9_ask1009(self):
        """Направляет запрос на тестового человека по путевкам в лагеря. Ожидаю данные за 2014г.
        Выделение путевки в санаторный оздоровительный лагерь"""

        with open('Шаблоны/Request_1009.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        parent = dict()
        parent['famil'] = "Тестовая"
        parent['name'] = "Путевка"
        parent['otch'] = "Лагерь"
        parent['snils'] = ""
        parent['drog'] = "01.03.2005"

        name = 'Тестовая_без_СНИЛС'
        obr = 'Образцы/' + name + '.xml'
        req = smev.change(shablon, parent)
        req = smev.change(req, TI)
        print("Отрабатываем пример", name)
        res = service_1009.service_1009(req, TI, name)
        # вытащим из нее строку между тегов <smev:MessageData>
        answ = res[res.find('<smev:MessageData>'):res.rfind('</smev:MessageData>')]
        # сравнить с образцом
        with open(obr, mode='r', encoding='utf-8') as f:
            good = f.read()
        self.assertEqual(good, answ, 'Второй ответ 1009 сервиса не совпадает с образцом %s' % obr)


    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e:
            return False
        return True


    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException as e: return False
        return True


    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True


    def tearDown(self):
        n = 1
        arh_name = 'fig/4/error_%s.png' % n
        while os.path.exists(arh_name):
           n +=1
           arh_name = 'fig/4/error_%s.png' % n
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
