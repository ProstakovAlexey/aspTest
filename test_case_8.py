#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re
import pypyodbc
import os
import config
import datetime
import time
import forSeleniumTests


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])


class case8(unittest.TestCase):
    """Проверяет прием и обработку
    ГСП:  Ежемесячные денежные выплаты,
    вид заявки: Заявка на возмещение расходов по оплате проезда.
    В БД уже есть одно заявление, принимает второе, оно ложится обращением, делает по нему решение.
    Принимает 3-е - обращением, делает по нему решение.
    Заходит в заявление, проверяет что в нем 3 обращения, в первом нет гсоуслуг, в 2-х других есть и текст ответа и
    файл в каждом свой.
    Используется человек Ежемесячные Денежные Выплаты"""

    @staticmethod
    def setUpClass():
        # очистить папку со скриншотами ошибок
        dir = 'fig/8/'
        for f in os.listdir(dir):
            os.remove(dir+f)


    def setUp(self):
        self.timeStart = datetime.datetime.now()
        self.timeBegin = time.time()
        print('%s Выполняю тест: %s' % (self.timeStart, unittest.TestCase.id(self)))
        self.base_url = addr
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.driver.get(self.base_url+'Login.aspx')
        self.verificationErrors = []
        self.accept_next_alert = True
        self.goMainASP()


    def delASP(self, cur, FIO):
        cur.execute("select id from F2 where FAMIL=? and IMJA=? and OTCH=?", FIO)
        idList = list()
        f2_id = None
        for id in cur.fetchall():
            idList.append(str(id[0]))
            f2_id = ','.join(idList)
        if f2_id:
            cur.execute("select id from EService_Request where F2_ID in (%s)" % f2_id)
            idList = list()
            for id in cur.fetchall():
                idList.append(str(id[0]))
            es_id = ','.join(idList)
            if es_id == "":
                es_id = '0'
            cur.execute("delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
            cur.execute("delete EService_Response where eService_Request_id in (%s)" %  es_id)
            cur.execute("delete EService_Scandoc where eService_Request_id in (%s)" % es_id)
            cur.commit()
            # удалить все заявки, кроме самой первой F6_ID=  F6IZM_ID=
            f6izm_id=9080
            f6_id=9430
            cur.execute("""DELETE F6IZM_DOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))) and f6izm_id!=%s """ % (f2_id, f6izm_id))
            cur.execute("""DELETE F6LDOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))) and f6izm_id!=%s""" % (f2_id, f6izm_id))
            cur.execute("""DELETE F6LGKYSL WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))) and f6izm_id!=%s""" % (f2_id, f6izm_id))
            cur.execute("""DELETE F6DOKUMV where F6IZM_ID in
            (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))) and f6izm_id!=%s""" % (f2_id, f6izm_id))
            cur.execute("""DELETE F_STAGERESULT where F6IZM_ID in
            (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))) and f6izm_id!=%s""" % (f2_id, f6izm_id))
            cur.execute("""DELETE F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)) and id!=%s""" % (f2_id, f6izm_id))
            cur.execute("delete EService_Request where F2_ID in (%s)" % f2_id)
            cur.execute("""delete F6 where F2_ID in (%s) and id!=%s""" % (f2_id, f6_id))
            cur.execute("delete F_SCANDOC where F2_ID in (%s)" % f2_id)
            cur.commit()


    def startConTI(self):
        # возвращает соединение к ТИ
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД ТИ, строка соединения %s" % conS)
            exit(1)
        return conTI


    def startConASP(self):
        DB = ASP
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" % (
        DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conASP = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД АСП строка соединения %s" % conS)
            exit(1)
        return conASP


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


    def madeFiltr(self, driver, fio):
        # устанавливаю фильтр по ФИО
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys(fio[0])
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys(fio[1])
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys(fio[2])
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()


    def verASP(self, cur, nom, good, goodFile):
        """
        :param cur: курсов к БД
        :param nom: образец
        :param good: образец
        :return:
        """
        # проверяю что в БД
        cur.execute("select id, state, info from EService_Response where eService_Request_id in (select id from EService_Request where requestId=?) order by id", (nom,))
        bad = list()
        msg = ""
        respAll = cur.fetchall()
        for resp in respAll :
            bad.append(dict(status=resp[1], comment=resp[2]))
        if(len(good) == len(bad)):
            # проверяем статусы и комментарии
            for i in range(0, len(bad)):
                if bad[i]['status']!=good[i]['status'] or  bad[i]['comment']!=good[i]['comment']:
                    msg += ('Ошибка при проверке решения по заявлению ПГУ. Образец - статус %s, комментарий %s. '
                            'Записано - статус %s, комментарий %s') % (good[i]['status'], good[i]['comment'], bad[i]['status'], bad[i]['comment'])
        else:
            msg+='ОШИБКА! При проверке решений по заявлению ПГУ/МФЦ длина списка образцой не совпадает с фактически полученным.'

        # проверяю приложенные файлы
        cur.execute("select filename from eservice_scandoc where eService_Request_id in (select id from EService_Request where requestId=?) and isResponse = 1", (nom,))
        res = cur.fetchall()
        badFile = None
        if res:
            badFile = '; '.join(res[0])

        if badFile == goodFile:
            #print('Проверка файлов прошла успешно')
            pass
        else:
            msg += 'ОШИБКА! Есть файлы: %s\nОбразец: %s' % (badFile, goodFile)
        return msg


    #@unittest.skip('Временно пропущен')
    def test_1_loadZaivl(self):
        """Загружает заявление Ежемесячные Денежные Выплаты номер=10756763196_fr"""
        # человек
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        # соединяюсь с БД ТИ
        con = self.startConTI()
        cur = con.cursor()
        # перед загрузкой отмечаем все для района как загруженное
        print('перед загрузкой отмечаем все для района как загруженное')
        cur.execute("""
-- номер района
declare @id int = 159
-- отметить все заявки района как загруженными
update EService_Request set exportDate = GETDATE(), exportFile='WEB_SERVICE'
where EService_Users_id = @id and exportDate is NULL and exportFile is NULL
-- отметить все СМЭВ ответы как загруженные
update smev_response_header set Date_Export=GETDATE(), EService_Users_id=@id from smev_response_header a
inner join SMEV_REQUEST b on b.ID=a.SMEV_REQUEST_ID
where a.Date_Export is null and b.EService_Users_id=@id
    """)
        con.commit()
        # удаляю ответы на заявки человека на ТИ
        print('удаляю ответы на заявки человека на ТИ')
        cur.execute("select id from EService_request where lastName=? and firstName=? and middleName=?", fio)
        idList = list()
        for id in cur.fetchall():
            idList.append(str(id[0]))
        es_id = ','.join(idList)
        cur.execute("delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
        cur.execute("delete EService_Response where eService_Request_id in (%s)" %  es_id)
        con.commit()
        print('отмечаю заявления человека к загрузке на ТИ')
        # отмечаю заявление  к загрузке на ТИ
        cur.execute("""-- номер района
declare @id int = 159
-- отметить все заявки района как не загруженную
update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
lastName=? and firstName=? and middleName=? and requestId='10756763196_ft'""", fio)
        # отсоединяюсь от ТИ
        con.commit()
        con.close()
        # соединяюсь с АСП
        con = self.startConASP()
        cur = con.cursor()
        # удаляет в АСП все не обработанные заявления
        print('удаляет в АСП все не обработанные заявления')
        cur.execute("""delete EService_Response where eService_Request_id in (select id from EService_Request where f6_id is NULL and f6izm_id is NULL)
delete EService_Scandoc where eService_Request_id in (select id from EService_Request where f6_id is NULL and f6izm_id is NULL)
delete EService_Request where f6_id is NULL and f6izm_id is NULL""")
        con.commit()
        # удаляю по человеку с АСП заявления, ответы, скандоки
        self.delASP(cur=cur, FIO=fio)
        # отсоединяюсь от АСП
        con.commit()
        con.close()
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # пробуем загрузить заявление
        driver.find_element_by_id("ctl00_cph_lbtnImport").click()
        driver.find_element_by_id("ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal").click()
        # подождать, когда отработает прогресс бар
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        try:
            zaiv = driver.find_element_by_xpath("//span[@id='ctl00_cph_L_Res']/strong[6]").text
        except:
            zaiv = '0'
        self.assertEqual('1', zaiv, 'Ожидали загрузку 1-го заявления')


    #@unittest.skip('Временно пропущен')
    def test_2_writeZaivl(self):
        """Регистрирует заявление. Проверяет как записалось заявление. У человека уже должно было быть одно заявление,
        это сядет к нему как изменение. При этом должно проставится F6 и F6IZM у самой заявки с ПГУ"""
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # запись заявлений
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()
        # Сформировани список
        driver.find_element_by_id("ctl00_cph_lbtnCreateSpisok").click()
        for i in range(120):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться окна Массовая рег. заявок")
        # вот тут надо нажать на 1, в списке
        driver.find_element_by_id("ctl00_cph_pnlVidSpiska_Lbn9").click()
        driver.find_element_by_css_selector("#ctl00_cph_pnl_ViewInfo_lbtnSave > img").click()
        # подождем прогресс запись заявок в БД
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться записи заявок")
        # выйти из записи
        driver.find_element_by_id("ctl00_cph_lbtnGoBack__4").click()
        # соединяюсь с БД АСП
        con = self.startConASP()
        cur = con.cursor()
        # проверяет, что у человека одно заявление
        res = cur.execute("select id from F6 where F2_ID in"
                          "(select id from F2 where famil=? and imja=? and otch=?)", fio).fetchone()
        self.assertEqual(1, len(res), 'Ожидали наличие одного F6')
        f6Id = res[0]
        # проверяет, что у этого заявления 2 IZM
        res = cur.execute("select count(id) from F6izm where F6_ID=%s" % f6Id).fetchone()
        self.assertEqual(2, res[0], 'Ожидали наличие 2-х F6IZM у заявления c F6ID=%s.' % f6Id)
        # проверяет записалось ли F6 и F6IZM в заявление ПГУ
        res = cur.execute(
            "select f6_id, f6izm_id from eService_Request where lastName=? and firstName=? and middleName=?",
            fio).fetchone()
        # print(res[0], res[1])
        self.assertIsNotNone(res[0], 'Ожидали наличие ненулевого F6')
        self.assertIsNotNone(res[1], 'Ожидали наличие ненулевого F6IZM')
        # закрыть соединение с БД
        con.close()


    #@unittest.skip('Временно пропущен')
    def test_3_load2Zaivl(self):
        """Загружает второе заявление Ежемесячные Денежные Выплаты номер=10770536301_ft"""
        # человек
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        # соединяюсь с БД ТИ
        con = self.startConTI()
        cur = con.cursor()
        # отмечаю заявление  к загрузке на ТИ
        cur.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
    lastName=? and firstName=? and middleName=? and requestId in ('10770536301_ft')""", fio)
        # отсоединяюсь от ТИ
        con.commit()
        con.close()
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # пробуем загрузить заявление
        driver.find_element_by_id("ctl00_cph_lbtnImport").click()
        driver.find_element_by_id("ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal").click()
        # подождать, когда отработает прогресс бар
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        try:
            zaiv = driver.find_element_by_xpath("//span[@id='ctl00_cph_L_Res']/strong[6]").text
        except:
            zaiv = '0'
        self.assertEqual('1', zaiv, 'Ожидали загрузку одного заявления')


    #@unittest.skip('Временно пропущен')
    def test_4_writeZaivl(self):
        """Регистрирует заявление. Проверяет как записалось заявление. У человека уже должно было быть одно заявление,
            и 3 изменения. При этом должно проставится F6 и F6IZM у самой заявки с ПГУ"""
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # запись заявлений
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()
        # Сформировани список
        driver.find_element_by_id("ctl00_cph_lbtnCreateSpisok").click()
        for i in range(120):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться окна Массовая рег. заявок")
        # вот тут надо нажать на 1, в списке
        driver.find_element_by_id("ctl00_cph_pnlVidSpiska_Lbn9").click()
        driver.find_element_by_css_selector("#ctl00_cph_pnl_ViewInfo_lbtnSave > img").click()
        # подождем прогресс запись заявок в БД
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться записи заявок")
        # выйти из записи
        driver.find_element_by_id("ctl00_cph_lbtnGoBack__4").click()
        # соединяюсь с БД АСП
        con = self.startConASP()
        cur = con.cursor()
        # проверяет, что у человека одно заявление
        res = cur.execute("select id from F6 where F2_ID in"
                          "(select id from F2 where famil=? and imja=? and otch=?)", fio).fetchall()
        self.assertEqual(1, len(res), 'Ожидали наличие одного F6')
        f6Id = res[0]
        # проверяет, что у этого заявления 2 IZM
        res = cur.execute("select count(id) from F6izm where F6_ID=%s" % f6Id).fetchone()
        self.assertEqual(3, res[0], 'Ожидали наличие 3-х F6IZM у заявления c F6ID=%s.' % f6Id)
        # проверяет записалось ли F6 и F6IZM в заявление ПГУ
        res = cur.execute(
            "select f6_id, f6izm_id from eService_Request where lastName=? and firstName=? and middleName=?",
            fio).fetchall()
        for i in res:
            self.assertIsNotNone(i[0], 'Ожидали наличие ненулевого F6')
            self.assertIsNotNone(i[1], 'Ожидали наличие ненулевого F6IZM')
        # закрыть соединение с БД
        con.close()


    #@unittest.skip('Временно пропущен')
    def test_5_check3zaiv(self):
        """Не работает, задание 51314. Проверит, что у человека в ПКУ только одно заявлени. Пройти в это заявление, проверить:
        1) изменение от 22.04.2014  нет вкладки Госуслуги
        2) изменение от 29.03.2016 есть вкладка Госуслуги
        3) изменение от 11.04.2016 есть вкладка Госуслуги"""
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        driver = self.driver
        # проверить, что у человека показана только одна заявка
        # зайти  в поиск и найти ПКУ человека
        driver.find_element_by_xpath("//form[@id='aspnetForm']/table/tbody/tr/td[3]/a[3]/img").click()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbLastName").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbLastName").send_keys(fio[0])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbName").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbName").send_keys(fio[1])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbPatronymic").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbPatronymic").send_keys(fio[2])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_button1").click()
        # зайти в ПКУ человека
        driver.find_element_by_id("15492").click()
        # найти таблицу с заявками
        table = driver.find_element_by_id('ctl00_cph_DGNeedsOnMain')
        # найти все строки
        st = table.find_elements_by_tag_name('tr')
        count = 0
        for line in st:
            if line.text.find('Заявка на выдачу проездного билета(ЕСПБ РЛ)')>-1:
                count += 1
        self.assertEqual(count, 1, 'Нашли %s заявок в ПКУ. Ожидаем 1' % count)
        # зайти в заявление
        driver.find_element_by_id(
            "ctl00_cph_DGNeedsOnMain_ctl02_Common/EditZayv.aspx?k_gsp=2&id=15492&id_zayv=9430").click()
        # проверить обращение от 11.04.2016
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("11.04.2016")
        driver.find_element_by_id("ctl00_cph_ListData").click()
        # проверить, что есть вкладка госуслуги
        self.assertTrue(self.is_element_present(By.XPATH, u"//a[contains(text(),'ГосУслуги')]"),
            'Для обращения от 11.04.2016 нет вкладки Госуслуги')
        # перейти на владку госуслуги
        driver.find_element_by_id('ctl00_cph_lbtab8').click()
        # проверить, что внутри контрола есть все поля
        err = forSeleniumTests.checkControl(driver, pre='ctl00_cph_guResp1')
        if err:
            self.fail('При проверке контрола госуслуги для обращени 11.04.2016 найдены ошибки:\n%s' % err)
        # проверить, что есть контроль госуслуги
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "#ctl00_cph_TopStr_GosUslTop"),
            'Для обращения от 11.04.2016 нет контрола Госуслуги')
        s = driver.find_element_by_css_selector('#ctl00_cph_TopStr_GosUslTop').text
        if (s.find('Подано через портал ГосУслуг')==-1):
            self.fail('Для обращения от 11.04.2016 в контроле госуслуг должно быть написано Подано через портал ....')

        # проверить обращение от 29.03.2016
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("29.03.2016")
        driver.find_element_by_id("ctl00_cph_ListData").click()
        # проверить, что есть вкладка госуслуги
        self.assertTrue(self.is_element_present(By.XPATH, u"//a[contains(text(),'ГосУслуги')]"),
                                                'Для обращения от 29.03.2016 нет вкладки Госуслуги')
        # перейти на владку госуслуги
        driver.find_element_by_id('ctl00_cph_lbtab8').click()
        # проверить, что внутри контрола есть все поля
        err = forSeleniumTests.checkControl(driver, pre='ctl00_cph_guResp1')
        if err:
            self.fail('При проверке контрола госуслуги для обращени 29.03.2016 найдены ошибки:\n%s' % err)
        # проверить, что есть контроль госуслуги
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "#ctl00_cph_TopStr_GosUslTop"),
                        'Для обращения от 29.03.2016 нет контрола Госуслуги')
        s = driver.find_element_by_css_selector('#ctl00_cph_TopStr_GosUslTop').text

        if (s.find('Подано через портал ГосУслуг') == -1):
            self.fail('Для обращения от 29.03.2016 в контроле госуслуг должно быть написано Подано через портал ....')

        # проверить обращение от 22.04.2016
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("22.04.2014")
        driver.find_element_by_id("ctl00_cph_ListData").click()
        # проверить, что есть вкладка госуслуги
        self.assertFalse(self.is_element_present(By.XPATH, u"//a[contains(text(),'ГосУслуги')]"),
                                                'Для обращения от 22.04.2014 не должно быть  вкладки Госуслуги')
        # проверить, что есть контроль госуслуги
        s = driver.find_element_by_css_selector('#ctl00_cph_TopStr_GosUslTop').text
        if (s.find('Подано через портал ГосУслуг') > -1):
            self.fail('Для обращения от 22.04.2014 в контроле госуслуг должно быть написано Подано через портал ....')


    @unittest.skip('Не работает, задание 50961. Временно пропущен')
    def test_6_check3zaiv(self):
        """Проверить способ выплаты у человека по всем обращениям. Способ выплаты из должен из первого обращения
        (22.04.2014) перенестись в два других (29.03.2016, 11.04.2016). Проверить, что номер транспортной карты
        перенесен из 1-го обращения в два других."""
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        driver = self.driver
        # зайти  в поиск и найти ПКУ человека
        driver.find_element_by_xpath("//form[@id='aspnetForm']/table/tbody/tr/td[3]/a[3]/img").click()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbLastName").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbLastName").send_keys(fio[0])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbName").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbName").send_keys(fio[1])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbPatronymic").clear()
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_tbPatronymic").send_keys(fio[2])
        driver.find_element_by_id("ctl00_cph_WebPanel1_UltraWebTab1_ctl00_button1").click()
        # зайти в ПКУ человека
        driver.find_element_by_id("15492").click()
        # зайти в заявление
        driver.find_element_by_id(
            "ctl00_cph_DGNeedsOnMain_ctl02_Common/EditZayv.aspx?k_gsp=2&id=15492&id_zayv=9430").click()

        # проверить обращение от 22.04.2014
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("22.04.2014")
        # зайти на вкладку Кому выплачивать
        driver.find_element_by_id('ctl00_cph_lbtab3').click()
        # получить направление выплат
        pay = driver.find_element_by_id('ctl00_cph_PayInfo1_lblDirectionPay').text
        # Перейти во вкладку Доп. информация
        driver.find_element_by_id('ctl00_cph_lbtab0').click()
        # Получить номер транспорной карты
        card = driver.find_element_by_id('ctl00_cph_AddInfoZayv1_tbNumTelephone').get_attribute('value')
        #
        # Проверить, что направление выплаты соответствует образцу
        self.assertEqual('Выплатные ведомости (отд. связи/доставки)', pay,
                    'Способ выплаты в обращении от 22.04.2014 не равен Выплатные ведомости (отд. связи/доставки')
        # Проверить, что номер карты = 1234567890
        self.assertEqual('1234567890', card, 'Номер карты в обращении 22.04.2014 не равен 1234567890')
        # Проверить тип транспортной карты
        sel = Select(driver.find_element_by_id('ctl00_cph_AddInfoZayv1_ddlTipCard'))
        photo = sel.first_selected_option.text
        self.assertEqual(photo, 'с фотографией', 'В обращении от 22.04.2014 должно быть установлено в с фотографией')

        # проверить обращение от 29.03.2016
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("29.03.2016")
        #driver.find_element_by_css_selector("option[value=\"9095\"]").click()
        # зайти на вкладку Кому выплачивать
        driver.find_element_by_id('ctl00_cph_lbtab3').click()
        # получить направление выплат
        pay1 = driver.find_element_by_id('ctl00_cph_PayInfo1_lblDirectionPay').text
        # Перейти во вкладку Доп. информация
        driver.find_element_by_id('ctl00_cph_lbtab0').click()
        # Получить номер транспорной карты
        card1 = driver.find_element_by_id('ctl00_cph_AddInfoZayv1_tbNumTelephone').get_attribute('value')
        # Проверить тип транспортной карты
        sel = Select(driver.find_element_by_id('ctl00_cph_AddInfoZayv1_ddlTipCard'))
        photo1 = sel.first_selected_option.text
        self.assertEqual(pay, pay1,
            'Способ выплаты в обращении от 29.03.2016 не совпадает со способом выплат из обр. 22.04.2014')
        self.assertEqual(card, card1,
            'Номер транспортной карты в обращении от 29.03.2016 не совпадает с номером из обр. 22.04.2014')
        self.assertEqual(photo, photo1,'Тип транспортной карты в обращении от 29.03.2016 должно совпадать с 22.04.2014')

        # проверить обращение от 22.04.2016
        Select(driver.find_element_by_id("ctl00_cph_ListData")).select_by_visible_text("22.04.2014")
        #driver.find_element_by_css_selector("option[value=\"9080\"]").click()
        # зайти на вкладку Кому выплачивать
        driver.find_element_by_id('ctl00_cph_lbtab3').click()
        # получить направление выплат
        pay1 = driver.find_element_by_id('ctl00_cph_PayInfo1_lblDirectionPay').text
        # Перейти во вкладку Доп. информация
        driver.find_element_by_id('ctl00_cph_lbtab0').click()
        # Получить номер транспорной карты
        card1 = driver.find_element_by_id('ctl00_cph_AddInfoZayv1_tbNumTelephone').get_attribute('value')
        # Проверить тип транспортной карты
        sel = Select(driver.find_element_by_id('ctl00_cph_AddInfoZayv1_ddlTipCard'))
        photo2 = sel.first_selected_option.text
        self.assertEqual(pay, pay1,
                         'Способ выплаты в обращении от 22.04.2016 не совпадает со способом выплат из обр. 22.04.2014')
        self.assertEqual(card, card1,
                         'Номер транспортной карты в обращении от 22.04.2016 не совпадает с номером из обр. 22.04.2014')
        self.assertEqual(photo, photo2, 'Тип транспортной карты в обращении от 22.04.2016 должно совпадать с 22.04.2014')


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
            alert = webdriver.common.alert.Alert(self.driver)
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True


    def tearDown(self):
        arh_name = 'fig/8/%s.png' % self.id()
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        print('Выполнил тест: %s за %s секунд.' % (self.id(), int(time.time() - self.timeBegin)))



if __name__ == "__main__":
    unittest.main(verbosity=2)