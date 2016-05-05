# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, datetime, re
import pypyodbc
import os, sys
import hashlib
import http.client
import config
import xml.etree.ElementTree as ET


# шаблон для запроса
with open("Шаблоны/RequestInfo.xml", mode='r', encoding='utf-8') as f:
    templateRequest = f.read()

TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)



def sendJam(IS, snils, year=''):
    """
    Отсылает запрос и
    :param req: запрос
    :param con: соединение
    :return: возращает ответ или None
    """

    headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "http://socit.ru/GetInfo",
               "Connection": "Keep-Alive"}
    # делаем код безопасности
    m = hashlib.md5()
    m.update(b'JeminySyst')
    m.update(snils.encode('utf-8'))
    # вставляю код безопасности в шаблон
    req = templateRequest.replace("#authCode#", m.hexdigest())
    # вставляю СНИЛС
    req = req.replace("#SNILS#", snils)
    req = req.replace("#YEAR#", year)
    con = http.client.HTTPConnection(IS['adr'], IS['port'])
    try:
        con.request("POST", "/socportal/SMEV/InfoService.asmx", req.encode('utf-8'), headers=headers)
        #con.request("POST", "/ATN2/WebExt/SMEV/InfoService.asmx", req.encode('utf-8'), headers=headers)
        #http://andreyan/ATN2/WebExt/SMEV/InfoService.asmx/GetInfo
        result = con.getresponse().read()
        result = result.decode('utf-8')
        con.close()
    except:
        Type, Value, Trace = sys.exc_info()
        print("Не удалось обратится к методу Request (1-я часть запроса), возникли ошибки:")
        print("Тип:", Type, "Значение:", Value)
        print("Выполнение будет продолжено")
        result = None
    return result



def parseJam (xml):
    """Получает XML, выдает сумму всех sumTotal"""
    summ = 0
    try:
        # пробуем распарсить файл
        root = ET.fromstring(xml)
    except:
        print('Файл не XML')
        summ = -1
    if summ >= 0:
        for case in root.iter('{http://socit.ru/}sumTotal'):
            try:
                summ += float(case.text)
            except:
                print('В одном из тегов sumTotal оказалась не сумма')
    return summ


def delLK(DB):
    """ Удаляет загруженные ранее данные для района, чтобы грузить в новую БД.
    :return:
    """
    # название районов - Энск, ID=17
    with open("Удалить данные района за период.sql", encoding='utf-8', mode='r') as f:
        req = f.read()
    conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
    print(conS)
    try:
        conLK = pypyodbc.connect(conS)
    except:
        print("Возникла ошибка при соединении с БД АСП")
        exit(1)
    cur = conLK.cursor()
    idList = cur.execute("select EService_Users_id from F2 where nps='111-111-221 45' or nps='11111122145'").fetchall()
    for id in idList:
        if id[0]!=17:
            print('Кроме района 17(Энск), человек найден в районе: %s. Там у него будет удален СНИЛС' % id[0])
            cur.execute("update F2 set nps=NULL where nps='111-111-221 45' or nps='11111122145' and EService_Users_id=?", id)
    print('Начинаю удаление данных ЛК для района ЭНСК')
    cur.execute(req)
    conLK.commit()
    conLK.close()
    print('Удаление выполнено')


