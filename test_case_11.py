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
import config
import forSeleniumTests


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])
fio = ('Социальные', 'Пособия', 'Нуждаемость')


def checkZaiv(good, bad):
    """Сравнивает заявление из ПКУ с образцом"""
    res = ''
    # Сравнить номер
    if good['numer']!=bad[0]:
        res += 'Номер заявления не совпадает с образцом. Должен быть %s, получен %s\n' % (good['numer'], bad[0])
    # Дату подачи
    if good['start'] != bad[1]:
        res += 'Дата подачи заявления не совпадает с образцом. Должна быть %s, получена %s\n' % (good['start'], bad[1])
    # Дату с
    if good['begin'] != bad[2]:
        res += 'Дата c заявления не совпадает с образцом. Должна быть %s, получена %s\n' % (good['begin'], bad[2])
    # Дату по
    if good['end'] != bad[3]:
        res += 'Дата c заявления не совпадает с образцом. Должна быть %s, получена %s\n' % (good['end'], bad[3])
    return res


class case11(unittest.TestCase):
    """Социальные пособия (по нуждаемости)
    Тестовый человек: Социальные Пособия Нуждаемость, 01.01.1980
    Код госуслуги: test_case_11
    Код района: 159
    Номера заявлений: test_case_11_1, test_case_11_2, test_case_11_3
    Вид ГСП: Социальные пособия (по нуждаемости)
    Вид заявление АСП: Заявка на адресную социальную помощь
    """
    @staticmethod
    def setUpClass():
        # очистить папки
        dirList = ('fig/11/', 'Результаты/')
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)

    def setUp(self):
        self.timeStart = datetime.datetime.now()
        self.timeBegin = time.time()
        print('%s Выполняю тест: %s' % (self.timeStart, self.id()))
        # соединиться с БД ТИ и АСП
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            self.conTI = pypyodbc.connect(conS)
            self.curTI = self.conTI.cursor()
        except:
            print("Возникла ошибка при соединении с БД ТИ, строка соединения %s" % conS)
            exit(1)
        # соединиться с АСП
        DB = ASP
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" % (
            DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            self.conASP = pypyodbc.connect(conS)
            self.curASP = self.conASP.cursor()
        except:
            print("Возникла ошибка при соединении с БД АСП строка соединения %s" % conS)
            exit(1)
        # создать вебдрайвер
        self.base_url = addr
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        # зайти в АСП
        self.driver.get(self.base_url + 'Login.aspx')
        self.verificationErrors = []
        self.accept_next_alert = True
        self.goMainASP()


    def delASP(self, FIO):
        """По тестовому человеку удаляет заявки и все к ним приложенное"""
        cur = self.curASP
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
            cur.execute(
                "delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
            cur.execute("delete EService_Response where eService_Request_id in (%s)" % es_id)
            cur.execute("delete EService_Scandoc where eService_Request_id in (%s)" % es_id)
            cur.commit()
            # удалить все заявки, кроме самой первой F6_ID=  F6IZM_ID=
            cur.execute("""DELETE F6IZM_DOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6LDOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6DOKUMP WHERE f6izm_id in (select id from F6IZM where F6_ID in
                (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6DOKUMS WHERE f6izm_id in (select id from F6IZM where F6_ID in
                (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6DOKUMV where F6IZM_ID in
            (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s))""" % f2_id)
            cur.execute("delete EService_Request where F2_ID in (%s)" % f2_id)
            cur.execute("""delete F6 where F2_ID in (%s)""" % f2_id)
            cur.execute("delete F_SCANDOC where F2_ID in (%s)" % f2_id)
            cur.commit()


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


    def madeFiltr(self, fio):
        # устанавливаю фильтр по ФИО
        driver = self.driver
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys(fio[0])
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys(fio[1])
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys(fio[2])
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()


    #@unittest.skip('Не работает, задание 51185')
    def test_1(self):
        """Не работает, задание 51185. Удаляет из АСП заявления на человека, загружает и записывает одно заявление с ПГУ"""

        # удаление
        self.delASP(fio)
        # перед загрузкой отмечаем все для района как загруженное
        print('перед загрузкой отмечаем все для района как загруженное')
        self.curTI.execute("""
    -- отметить все заявки района как загруженными
    update EService_Request set exportDate = GETDATE(), exportFile='WEB_SERVICE'
    where EService_Users_id=159 and exportDate is NULL and exportFile is NULL
    -- отметить все СМЭВ ответы как загруженные
    update smev_response_header set Date_Export=GETDATE(), EService_Users_id=159 from smev_response_header a
    inner join SMEV_REQUEST b on b.ID=a.SMEV_REQUEST_ID
    where a.Date_Export is null and b.EService_Users_id=159
        """)
        self.conTI.commit()

        # удаляю ответы на заявки человека на ТИ
        print('удаляю ответы на заявки человека на ТИ')
        cur = self.curTI
        cur.execute("select id from EService_request where lastName=? and firstName=? and middleName=?", fio)
        idList = list()
        for id in cur.fetchall():
            idList.append(str(id[0]))
        es_id = ','.join(idList)
        cur.execute(
            "delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
        cur.execute("delete EService_Response where eService_Request_id in (%s)" % es_id)
        self.conTI.commit()
        print('отмечаю заявления человека к загрузке на ТИ')
        # отмечаю заявление test_case_11_1 к загрузке на ТИ
        cur.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
    lastName=? and firstName=? and middleName=? and requestId='test_case_11_1'""", fio)
        self.conTI.commit()

        # загружаю заявление test_case_11_1
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
        # проверить, что загружено 1 заявление
        self.assertEqual('1', zaiv, 'Ожидали загрузку 1-го заявления')
        # запись заявок
        # захожу в госуслуги
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        # Проверить, должно быть найдено точно = 1, найдено не точно = 1
        self.assertEqual(driver.find_element_by_id("ctl00_cph_wpOper_lbCountFoundVeryOk").text, '1',
                         "Ожидали, что найдено точно = 1")

        self.assertEqual(driver.find_element_by_id("ctl00_cph_wpOper_lbCountFoundOk").text, '1',
                         "Ожидали, что найдено не точно = 1")
        # Нажимает связать все
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр по ФИО
        self.madeFiltr(fio)
        # запись заявлений
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()

        # Перед формирование списка приведу галочки в состояние как на скриншоте №1
        # очистить дату с и по
        for id in ('x:375793386.0:mkr:3', 'x:1509675584.0:mkr:3'):
            p = driver.find_element_by_id(id)
            p.click()
            p.clear()
        # установить галочку независимо от причины отказа
        checkBox = driver.find_element_by_id('ctl00_cph_cbx_SettZayv_1')
        if checkBox.is_selected():
            # если выбран, нормально
            pass
        else:
            # иначе выбираю
            checkBox.click()
        # Установить радиогруппу Со статусом 'отказано' в Зарегистрировать новое заявление
        driver.find_element_by_id('ctl00_cph_rbl_1_SettZayv1').click()
        # Установить радиогруппу Со статусом 'назначено' в Зарегистрировать новые документы к заявлению
        driver.find_element_by_id('ctl00_cph_rbl_2_SettZayv2').click()
        arh_name = 'fig/11/test_галочка_1.png'
        self.driver.save_screenshot(arh_name)
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


    #@unittest.skip('Временно пропущен')
    def test_2(self):
        """Загружает записывает второе заявления с ПГУ"""
        # отмечаю заявление test_case_11_2 к загрузке на ТИ
        self.curTI.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
    lastName=? and firstName=? and middleName=? and requestId='test_case_11_2'""", fio)
        # отсоединяюсь от ТИ
        self.conTI.commit()

        # загружаю заявление test_case_11_2
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
        # проверить, что загружено 1 заявление
        self.assertEqual('1', zaiv, 'Ожидали загрузку 1-го заявления')
        # запись заявок
        # захожу в госуслуги
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр по ФИО
        self.madeFiltr(fio)
        # запись заявлений
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()

        # Перед формирование списка приведу галочки в состояние как на скриншоте №1
        # очистить дату с и по
        for id in ('x:375793386.0:mkr:3', 'x:1509675584.0:mkr:3'):
            p = driver.find_element_by_id(id)
            p.click()
            p.clear()
        # установить галочку независимо от причины отказа
        checkBox = driver.find_element_by_id('ctl00_cph_cbx_SettZayv_1')
        if checkBox.is_selected():
            # если выбран, нормально
            pass
        else:
            # иначе выбираю
            checkBox.click()
        # Установить радиогруппу Со статусом 'отказано' в Зарегистрировать новое заявление
        driver.find_element_by_id('ctl00_cph_rbl_1_SettZayv1').click()
        # Установить радиогруппу Со статусом 'назначено' в Зарегистрировать новые документы к заявлению
        driver.find_element_by_id('ctl00_cph_rbl_2_SettZayv2').click()
        arh_name = 'fig/10/test_галочка_1.png'
        self.driver.save_screenshot(arh_name)
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


    #@unittest.skip('Не работает, задание 51186')
    def test_3(self):
        """е работает, задание 51186. В двух принятых заявлениях визуально проверяет обязательные поля: вкладка госуслуги, контроль госуслуги, номера заявлений"""
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(fio)
        # захожу в обе заявке по очереди
        zaiv = {'test_case_11_1':
                    {'id': 'ctl00_cph_grdMain_ctl03_lbtnGotoZayv',
                     'numer': '1',
                     'get': '05.01.2016'
                     },
                'test_case_11_2':
                    {'id': 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv',
                     'numer': '2',
                     'get': '05.02.2016'
                     }
                }
        for key in zaiv.keys():
            z = zaiv[key]
            # Войти в завку
            driver.find_element_by_id(z['id']).click()
            # Проверить на обложке заявления
            # Проверить Дата подачи заявления
            get = driver.find_element_by_id("ctl00_cph_tbDATRZ1").text
            self.assertEqual(get, z['get'], 'Для заявления %s ожидается период назначения с=%s' % (key, z['get']))
            # Проверить номер заявления в АСП
            numer = driver.find_element_by_id("igtxtctl00_cph_tbNzayv").get_attribute('value')
            self.assertEqual(numer, z['numer'], 'Номер заявления в АСП=%s для заявки ПГУ %s не равен образецу %s' % (numer, key, z['numer']))
            # Проверить наличие вкладки госуслуги
            self.assertTrue(self.is_element_present(By.ID, 'ctl00cphpnlGosUsl_header'),
                            'Для заявления %s нет вкладки Госуслуги' % key)
            # проверить, что внутри контрола есть все поля
            err = forSeleniumTests.checkControl(driver, pre='ctl00_cph_pnlGosUsl_guResp1')
            if err:
                self.fail('При проверке контрола госуслуги на обложке заявления %s найдены ошибки:\n%s' % (key, err))
            # Проверить, что есть контроль госуслуги
            id = "td.StandartHeader > span"
            self.assertTrue(self.is_element_present(By.CSS_SELECTOR, id),
                                 'Для заявления %s нет контрола Госуслуги' % key)

            # Проверить, что контрол не пустой
            s = driver.find_element_by_css_selector(id).text
            if (s.find('Подано через портал ГосУслуг') == -1):
                self.fail('Для заявления %s в контроле должно быть написано Подано через портал ГосУслуг' % key)

            # Проверка внутри заявления
            # Зайти в заявление
            driver.find_element_by_id("ctl00_cph_lbtnDokum").click()

            # Проверить наличие вкладки госуслуги
            self.assertTrue(self.is_element_present(By.XPATH, u"//a[contains(text(),'ГосУслуги')]"),
                            'Для заявления %s нет вкладки Госуслуги' % key)
            # зайти во вкладку
            driver.find_element_by_id('ctl00_cph_tdTabGosUsl').click()
            # проверить, что внутри контрола есть все поля
            err = forSeleniumTests.checkControl(driver, pre='ctl00_cph_guResp1')
            if err:
                self.fail('При проверке контрола госуслуги внутри заявления %s найдены ошибки:\n%s' % (key, err))
            # Проверить, что есть контроль госуслуги
            id = "#ctl00_cph_TopStr_GosUslTop"
            self.assertTrue(self.is_element_present(By.CSS_SELECTOR, id),
                            'Для заявления %s нет контрола Госуслуги' % key)
            # Проверить, что контрол не пустой
            s = driver.find_element_by_css_selector(id).text
            if (s.find('Подано через портал ГосУслуг') == -1):
                self.fail('Для заявления %s в контроле должно быть написано Подано через портал ГосУслуг' % key)
            # выйти в список заявлений
            driver.find_element_by_xpath("//a[@title='Выход']/img").click()


    #@unittest.skip('Временно пропущен')
    def test_4(self):
        """В двух принятых заявлениях выставляет отказ"""
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(fio)
        # захожу в обе заявке по очереди
        zaiv = {'test_case_12_1':
                    {'id': 'ctl00_cph_grdMain_ctl03_lbtnGotoZayv',
                     'numer': '1',
                     'get': '05.01.2016'
                     },
                'test_case_12_2':
                    {'id': 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv',
                     'numer': '2',
                     'get': '05.02.2016'
                     }
                }
        for key in zaiv.keys():
            z = zaiv[key]
            # Войти в завку
            driver.find_element_by_id(z['id']).click()
            # Войти по внутрь
            driver.find_element_by_id("ctl00_cph_lbtnDokum").click()
            # Нажать проверить право
            driver.find_element_by_id("ctl00_cph_lbtnCheckPravo").click()
            # Нажать подтвердить отказ
            driver.find_element_by_id("ctl00_cph_lbnDoIt").click()
            # Выйти с сохранением
            driver.find_element_by_xpath("//a[@title='Выход с сохранением']/img").click()


    #@unittest.skip('Не работает, задание 51206')
    def test_5(self):
        """Не работает, задание 51206. Загружает записывает 3-е заявления с ПГУ. Оно должно будет сесть как еще одно заявление для с неопределенным
        статусом, т.к. два предыдущих были сделаны с отказом."""
        # отмечаю заявление test_case_11_3 к загрузке на ТИ
        self.curTI.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
    lastName=? and firstName=? and middleName=? and requestId='test_case_11_4'""", fio)
        # отсоединяюсь от ТИ
        self.conTI.commit()

        # загружаю заявление test_case_11_2
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
        # проверить, что загружено 1 заявление
        self.assertEqual('1', zaiv, 'Ожидали загрузку 1-го заявления')
        # запись заявок
        # захожу в госуслуги
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр по ФИО
        self.madeFiltr(fio)
        # запись заявлений
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()

        # Перед формирование списка приведу галочки в состояние как на скриншоте №1
        # очистить дату с и по
        for id in ('x:375793386.0:mkr:3', 'x:1509675584.0:mkr:3'):
            p = driver.find_element_by_id(id)
            p.click()
            p.clear()
        # установить галочку независимо от причины отказа
        checkBox = driver.find_element_by_id('ctl00_cph_cbx_SettZayv_1')
        if checkBox.is_selected():
            # если выбран, нормально
            pass
        else:
            # иначе выбираю
            checkBox.click()
        # Установить радиогруппу Со статусом 'отказано' в Зарегистрировать новые документы заявление
        driver.find_element_by_id('ctl00_cph_rbl_2_SettZayv1').click()
        # Установить радиогруппу Со статусом 'назначено' в Зарегистрировать новые документы к заявлению
        driver.find_element_by_id('ctl00_cph_rbl_2_SettZayv2').click()
        arh_name = 'fig/11/test_галочка_2.png'
        self.driver.save_screenshot(arh_name)
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
        # Проверить, что заявок для регистрации 1
        self.assertEqual(driver.find_element_by_id('ctl00_cph_pnlVidSpiska_Lbn1').text, '1',
                         'Ожидается заявок для регистрации 1')
        # Проверить, что заявок для назначения 1
        self.assertEqual(driver.find_element_by_id('ctl00_cph_pnlVidSpiska_Lbn2').text, '1',
                         'Ожидается заявок для назначения 1')
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
        """Выполняется после каждого теста. Сохраняет скриншот результата, закрывает веб-драйвер и соединения с БД"""
        arh_name = 'fig/11/%s.png' % self.id()
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        print('Выполнил тест: %s за %s секунд.' % (self.id(), int(time.time() - self.timeBegin)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
