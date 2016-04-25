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


    @unittest.skip('Временно пропущен')
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


    @unittest.skip('Временно пропущен')
    def test_2_writeZaivl(self):
        """Регистрирует заявление"""
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
        driver.find_element_by_id("ctl00_cph_pnlVidSpiska_Lbn1").click()
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


    #@unittest.skip('Временно пропущен')
    def test_3_checkZaivl(self):
        """Проверяет как записалось заявление. У человека уже должно было быть одно заявление, это сядет к нему
        как изменение. При этом должно проставится F6 и F6IZM у самой заявки с ПГУ"""
        fio = ('Ежемесячные', 'Денежные', 'Выплаты')
        # соединяюсь с БД АСП
        con = self.startConASP()
        cur = con.cursor()
        # проверяет, что у человека одно заявление
        res = cur.execute("select id from F6 where F2_ID in"
                          "(select id from F2 where famil=? and imja=? and otch=?)", fio).fetchone()
        self.assertEqual(1, len(res), 'Ожидали наличие одного F6')
        # проверяет, что у этого заявления 2 IZM
        res = cur.execute("select count(id) from F6izm where F6_ID=?", res).fetchone()
        self.assertEqual(2, len(res), 'Ожидали наличие 2-х F6IZM у заявления %s' % res[0])
        # проверяет записалось ли F6 и F6IZM в заявление ПГУ
        res = cur.execute("select count(id) from eService_Request "
                          "where lastName=? and firstName=? and middleName=? and "
                          "(F6_ID is not NULL) and F6IZM_ID in not NULL", fio).fetchall()
        self.assertEqual(1, len(res), 'Ожидали наличие 1-го не нулевого F6IZM')
        # закрыть соединение с БД
        con.close()



    @unittest.skip('Временно пропущен')
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


    @unittest.skip('Временно пропущен')
    def test_4_writeZaivl(self):
        """Регистрирует заявление, проверяет создание 3-х заявление с заполненными F6 и F6_izm."""
        fio = ('Пособие', 'Семьям', 'Детям')
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
        driver.find_element_by_id("ctl00_cph_pnlVidSpiska_Lbn1").click()
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
        # проверить, как записалось. Для этого человека должно быть создано 2 f6
        # соединяюсь с БД АСП
        con = self.startConASP()
        cur = con.cursor()
        # получает кол-во заявлений и изменений к ним для человека
        res = cur.execute("select f6_id, f6izm_id from eService_Request "
                          "where lastName=? and firstName=? and middleName=?", fio).fetchall()
        # закрыть соединение с БД
        con.close()
        # проверяет, что создалось одно заявление и один izm
        self.assertEqual(3, len(res), 'Ожидали создание 1-х F6 и F6_izm')
        # проверяет, что каждый F6 и F6_IZM заполен
        for i in res:
            self.assertTrue(i[0], 'F6 должен быть заполнен')
            self.assertTrue(i[1], 'F6_IZM должен быть пустой')


    @unittest.skip('Временно пропущен')
    def test_5_check3zaiv(self):
        """Проверит, что во всех 3-х заявления есть обязательные поля:
        1) уникальный номер заявления
        2) на обложке вкладка Госуслуги
        3) в заявлении вкладка Госуслуги"""
        # словарь ID, по которым переходить
        id = {'family_4': 'ctl00_cph_grdMain_ctl04_lbtnGotoZayv',
              'family_3': 'ctl00_cph_grdMain_ctl03_lbtnGotoZayv',
              'family_2': 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'}
        # список уникальных номеров заявлений в АСП
        num = list()
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        fio = ('Пособие', 'Семьям', 'Детям')
        self.madeFiltr(driver, fio)
        # перебираю 3 заявления
        for key in id.keys():

            # проверить на обложке. Заходит в заявление
            driver.find_element_by_id(id[key]).click()
            # поверить наличие номера заявления
            n = driver.find_element_by_id('igtxtctl00_cph_tbNzayv').get_attribute('value')
            # записать его в список номеров
            num.append(n)
            # проверить, что есть госуслуги на обложке
            try:
                driver.find_element_by_id('ctl00_cph_pnlGosUsl')
            except:
                self.fail('Для заявления %s нет вкладки Госуслуги на обложке' % key)

            # проверить внутри заявления. Зайти во внутрь заявления
            driver.find_element_by_id('ctl00_cph_lbtnDokum').click()
            # проверить, что есть вкладка госуслуги
            try:
                driver.find_element_by_id('ctl00_cph_tabtd12')
            except:
                self.fail('Для заявления %s нет вкладки Госуслуги внутри заявления' % key)
            # перейти на вкладку дети
            driver.find_element_by_id('ctl00_cph_tabtd1').click()
            # проверить, что есть ребенок ФамилияРебенка ИмяРебенка ОтчествоРебенка
            s = driver.page_source
            if s.find('ФамилияРебенка ИмяРебенка ОтчествоРебенка')<0:
                self.fail('Для заявления %s на вкладке Дети не нашли ФИО ребенка' % key)
            # перейти на вкладку Кому выплачивается
            driver.find_element_by_id('ctl00_cph_tabtd3').click()
            # проверить получателя
            pol = driver.find_element_by_id('ctl00_cph_tab__ctl3_PayInfo1_lblPoluch').text
            self.assertEqual(pol, '01:01:0011577 Пособие Семьям Детям')
            # проверит направление выплаты
            pol = driver.find_element_by_id('ctl00_cph_tab__ctl3_PayInfo1_lblDirectionPay').text
            self.assertEqual(pol, 'Списки (касса учреждения)')
            # выходит на обложку
            driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_Exit").click()
            #  выходит из заявки
            driver.find_element_by_id("ctl00_cph_lbtnExit").click()
        # проверить, что все номера уникальные.
        # Способ проверки - через множества - http://younglinux.info/python/task/uniqueness
        setnum = set(num)
        self.assertEqual(len(num), len(setnum),
                         'Найдены не уникальные номера заявлений в АСП. Список номеров: %s' % num)


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
        n = 1
        arh_name = 'fig/8/test_%s.png' % n
        while os.path.exists(arh_name):
           n +=1
           arh_name = 'fig/8/test_%s.png' % n
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)


if __name__ == "__main__":
    unittest.main(verbosity=2)