class case3(unittest.TestCase):
    """Проверяет выгрузку в ЛК и работы веб-сервиса Jaminai. Сначала проверит работу галочек,
    потом будет выгружать за разные периоды и проверять ответы веб-сервиса. Попутно проверит протоколирование выгрузки
    и обращения к сервису на ТИ.
    Всю выгрузку проводит в район Энск (ИД=17), перед выполнением очищает данные для района в ЛК."""

    @staticmethod
    def setUpClass():
        # очистить папки
        dirList = ('fig/3/', 'Результаты/')
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)



    def setUp(self):
        self.timeStart = datetime.datetime.now()
        self.timeBegin = time.time()
        print('%s Выполняю тест: %s' % (self.timeStart, self.id()))
        self.base_url = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.driver.get(self.base_url+'Login.aspx')
        self.verificationErrors = []
        self.accept_next_alert = True
        self.goMainASP()


    def goMainASP(self):
        """ Входит в главное меню АСП
        """
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


    #@unittest.skip('временно отключен')
    def test_1_load_2013(self):
        """ Выгружает ПКУ для ЛК за 2013г.
        :return:
        """
        delLK(LK)
        # направить запрос, чтобы убедится что выплат нет
        IS = TI
        snilsDict = {'111-111-221 45': 0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils)
            with open('Результаты/' + snils + '_1.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого в тесте №1')

        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU','ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для ЛК
        driver.find_element_by_id('ctl00_cph_CB_PKU').click()
        time.sleep(2)
        # снимаю галочки на выгрузку всего, если они стояли
        checkIdList = ('ctl00_cph_CB_payments', 'ctl00_cph_CB_pu', 'ctl00_cph_CB_yd',
                       'ctl00_cph_CB_payinfo', 'ctl00_cph_CB_msp' )
        self.clearCheck(driver, checkIdList)
        # ставлю на ПКУ с ПИН кодом
        driver.find_element_by_id('ctl00_cph_RBL_Type_PKU_1').click()
        # ставлю не выгружать персональную информацию
        driver.find_element_by_id('ctl00_cph_CB_Pers').click()
        # ставлю выплаты
        driver.find_element_by_id('ctl00_cph_CB_payments').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateFrom')
        p.click()
        p.send_keys('01012013')
        # установить дату период по
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateTo')
        p.click()
        p.send_keys('31122013')
        # убираю все галочки с выплат
        checkIdList = ('ctl00_cph_CB_unpaid', 'ctl00_cph_CB_negative', 'ctl00_cph_CB_Inf', 'ctl00_cph_CB_nopay')
        self.clearCheck(driver, checkIdList)
        # ставлю галочки
        checkIdList = ('ctl00_cph_CB_unpaid', 'ctl00_cph_CB_negative', 'ctl00_cph_CB_Inf')
        for id in checkIdList:
            driver.find_element_by_id(id).click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True, 'Галочка признаки учета должна быть не активна при не выбранной Признаки учета')
        # проверяю галочку не выгружать закрытые удостоверения
        p = driver.find_element_by_id('ctl00_cph_CB_no_yd')
        self.assertEqual(p.is_displayed(), True, 'Галочка не выгружать удостоверения закрытые более года назад должна '
                                                  'быть disable при не выбранной Удостоверения')
        # устанавливаю галочку Признаки учета
        driver.find_element_by_id('ctl00_cph_CB_pu').click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        # тут ошибка в ПО, поэтому пока закомментировал
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True, 'Галочка признаки учета должна быть активна при выбранной Признаки учета')
        # проверяет кол-во ПКУ для ЛК
        c = driver.find_element_by_id('ctl00_cph_lbl_Pku_cnt').text
        if c != '21':
            self.assertWarns('Ожидали 24 ПКУ для ЛК, получили %s' % c)
        # перейти на выгрузку с помощью веб-сервиса
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td1').click()
        # запускает отправка в ЛК
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ в ЛК")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ в ЛК возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ ЛК. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для ЛК прошла не успешно')


    #@unittest.skip('временно отключен')
    def test_2(self):
        """Направляет запрос к сервису Jaminai для проверки после загрузки данных за 2013г. Проверяет результат
        на соответствие образцу 111-111-221 45_1.xml. Кратко: за 2013г. - 2650 руб."""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 5300.0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils)
            with open('Результаты/'+snils+'_2.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого в тесте №2')


    #@unittest.skip('временно отключен')
    def test_3_load(self):
        """ Выгружает ПКУ для ЛК за 2014г."""
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU','ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для ЛК
        driver.find_element_by_id('ctl00_cph_CB_PKU').click()
        time.sleep(2)
        # снимаю галочки на выгрузку всего, если они стояли
        checkIdList = ('ctl00_cph_CB_payments', 'ctl00_cph_CB_pu', 'ctl00_cph_CB_yd',
                       'ctl00_cph_CB_payinfo', 'ctl00_cph_CB_msp' )
        self.clearCheck(driver, checkIdList)
        # ставлю на ПКУ с ПИН кодом
        driver.find_element_by_id('ctl00_cph_RBL_Type_PKU_1').click()
        # ставлю не выгружать персональную информацию
        driver.find_element_by_id('ctl00_cph_CB_Pers').click()
        # ставлю выплаты
        driver.find_element_by_id('ctl00_cph_CB_payments').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateFrom')
        p.click()
        p.send_keys('01012014')
        # установить дату период по
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateTo')
        p.click()
        p.send_keys('31122014')
        # убираю все галочки с выплат
        checkIdList = ('ctl00_cph_CB_unpaid', 'ctl00_cph_CB_negative', 'ctl00_cph_CB_Inf', 'ctl00_cph_CB_nopay')
        self.clearCheck(driver, checkIdList)
        # ставлю галочки
        checkIdList = ('ctl00_cph_CB_unpaid', 'ctl00_cph_CB_negative', 'ctl00_cph_CB_Inf')
        for id in checkIdList:
            driver.find_element_by_id(id).click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True, 'Галочка признаки учета должна быть не активна при не выбранной Признаки учета')
        # проверяю галочку не выгружать закрытые удостоверения
        p = driver.find_element_by_id('ctl00_cph_CB_no_yd')
        self.assertEqual(p.is_displayed(), True, 'Галочка не выгружать удостоверения закрытые более года назад должна '
                                                  'быть disable при не выбранной Удостоверения')
        # устанавливаю галочку Признаки учета
        driver.find_element_by_id('ctl00_cph_CB_pu').click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        # тут ошибка в ПО, поэтому пока закомментировал
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True, 'Галочка признаки учета должна быть активна при выбранной Признаки учета')

        # проверяет кол-во ПКУ для ЛК
        c = driver.find_element_by_id('ctl00_cph_lbl_Pku_cnt').text
        #self.assertEqual(c, '24', 'Ожидали 24 ПКУ для ЛК, получили %s' % c)
        # запускает отправка в ЛК
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ в ЛК")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ в ЛК возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ ЛК. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для ЛК прошла не успешно')


    #@unittest.skip('временно отключен')
    def test_4(self):
        """ Направляет запрос к сервису Jaminai для проверки после загрузки данных за весь период"""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 6207.0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils)
            with open('Результаты/' + snils + '_4.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого в тесте №4')


    #@unittest.skip('временно отключен')
    def test_5(self):
        """ Направляет запрос к сервису Jaminai только за 2013г. для проверки после загрузки данных"""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 5300.0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils, '2013')
            with open('Результаты/' + snils + '_5.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого в тесте №4')


    #@unittest.skip('временно отключен')
    def test_6(self):
        """ Направляет запрос к сервису Jaminai только за 2014г. для проверки после загрузки данных должно быть 0"""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils, '2014')
            with open('Результаты/' + snils + '_6.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого')


    #@unittest.skip('временно отключен')
    def test_7(self):
        """ Направляет запрос к сервису Jaminai только за 2015г."""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 907.0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils, '2015')
            with open('Результаты/' + snils + '_7.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого')


    #@unittest.skip('временно отключен')
    def test_8_load(self):
        """Повторит выгрузку за 2013-2015г. но укажет, чтобы не выгружалось по мерам соцподдержки = Льготы по налогам,
        Ежемесячное пособие на ребенка. Выгрузка должна перетереть имеющиеся данные"""

        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU', 'ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        self.clearCheck(driver, checkIdList)
        # ставлю галочку на ПКУ для ЛК
        driver.find_element_by_id('ctl00_cph_CB_PKU').click()
        time.sleep(2)
        # снимаю галочки на выгрузку всего, если они стояли
        checkIdList = ('ctl00_cph_CB_payments', 'ctl00_cph_CB_pu', 'ctl00_cph_CB_yd',
                       'ctl00_cph_CB_payinfo', 'ctl00_cph_CB_msp')
        self.clearCheck(driver, checkIdList)
        # ставлю на ПКУ с ПИН кодом
        driver.find_element_by_id('ctl00_cph_RBL_Type_PKU_1').click()
        # ставлю не выгружать персональную информацию
        driver.find_element_by_id('ctl00_cph_CB_Pers').click()
        # ставлю выплаты
        driver.find_element_by_id('ctl00_cph_CB_payments').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateFrom')
        p.click()
        p.send_keys('01012013')
        # установить дату период по
        p = driver.find_element_by_id('igtxtctl00_cph_periodDateTo')
        p.click()
        p.send_keys('31122015')
        # убираю все галочки с выплат
        checkIdList = ('ctl00_cph_CB_unpaid', 'ctl00_cph_CB_negative', 'ctl00_cph_CB_Inf', 'ctl00_cph_CB_nopay')
        self.clearCheck(driver, checkIdList)
        # ставлю галочки, в т.ч. на Не выгружать информацию по мерам соцподдержки
        for id in checkIdList:
            driver.find_element_by_id(id).click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True,
                         'Галочка признаки учета должна быть не активна при не выбранной Признаки учета')
        # проверяю галочку не выгружать закрытые удостоверения
        p = driver.find_element_by_id('ctl00_cph_CB_no_yd')
        self.assertEqual(p.is_displayed(), True, 'Галочка не выгружать удостоверения закрытые более года назад должна '
                                                 'быть disable при не выбранной Удостоверения')
        # устанавливаю галочку Признаки учета
        driver.find_element_by_id('ctl00_cph_CB_pu').click()
        # проверяю работу галочки не выгружать закрытые признаки учета
        # тут ошибка в ПО, поэтому пока закомментировал
        p = driver.find_element_by_id('ctl00_cph_CB_closed_pu')
        self.assertEqual(p.is_displayed(), True, 'Галочка признаки учета должна быть активна при выбранной Признаки учета')
        # запускает отправка в ЛК
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # ждет, когда отработает прогресс бар (30 мин)
        for i in range(60):
            try:
                p = driver.find_element_by_css_selector("b > b")
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания выгрузки ПКУ в ЛК")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ в ЛК возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ ЛК. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для ЛК прошла не успешно')


    #@unittest.skip('временно отключен')
    def test_9(self):
        """Направить запрос на весь период после выгрузки без учета заявлений Заявка на ежемесячное пособие на детей.
        Сравнит с контрольной суммой"""
        IS = TI
        # заполняет словарь со СНИСЛ и файлами образцами ответов
        snilsDict = {'111-111-221 45': 7.0}
        # перебирает тестовые СНИЛС
        for snils in snilsDict.keys():
            # направляет запрос в сервис по СНИЛС
            result = sendJam(IS, snils)
            with open('Результаты/' + snils + '_9.xml', encoding='utf-8', mode='w') as f:
                f.write(result)
            summ = parseJam(result)
            self.assertEqual(summ, snilsDict[snils], 'Не совпадает сумма итого в тесте №9')


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
        arh_name = 'fig/1/%s.png' % self.id()
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        print('Выполнил тест: %s за %s секунд.' % (self.id(), int(time.time() - self.timeBegin)))


if __name__ == "__main__":
    # прочитаем конфиг файл
    unittest.main(verbosity=2)
