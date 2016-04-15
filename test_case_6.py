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


class case6(unittest.TestCase):
    """Проверяет прием и обработку заявлений по Вид заявки: Заявки на получение субсидии на оплату жилья и ЖКУ,
    ГСП: прочее. Используется человек Тестова ПГУ Прочее, номера заявлений: 122675408, 122675409, 122675410.
    Сначала загружает, обрабатывает и проверяет одно заявление, потом два."""

    @staticmethod
    def setUpClass():
        # очистить папку со скриншотами ошибок
        dir = 'fig/6/'
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
            cur.execute("""DELETE F6IZM_DOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6LDOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6LGKYSL WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (%s)))""" % f2_id)
            cur.execute("""DELETE F6IZM where F6_ID in (select id from F6 where F2_ID in (%s))""" % f2_id)
            cur.execute("delete EService_Request where F2_ID in (%s)" % f2_id)
            cur.execute("""delete F6 where F2_ID in (%s)""" % f2_id)
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


    def test_1_loadZaivl(self):
        """Загружает заявление для Тестова ПГУ Прочее"""
        # человек
        fio = ('Тестова', 'ПГУ', 'Прочее')
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
        # отмечаю заявление  122675408 к загрузке на ТИ
        cur.execute("""-- номер района
declare @id int = 159
-- отметить все заявки района как не загруженную
update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
lastName=? and firstName=? and middleName=? and requestId='122675408'""", fio)
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


    def test_2_writeZaivl(self):
        """Регистрирует заявление, проверяет создание 1-х заявление с заполненными F6 не NULL, F6_izm=NULL."""
        fio = ('Тестова', 'ПГУ', 'Прочее')
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
        self.assertEqual(1, len(res), 'Ожидали создание 1-х F6 и F6_izm')
        # проверяет, что каждый F6 и F6_IZM заполен
        for i in res:
            self.assertTrue(i[0], 'F6 должен быть заполнен')
            self.assertIsNone(i[1], 'F6_IZM должен быть пустой')


    def test_3_makeRehenie(self):
        """Делает решение принятому заявлению. Выставляет статус ИСПОЛНЕНО,
        тестовый комментарий с указанием номера заявления и прикладывается один файл.
        Решение сохраняет и возвращается в главное меню"""
        # человек
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # заходит в заявление
        task = 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'
        # войти в заявку
        driver.find_element_by_id(task).click()
        # новый ответ из обложки заявления
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
        # выставляет статус ИСПОЛНЕНО(3)
        Select(driver.find_element_by_id("ctl00_cph_guResp1_ddlStatus")).select_by_visible_text("Исполнено")
        driver.find_element_by_css_selector("option[value=\"3\"]").click()
        # заполняет комментарий
        numer = driver.find_element_by_id("igtxtctl00_cph_tbNzayv").get_attribute('value')
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys("Это тестовый статус ИСПОЛНЕНО на заявление №%s" % numer)
        # загружает файл
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc").click()
        fileLoader = 'ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader'
        driver.find_element_by_id(fileLoader).clear()
        driver.find_element_by_id(fileLoader).send_keys("/home/alexey/Desktop/7NAabNgvl0Q.jpg")
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_btnOk > b > b").click()
        # жду загрузки файла
        for i in range(10):
            try:
                p = driver.find_element_by_id('igtxtctl00_cph_clDATWP')
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться загрузки файла")
        # вводит срок действия заявки
        p.click()
        p.send_keys('12042016')
        # выходит из заявки
        driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_SaveExit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_4_checkStatus(self):
        """Скриптом проверяет правильно ли сохранилось в БД принятое решение по 1-м заявления 122675408.
        Визуально проверяет, чтобы не было в прикрепленных файлах otvet.txt.
        """
        # соединяется с БД
        con = self.startConASP()
        cur = con.cursor()
        # проверяет по заявлению 122675408
        good = list()
        good.append(dict(status=2, comment=None, file=None))
        good.append(dict(status=3, comment='Это тестовый статус ИСПОЛНЕНО на заявление №1'))
        msg = self.verASP(cur, '122675408', good, '7NAabNgvl0Q.jpg')
        if msg:
            self.fail('Заявление 122675408. ' + msg)

        # закрывает соединение с БД
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # заходит в заявление
        fileName = 'otvet.txt'
        task = 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'
        # войти в заявку
        driver.find_element_by_id(task).click()
        # ищет на странице текст otvet.txt
        s = driver.page_source
        if s.find(fileName) > 0:
            self.fail('В приложенных файлах нашли %s' % fileName)
        # выходит из заявки
        driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_Exit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_5_checkStatus(self):
        """Пытается повторно ввести статус по заявления 122675408.
        Визуально проверяет чтобы не было в прикрепленных файлах otvet.txt после отправки
        и во время ввода статуса
        """
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # соединяется с БД АСП
        con = self.startConASP()
        cur = con.cursor()
        # устанавливаю время выгрузки для ответов, будто они выгружены
        cur.execute("""update EService_Response set date_Response=getdate() where eservice_request_id in
        (select id from eservice_request where lastName=? and firstName=? and middleName=?) and
         date_Response is NULL""", fio)
        con.commit()
        # отсоединяемся от ДБ АСП
        con.close()
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # берет заявление
        fileName = 'otvet.txt'
        task = 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'
        # войти в заявку
        driver.find_element_by_id(task).click()
        # ищет на странице текст otvet.txt
        s = driver.page_source
        if s.find(fileName) > 0:
            self.fail('После отправки в приложенных файлах нашли %s' % fileName)
        # новый ответ из обложки заявления
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
        # ищет на странице текст otvet.txt
        s = driver.page_source
        if s.find(fileName) > 0:
            self.fail('После нажатия добавить повторный ответ в приложенных файлах нашли %s' % fileName)
        # выходит из заявки
        driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_Exit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_6_checkStatus(self):
        """Заходит в заявление, вставляет комментарий из справочника, проверяет, что вставилось нормально.
         Выходит без сохранения.
        """
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # перебираю два заявления
        mycomment = "Это тестовый комментарий для поверки справочника. "
        task = 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'
        # войти в заявку
        driver.find_element_by_id(task).click()
        # новый ответ из обложки заявления
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
        # выставляет статус Исполено(3)
        Select(driver.find_element_by_id("ctl00_cph_guResp1_ddlStatus")).select_by_visible_text("Исполнено")
        driver.find_element_by_css_selector("option[value=\"3\"]").click()
        # заполняет комментарий
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys(mycomment)
        # сделать вставку из справочника
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnAddInfoSpr").click()
        driver.find_element_by_css_selector("#ctl00_cph_Btn6000000 > font").click()
        driver.find_element_by_id("ctl00_cph_Chk6001000").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit").click()
        # сделать проверку, что в комментарии.
        good ="Ваша заявка была рассмотрена в соответсвии с действующим административным регламентом, и по результатам рассмотрения было принято решение отказать в заявлении в связи с ....."
        good = mycomment + good
        comment = driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text
        self.assertEqual(comment, good, 'Ошибка при использованиии справочника для ввода комментария. Не правильно выполнена вставка из справочнника')
        # выходит из заявки
        driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_Exit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_7_Status2(self):
        """Проверяет известную ошибку, когда при добавлении решений и выгрузке каждого может сохранятся много
        файлов решений (otvet.txt). Заходит в заявление, делает два решения, выгрузку после каждого.
        Проверяет скриптом в БД, должен быть один файл otvet.txt"""
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # соединяется с БД
        con = self.startConASP()
        cur = con.cursor()
        # захожу в госуслуги
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливаю фильтр по ФИО
        self.madeFiltr(driver, fio)
        # берет заявление 265063t3
        mycomment = "Это тестовый комментарий для проверки формирования 2-х файлов otvet.txt\n"
        # делает два решения и выгрузку после каждого
        task = 'ctl00_cph_grdMain_ctl02_lbtnGotoZayv'
        for i in (1,2):
            # войти в заявку
            driver.find_element_by_id(task).click()
            # новый ответ из обложки заявления
            driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
            # выставляет статус Исполено(3)
            Select(driver.find_element_by_id("ctl00_cph_guResp1_ddlStatus")).select_by_visible_text("Исполнено")
            driver.find_element_by_css_selector("option[value=\"3\"]").click()
            # заполняет комментарий
            driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").click()
            driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
            num = "%s) " % i
            text = num + mycomment
            driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys(text)
            # сохраняет комментарий и статус
            driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_Save").click()
            # проверить, что вышло окно подтверждающее сохранение
            text = self.close_alert_and_get_its_text()
            self.assertEqual(text, 'Сохранение выполнено!', 'Сохранение не выполнено'  )
            # загружает файл
            driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc").click()
            fileLoader = 'ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader'
            driver.find_element_by_id(fileLoader).clear()
            driver.find_element_by_id(fileLoader).send_keys("/home/alexey/Desktop/7NAabNgvl0Q.jpg")
            driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_btnOk > b > b").click()
            # жду загрузки файла
            for i in range(10):
                try:
                    driver.find_element_by_id('igtxtctl00_cph_clDATWP')
                    break
                except:
                    pass
                time.sleep(1)
            else:
                self.fail("Не удалось дождаться загрузки файла")
            # выходит из заявки
            driver.find_element_by_id("ctl00_cph_TopStr1_lbtnTopStr_Exit").click()
            # устанавливаю время выгрузки для ответов, будто они выгружены
            cur.execute("""update EService_Response set date_Response=getdate() where eservice_request_id in
        (select id from eservice_request where lastName=? and firstName=? and middleName=?) and
         date_Response is NULL""", fio)
            con.commit()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # спросить в БД сколько файлов otvet.txt к заявлению 122675408
        cur.execute("""select count(id) from eservice_scandoc where EService_Response_id in
	(select top 1 id from EService_Response where EService_Request_id in
         (select id from EService_Request where requestId='122675408') order by id desc)
         and isResponse = 1 and filename='otvet.txt'""")
        c = cur.fetchone()[0]
        # отсоединяется от Бд
        con.close()
        # выполняется проверка, кол-во файлов otvet.txt по заявлению  265063t3  должно быть 1
        self.assertEqual(c, 1, 'Кол-во файлов otvet.txt по заявлению 265063t3  должно быть 1, получилось %s' % c)


    def test_8_loadZaivl(self):
        """Загружает 2 заявления для Тестова ПГУ Прочее"""
        # человек
        fio = ('Тестова', 'ПГУ', 'Прочее')
        # соединяюсь с БД ТИ
        con = self.startConTI()
        cur = con.cursor()
        # отмечаю заявление  122675408 к загрузке на ТИ
        cur.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and
    lastName=? and firstName=? and middleName=? and requestId in ('122675409', '122675410')""", fio)
        # отсоединяюсь от ТИ
        con.commit()
        con.close()
        # пробуем загрузить заявление
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
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
        self.assertEqual('2', zaiv, 'Ожидали загрузку 2-х заявлений')


    def test_9_writeZaivl(self):
        """Регистрирует два заявления, проверяет создание 3-х заявление (3-х, т.к. сейчас 2, до этого 1)
         с заполненными F6 не NULL, F6_izm=NULL."""
        fio = ('Тестова', 'ПГУ', 'Прочее')
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
        self.assertEqual(3, len(res), 'Ожидали наличие 3-х F6 и F6_izm')
        # проверяет, что каждый F6 и F6_IZM заполен
        for i in res:
            self.assertTrue(i[0], 'F6 должен быть заполнен')
            self.assertIsNone(i[1], 'F6_IZM должен быть пустой')


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
        arh_name = 'fig/6/error_%s.png' % n
        while os.path.exists(arh_name):
           n +=1
           arh_name = 'fig/6/error_%s.png' % n
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)


if __name__ == "__main__":
    # очистить папку со скриншотами ошибок
    unittest.main(verbosity=2)
