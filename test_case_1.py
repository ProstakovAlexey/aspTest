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
import hashlib
import config


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])


class case1(unittest.TestCase):
    """Проверяет работу основных пунктов меню для госуслуги. Заявку вид
    АСП: Заявки на получение льгот на оплату жилья и ЖКУ,
    вид ГСП: Льготы на оплату жилья и ЖК услуги.
    Должны загружаться 2 заявления последовательно, 2-е добавляться как обращение к первому.
    Корректная работа полученного обращения с контролом госуслуги."""
    @staticmethod
    def setUpClass():
        # очистить папку со скриншотами ошибок
        dir = 'fig/1/'
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
            cur.execute("select id from EService_Request where F2_ID in (?)",(f2_id,))
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
            (select id from F6 where F2_ID in (?)))""", (f2_id,))
            cur.execute("""DELETE F6LDOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (?)))""", (f2_id,))
            cur.execute("""DELETE F6LGKYSL WHERE f6izm_id in (select id from F6IZM where F6_ID in
            (select id from F6 where F2_ID in (?)))""", (f2_id,))
            cur.execute("""DELETE F6IZM where F6_ID in (select id from F6 where F2_ID in (?))""", (f2_id,))
            cur.execute("delete EService_Request where F2_ID in (?)", (f2_id,))
            cur.execute("""delete F6 where F2_ID in (?)""", (f2_id,))
            cur.execute("delete F_SCANDOC where F2_ID in (?)", (f2_id,))
            cur.commit()


    def startConTI(self):
        # возвращает соединение к ТИ
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except :
            print("Возникла ошибка при соединении с БД АСП")
            exit(1)
        return conTI


    def startConASP(self):
        DB = ASP
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conASP = pypyodbc.connect(conS)
        except :
            print("Возникла ошибка при соединении с БД АСП, строка соедиения=%s" % conS)
            exit(1)
        return conASP


    def goMainASP(self):
        """ Входит в главное меню АСП """
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


    def test_1(self):
        """Заходит в БД, проверяет что не нужно обновить, проверяет что это контрольный пример тест,
        ходит по меню госуслуги"""

        driver = self.driver
        # проверить, что ее нужно обновить
        s = driver.page_source
        if s.find('В списке баз данных найдены базы, у которых структура отличается от требуемой') > 0:
            self.fail('Необходимо обновить ПО или БД')
        # проверить что это БД Контрольного примера
        self.assertEqual(driver.find_element_by_id("ctl00_lb1").text, 'Контрольный пример -- тест:01 ТЕСТОВАЯ')
        # зайти в госуслуги и пробежать по всем меню
        # просмотр инф. с ПГУ
        driver.get(self.base_url +'VisitingService/ViewGosUsl.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Просмотр информации СМЭВ
        driver.get(self.base_url +'VisitingService/ViewSmev.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Массовое формирование запросов СМЭВ
        driver.get(self.base_url +'VisitingService/MassInputSmev.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Массовое удаление запросов СМЭВ
        driver.get(self.base_url +'VisitingService/MassDeleteSmev.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Загрузка ответов СМЭВ из файла
        driver.get(self.base_url+'VisitingService/ImportSmev.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Загрузка ответов СМЭВ из точки интеграции
        # пока ошибку не поправят!
        #driver.get(addr+'Reports/Gosuslugi_Import.aspx')
        #driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Выгрузка на точку интеграции
        driver.get(self.base_url+'Reports/SocPortal.aspx?Action=Export')
        driver.find_element_by_id("ctl00_cph_LB_Exit").click()
        # Массовая корректировка ПКУ запросами СМЭВ
        driver.get(self.base_url+'VisitingService/MassCorrSmev.aspx')
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # Настройка СМЭВ
        driver.get(self.base_url+'VisitingService/SettingSmev.aspx')
        driver.find_element_by_css_selector("#ctl00_cph_btnExit > img").click()
        driver.find_element_by_xpath("//form[@id='aspnetForm']/table/tbody/tr/td[3]/a[4]/img").click()
        # проверка что это логин
        self.assertEqual(driver.find_element_by_id("tdUserName").text, 'Имя', 'При входе на странице логина не удалось найти текст Имя')
        self.assertEqual(driver.find_element_by_id("tdPassword").text, 'Пароль', 'При входе на странице логина не удалось найти текст Пароль')


    def test_2(self):
        """Заходит в меню просмотр информации СМЭВ, проверяет в нем различные элементы на странице"""
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewSmev.aspx")
        # проверка выпадающего списка регламент
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Без группировки")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"0\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Регламент")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"1\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Дата запроса")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"2\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Организация")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"3\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Регламент + Организация")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"4\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Статус ответа")
        driver.find_element_by_css_selector("option[value=\"5\"]").click()
        Select(driver.find_element_by_id("ctl00_cph_ddlGroup")).select_by_visible_text(u"Регламент")
        driver.find_element_by_css_selector("#ctl00_cph_ddlGroup > option[value=\"1\"]").click()
        # проверка выпадающего списка фильтр
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_css_selector("#ctl00_cph_wpFilter_lbtnFilterReglam > img").click()
        driver.find_element_by_id("ctl00_cph_CheckBoxList3_0").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit2").click()
        driver.find_element_by_css_selector("#ctl00_cph_wpFilter_lbtnFilterOrg > img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit").click()
        driver.find_element_by_css_selector("#ctl00_cph_wpFilter_lbtnFilterRayonOrg > img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit2").click()
        driver.find_element_by_css_selector("#ctl00_cph_wpFilter_lbtnFilterRayonReq > img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit2").click()
        driver.find_element_by_css_selector("#ctl00_cph_wpFilter_lbtnFilterUserReq > img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit2").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_chblStatusAnswer_0").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()
        driver.find_element_by_css_selector(u"img[title=\"Отменить фильтр\"]").click()
        # проверка выпадающего списка печать
        driver.find_element_by_id("ctl00cphwpPrint_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Date_Req").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_FIO").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_PKU_KO").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Reglam").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Org").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Org").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Reglam").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_PKU_KO").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_FIO").click()
        driver.find_element_by_id("ctl00_cph_wpPrint_chkPrint_Date_Req").click()
        driver.find_element_by_id("ctl00cphwpPrint_header_img").click()
        # проверка листалки
        driver.find_element_by_css_selector(u"img[title=\"Следующая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Следующая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Последняя страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Предыдущая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Предыдущая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Первая страница\"]").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_3(self):
        """делает настройки для соединения с райнами в БД Контрольный пример для СМЭВ и ЛК."""
        con = self.startConASP()
        cur = con.cursor()
        driver = self.driver
        allert = webdriver.common.alert.Alert(driver)
        # удаляем старые настройки для ТИ и ЛК
        driver.get(self.base_url + "VisitingService/SettingSmev.aspx")
        driver.find_element_by_id("ctl00cphwpWSAuth_header_img").click()

        # очищаю строчку с адресом СМЭВ
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_SP").clear()
        # захожу в настройки СМЭВ
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnUserSet_SP").click()
        # снимаю галочку с района
        checkBox = driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_chk")
        if checkBox.is_selected():
            # если выбран, снимаю
            checkBox.click()
        # нажимаю сохранить
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_lbtnUsersSave > b > b").click()
        # очищаю строчку с адресом ЛК
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_LK").clear()
        # захожу в настройки ЛК
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnUserSet_LK").click()
         # снимаю галочку с района
        checkBox = driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_chk")
        if checkBox.is_selected():
            # если выбран, снимаю
            checkBox.click()
        # нажимаю сохранить
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_lbtnUsersSave > b > b").click()
        # выхожу из задачи с сохранением
        driver.find_element_by_id("ctl00_cph_lbtnExitSave").click()
        # окно предупреждение
        if allert.text == 'Изменение существующего регламента без его переименования может повлиять на существующие запросы!\nПродолжить без переименования?':
            allert.accept()
        else:
            self.fail('При сохранении настроек для СМЭВ и ЛК появилось окно предупреждения с неизвестным текстом: %s\n' % allert.text)
        # закончили очистку настроек, надо проверить
        # снова захожу
        driver.get(self.base_url + "VisitingService/SettingSmev.aspx")
        driver.find_element_by_id("ctl00cphwpWSAuth_header_img").click()
        # проверяю
        res = cur.execute("exec GetSett 0,'WebService_Authentification',0")
        hash = hashlib.md5(res.fetchone()[0].encode()).hexdigest()
        self.assertEqual(hash, 'ce9fe549c988ec711f110e158d1248ab', 'Настройки БД не очищенны. Получен hash класса настроек: %s' % hash)
        # заполняю СМЭВ
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_SP").clear()
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_SP").send_keys("http://tu:2121/SocPortal/Export.asmx")
        # проверка соединения cо СМЭВ
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnCheckWSServiceURL_SP").click()
        if allert.text == 'Подключение к веб-сервису прошло успешно!':
            allert.accept()
        else:
            self.fail('При сохранении настроек для СМЭВ и ЛК появилось окно предупреждения с неизвестным текстом: %s' % allert.text)
        # заполняю ЛК
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_LK").clear()
        driver.find_element_by_id("ctl00_cph_wpWSAuth_tbWSServiceURL_LK").send_keys("http://tu:2121/SocPortal1/Export.asmx")
        # проверка соединения с ЛК
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnCheckWSServiceURL_LK").click()
        if allert.text == 'Подключение к веб-сервису прошло успешно!':
            allert.accept()
        else:
            self.fail('При сохранении настроек для СМЭВ и ЛК появилось окно предупреждения с неизвестным текстом: %s' % allert.text)
        # настраиваю соединение для СМЭВ УСЗН по Шелаболихинскому району pas53
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnUserSet_SP").click()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_chk").click()
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_lbWSChooseUser > img").click()
        # заход в справочник районов
        driver.find_element_by_css_selector("#ctl00_cph_pgr__wibBottomPage > img").click()
        driver.find_element_by_id("ctl00_cph_Chk159").click()
         # в начало справочника
        driver.find_element_by_css_selector("img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit").click()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_tbWSPassword").clear()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_tbWSPassword").send_keys("pas53")
        # проверка пароля
        driver.find_element_by_css_selector("b > b").click()
        if allert.text == 'Проверка прошла успешно!':
            allert.accept()
        else:
            self.fail('При проверке пароля для СМЭВ получено предупреждение с неизвестным текстом: %s' % allert.text)
        # нажимаю сохранить
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_lbtnUsersSave > b > b").click()
        # настройка для ЛК ЭНСК 12345
        driver.find_element_by_id("ctl00_cph_wpWSAuth_btnUserSet_LK").click()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_chk").click()
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_lbWSChooseUser > img").click()
        # заход в справочник районов
        # в конец справочника
        driver.find_element_by_css_selector("#ctl00_cph_pgr__wibBottomPage > img").click()
        # выбор
        driver.find_element_by_id("ctl00_cph_Chk17").click()
        # в начало справочника
        driver.find_element_by_css_selector("img").click()
        driver.find_element_by_id("ctl00_cph_Imagebutton_Exit").click()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_tbWSPassword").clear()
        driver.find_element_by_id("ctl00_cph_pwSettingUsers_gwSettingUsers_ctl02_tbWSPassword").send_keys("12345")
        # проверка пароля
        driver.find_element_by_css_selector("b > b").click()
        if allert.text == 'Проверка прошла успешно!':
            allert.accept()
        else:
            self.fail('При проверке пароля для СМЭВ получено предупреждение с неизвестным текстом: %s' % allert.text)
        # нажимаю сохранить
        driver.find_element_by_css_selector("#ctl00_cph_pwSettingUsers_lbtnUsersSave > b > b").click()
        # выход из задачи
        driver.find_element_by_css_selector("#ctl00_cph_lbtnExitSave > img").click()
        # окно предупреждение
        if allert.text == 'Изменение существующего регламента без его переименования может повлиять на существующие запросы!\nПродолжить без переименования?':
            allert.accept()
        else:
            self.fail('При сохранении настроек для СМЭВ и ЛК появилось окно предупреждения с неизвестным текстом: %s\n' % allert.text)
        # проверка, что настройки сохранились
        # проверяю
        res = cur.execute("exec GetSett 0,'WebService_Authentification',0")
        hash = hashlib.md5(res.fetchone()[0].encode()).hexdigest()
        self.assertEqual(hash, '3ffbdfc67582f99ba36f7fd9dc5bb368','Настройки БД не сохранелись. Получен hash класса настроек: %s' % hash)
        # выход из asp
        driver.find_element_by_xpath("//form[@id='aspnetForm']/table/tbody/tr/td[3]/a[4]/img").click()


    def test_4(self):
        """ Пытается принять заявку (хотя ее нет) и пройти по этапам ее обработки """

        driver = self.driver
        # заходит в просмотр ПГУ/МФЦ
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # пройти по операциям, чтобы убедится что они открываются (1,3,4)

        # звязывание ПКУ(1)
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_Exit > img").click()

        # запись заявок(3)
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()
        driver.find_element_by_id("ctl00_cph_lbtnReturn__5").click()

        # карточки обращения(4)
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnMassRegVisitCard").click()
        driver.find_element_by_id("ctl00_cph_btnExit").click()

        # листалка
        driver.find_element_by_css_selector(u"img[title=\"Следующая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Следующая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Предыдущая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Предыдущая страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Последняя страница\"]").click()
        driver.find_element_by_css_selector(u"img[title=\"Первая страница\"]").click()
        # выход
        driver.find_element_by_id("ctl00_cph_btnExit").click()

        # снова вход в задачу
        # заходит в просмотр ПГУ/МФЦ
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # запись скандоков(2) должна выполнится быстро, на тесте - 2 сек, т.к. все заявления удалены
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetScandoc").click()
        # прогресс бар
        for i in range (0,4):
            sl = 5
            time.sleep(sl)
            try:
                driver.find_element_by_id("ctl00_cph_AJBarViewGosUsl_ProgressDiv2_AJStopBtn").click()
                break
            except:
                self.fail("Предупреждение! Попытка № %s Прогресс-бар при записи скандоков не отработал за 5 сек. "
                          "Должен работать за 2 сек, т.к. заявлений нет." % i)
        # диалог сохранения файлов
        driver.find_element_by_id("ctl00_cph_AJTran1_PopupDiv_CloseButton").click()
        # выход
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_5(self):
        """ Принимает Заявки на получение льгот на оплату жилья и ЖКУ (ГСП=Льготы на оплату жилья и ЖК услуги)
        :return:
        """
        conASP = self.startConASP()
        curASP = conASP.cursor()
        # удалеяе в АСП все не обработанные заявления
        curASP.execute("""delete EService_Response where eService_Request_id in (select id from EService_Request where f6_id is NULL and f6izm_id is NULL)
    delete EService_Scandoc where eService_Request_id in (select id from EService_Request where f6_id is NULL and f6izm_id is NULL)
    delete EService_Request where f6_id is NULL and f6izm_id is NULL""")
        conASP.commit()
        # удаляю на ТИ
        conTI = self.startConTI()
        curTI = conTI.cursor()
        # закомментировать тут
        curTI.execute("""
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
        conTI.commit()
        # удаляю ответы на заявку на ТИ
        curTI.execute("select id from EService_request where lastName=? and firstName=? and middleName=?", ("Данилов", "Борис", "Петрович"))
        idList = list()
        for id in curTI.fetchall():
            idList.append(str(id[0]))
        es_id = ','.join(idList)
        curTI.execute("delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
        curTI.execute("delete EService_Response where eService_Request_id in (%s)" %  es_id)
        conTI.commit()
        # удаляю заявку из госуслуг
        # удалить заявку в из ПКУ
        curASP.execute("select id from F2 where FAMIL=? and IMJA=? and OTCH=?", ("Данилов", "Борис", "Петрович"))
        idList = list()
        for id in curASP.fetchall():
            idList.append(str(id[0]))
        f2_id = ','.join(idList)
        curASP.execute("select id from EService_Request where F2_ID in (?)",(f2_id,))
        idList = list()
        for id in curASP.fetchall():
            idList.append(str(id[0]))
        es_id = ','.join(idList)
        if es_id == "":
            es_id = '0'
        curASP.execute("delete EService_Scandoc where EService_Response_id in (select id from EService_Response where eService_Request_id in (%s))" % es_id)
        curASP.execute("delete EService_Response where eService_Request_id in (%s)" %  es_id)
        curASP.execute("delete EService_Scandoc where eService_Request_id in (%s)" % es_id)
        conASP.commit()
        curASP.execute("""DELETE F6IZM_DOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
        (select id from F6 where F2_ID in (?)))""", (f2_id,))
        curASP.execute("""DELETE F6LDOKUM WHERE f6izm_id in (select id from F6IZM where F6_ID in
        (select id from F6 where F2_ID in (?)))""", (f2_id,))
        curASP.execute("""DELETE F6LGKYSL WHERE f6izm_id in (select id from F6IZM where F6_ID in
        (select id from F6 where F2_ID in (?)))""", (f2_id,))
        curASP.execute("""DELETE F6IZM where F6_ID in (select id from F6 where F2_ID in (?))""", (f2_id,))
        curASP.execute("delete EService_Request where F2_ID in (?)", (f2_id,))
        curASP.execute("""delete F6 where F2_ID in (?)""", (f2_id,))
        curASP.execute("delete F_SCANDOC where F2_ID in (?)", (f2_id,))
        conASP.commit()
        # заходит в просмотр ПГУ/МФЦ
        driver = self.driver
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # получить заявления
        driver.find_element_by_id("ctl00_cph_lbtnImport").click()
        driver.find_element_by_id("ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal").click()
        # подождать, когда отработает прогресс бар
        for i in range(60):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
        else:
            self.fail("Не дождался окончания загрузки заявления в 1-м случае")

        # теперь нужно заявление обновить на ТИ
        curTI.execute("""-- номер района
declare @id int = 159
-- отметить все заявки района как не загруженную
update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and requestId='10734214222'""")
        conTI.commit()
        # выходим в просмотр госуслуг
        driver.find_element_by_css_selector("#ctl00_cph_LB_Exit > img").click()
        # пробуем снова загрузить заявление
        driver.find_element_by_id("ctl00_cph_lbtnImport").click()
        driver.find_element_by_id("ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal").click()
        # подождать, когда отработает прогресс бар
        for i in range(60):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        else:
            self.fail("Не дождался окончания загрузки заявления в 2-м случае.")
        time.sleep(1)
        # проверить что вышло сообщение с результатами загрузки
        time.sleep(1)
        c = driver.find_element_by_xpath("//span[@id='ctl00_cph_L_Res']/strong[6]").text
        if c != '1':
            self.fail("Хотел загрузить только одно заявление, вместо него приехало: %s" % c)

        # проверить что заявка в БД
        nom = '10734214222'
        res = curASP.execute("select f6_id, f6izm_id from eService_Request where requestId=?", (nom,)).fetchall()
        if len(res) == 1:
            if res[0][0] == None and res[0][1] == None:
                #print('Заявка записалась успешно')
                pass
            else:
                self.fail('ОШИБКА! При записи заявления F6_ID=%s, F6IZM_ID=%s\n' % (res[0][0], res[0][1]))
        else:
            self.fail('ОШИБКА! Нашлось %s заявок с номером %s. Должна быть одна.\n' % (len(res), nom))

        driver.find_element_by_css_selector("#ctl00_cph_LB_Exit > img").click()
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys("Данилов")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys("Борис")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys("Петрович")
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()

        # запись скандоков
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetScandoc").click()
        for i in range(60):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
        else:
            self.fail('Не дождался записи скандоков во 2-м случае.')
        driver.find_element_by_id("ctl00_cph_AJTran1_PopupDiv_CloseButton").click()
        # запись заявлений
        time.sleep(1)
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()
        # Сформировани список
        driver.find_element_by_id("ctl00_cph_lbtnCreateSpisok").click()
        for i in range(3):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except: pass
        else:
            self.fail("Не удалось дождаться окна Массовая рег. заявок")
        time.sleep(1)
        # вот тут надо нажать на 1, в списке
        driver.find_element_by_id("ctl00_cph_pnlVidSpiska_Lbn1").click()
        driver.find_element_by_css_selector("#ctl00_cph_pnl_ViewInfo_lbtnSave > img").click()
        # подождем прогресс запись заявок в БД
        for i in range(3):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться записи заявок")
        # выйти из записи
        driver.find_element_by_id("ctl00_cph_lbtnGoBack__4").click()

        # проверить что заявка в БД
        nom = '10734214222'
        res = curASP.execute("select f6_id, f6izm_id from eService_Request where requestId=?", (nom,)).fetchall()
        if len(res) == 1:
            if res[0][0] and res[0][1]:
                #print('Заявка зарегистрированна успешно')
                pass
            else:
                self.fail('ОШИБКА! При после регистрации заявления F6_ID=%s, F6IZM_ID=%s\n' % (res[0][0], res[0][1]))
        else:
            self.fail('ОШИБКА! Нашлось %s заявок с номером %s. Должна быть одна.\n' % (len(res), nom))

        # выйти их массой регистрации
        driver.find_element_by_id("ctl00_cph_lbtnReturn__4").click()
        # войти в заявку
        driver.find_element_by_id("ctl00_cph_grdMain_ctl02_lbtnGotoZayv").click()
        # переключение на таб госуслуги
        driver.find_element_by_id("ctl00_cph_lbtab10").click()
        # новый ответ
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
        Select(driver.find_element_by_id("ctl00_cph_guResp1_ddlStatus")).select_by_visible_text("Отказ")
        driver.find_element_by_css_selector("option[value=\"4\"]").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys("Это тестовый статус на ОТКАЗ на заявление №10734214222")
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc > img").click()
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").send_keys("/home/alexey/Desktop/Файл с пробелом.jpg")
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_btnOk > b > b").click()
        # жду загрузки файла
        for i in range(3):
            try:
                driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_SaveExit").click()
                break
            except:
                pass

        else:
            self.fail("Ошибка! Не удалось дождаться появления кнопки выход (с дверью).")

        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        conTI.close()
        conASP.close()


    def test_6(self):
        """Загружает второе заявление, которое ляжет как обращение к первому и проверяет, что получилось в БД АСП"""
        # соединение с БД АСП
        conASP = self.startConASP()
        curASP = conASP.cursor()
        # соединение с БД ТИ
        conTI = self.startConTI()
        # на ТИ готовит заявление к загрузке
        curTI = conTI.cursor()
        nom = '12744214221'
        curTI.execute("""-- номер района
    declare @id int = 159
    -- отметить все заявки района как не загруженную
    update EService_Request set exportDate=NULL, exportFile=NULL where EService_Users_id = @id and requestId=?""", (nom,))
        conTI.commit()
        driver = self.driver
        # заходит в просмотр ПГУ/МФЦ
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
        else:
            self.fail("Не дождался окончания загрузки заявления.")
        # проверить что вышло сообщение с результатами загрузки
        c = driver.find_element_by_xpath("//span[@id='ctl00_cph_L_Res']/strong[6]").text
        if c != '1':
            self.driver("Хотел загрузить только одно заявление, вместо него приехало: %s" % c)

        # проверить что заявка в БД
        res = curASP.execute("select f6_id, f6izm_id from eService_Request where requestId=?", (nom,)).fetchall()
        if len(res) == 1:
            if res[0][0] == None and res[0][1] == None:
                #print('Заявка записалась успешно')
                pass
            else:
                self.fail('ОШИБКА! При записи заявления F6_ID=%s, F6IZM_ID=%s\n' % (res[0][0], res[0][1]))
        else:
            self.fail('ОШИБКА! Нашлось %s заявок с номером %s. Должна быть одна.\n' % (len(res), nom))
        # выход из задачи загрузки заявлений
        driver.find_element_by_css_selector("#ctl00_cph_LB_Exit > img").click()
        # связывание с ПКУ
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBindingPeopleAndPku").click()
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnBind").click()
        driver.find_element_by_css_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit > img").click()
        # устанавливаю фильтр
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys("Данилов")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys("Борис")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys("Петрович")
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()
        time.sleep(1)
        # запись скандоков
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetScandoc").click()
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        else:
            self.fail('Не дождался записи скандоков во 2-м случае.')
        driver.find_element_by_id("ctl00_cph_AJTran1_PopupDiv_CloseButton").click()
        # запись заявлений
        time.sleep(1)
        driver.find_element_by_id("ctl00_cph_wpOper_lbtnSetZayv").click()
        # Сформировани список. тут падает, если нет жилищных условий
        time.sleep(1)
        driver.find_element_by_id("ctl00_cph_lbtnCreateSpisok").click()
        for i in range(10):
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

        # проверить что заявка в БД
        res = curASP.execute("select f6_id, f6izm_id from eService_Request where requestId=?", (nom,)).fetchall()
        if len(res) == 1:
            if res[0][0] and res[0][1]:
                #print('Заявка зарегистрированна успешно')
                pass
            else:
                self.fail('ОШИБКА! При после регистрации заявления F6_ID=%s, F6IZM_ID=%s\n' % (res[0][0], res[0][1]))
        else:
            self.fail('ОШИБКА! Нашлось %s заявок с номером %s. Должна быть одна.\n' % (len(res), nom))

        # выйти их массой регистрации
        driver.find_element_by_id("ctl00_cph_lbtnReturn__4").click()
        # войти в заявку
        driver.find_element_by_id("ctl00_cph_grdMain_ctl02_lbtnGotoZayv").click()
        # переключение на таб госуслуги
        driver.find_element_by_id("ctl00_cph_lbtab10").click()
        # новый ответ
        driver.find_element_by_id("ctl00_cph_guResp1_lbtnNewResponse").click()
        time.sleep(1)
        Select(driver.find_element_by_id("ctl00_cph_guResp1_ddlStatus")).select_by_visible_text("Исполнено")
        driver.find_element_by_css_selector("option[value=\"3\"]").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").click()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys("Это тестовый статус ИСПОЛНЕНО на заявление №%s" % nom)
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc > img").click()
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").send_keys("/home/alexey/Desktop/7NAabNgvl0Q.jpg")
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_btnOk > b > b").click()
        # жду загрузки файла и выхожу
        for i in range(60):
            try:
                driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_SaveExit").click()
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться загрузки файла")
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # проверяю, что есть такой гражданин
        f2_id = curASP.execute("select id from F2 where FAMIL=? and IMJA=? and OTCH=?", ("Данилов", "Борис", "Петрович")).fetchone()
        if f2_id:
            docs = curASP.execute("select filename from F_SCANDOC where F2_ID=%s" % f2_id).fetchall()
            sd = ''
            for doc in docs:
                sd += doc[0]+';'
            #print('Список скандоков:', sd)
            # сравнение с образцом
            obr = 'infoPGU10734214222.txt;Военный билет.pdf;Заявление о возмещении расходов на оплату проезда.pdf;Паспорт гражданина Российской Федерации.pdf;Пенсионное удостоверение.pdf;Реквизиты счета.pdf;Свидетельство о праве на льготы.pdf;infoPGU12744214221.txt;'
            #print('Список скан. обр:', obr)
            self.assertEqual(sd, obr, 'Список сканированных документов записанных человеку не совпадает с образцом')
            f6 = curASP.execute('select count(id) from F6 where F2_ID=?', f2_id).fetchone()[0]
            self.assertEqual(f6, 1, 'Ошибка! Вместо одной заявки было создано: %s' % f6)
            f6izm = curASP.execute("select count(id) from F6IZM where F6_ID in (select id from F6 where F2_ID in (select id from F2 where FAMIL=? and IMJA=? and OTCH=?))", ("Данилов", "Борис", "Петрович")).fetchone()[0]
            self.assertEqual(f6izm, 2, 'Ошибка! Вместо 2-х обращений было создано: %s\n' % f6izm)
        else:
            self.fail('Ошибка! Гражданин Данилов Борис Петрович не создан с БД')
        # закомментировать тут
        # проверить какие ответы даны
        good = """1) Статус: 2, комментарий: None
2) Статус: 3, комментарий: Это тестовый статус ИСПОЛНЕНО на заявление №%s
Приложены файлы: 7NAabNgvl0Q.jpg
""" % nom
        curASP.execute("select id, state, info from EService_Response where eService_Request_id in (select id from EService_Request where requestId=?) order by id", (nom,))
        i = 1
        bad = ''
        for resp in curASP.fetchall():
            bad += ('%s) Статус: %s, комментарий: %s\n') % (i, resp[1], resp[2])
            i += 1
        curASP.execute("select filename from eservice_scandoc where eService_Request_id in (select id from EService_Request where requestId=?) and isResponse = 1", (nom,))
        res = curASP.fetchall()
        if res:
            bad += 'Приложены файлы: ' + ', '.join(res[0])+'\n'
        else:
            bad += 'Приложенных файлов нет.\n'

        self.assertEqual(bad, good, 'На заявление даны не правильные ответы.  Есть ответы:\n%sОбразец:\n%s' % (bad, good))
        conASP.close()
        conTI.close()


    def test_7(self):
        """"Проверяет чтобы при переключении обращения внутри заявления срабатывало переключение контрола госуслуги и
        отображался статус, комментарий и файл для соответствующей заявки ПГУ/МФЦ."""
        nom = '12744214221'
        driver = self.driver
        # заходит в просмотр ПГУ/МФЦ
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливает фильтр по ФИО, а мало ли что там стоит
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys("Данилов")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys("Борис")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys("Петрович")
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()
        # зайти в заявку
        driver.find_element_by_id("ctl00_cph_grdMain_ctl02_lbtnGotoZayv").click()
        """ эта часть проверяет заявление с №10734214222.
        Статус = Отказ,
        Комментарий = Это тестовый статус на ОТКАЗ на заявление №10734214222
        Приложен один файл: Файл с пробелом.jpg
        """
        # переключение на таб госуслуги
        driver.find_element_by_id("ctl00_cph_lbtab10").click()

        # выбрать для проверка обращение от 03.03.2016
        veryf = dict(status='Отказ',
                     comment='Это тестовый статус на ОТКАЗ на заявление №10734214222',
                     file='Файл с пробелом.jpg',
                     nom='10734214222')
        driver.find_element_by_id("x:1276916731.4:mkr:ButtonImage").click()
        driver.find_element_by_xpath("//li[@id='x:1276916731.9:adr:1']/table/tbody/tr/td[2]").click()
        time.sleep(2)
        # проверить комментаний (надо исправить на НАЗНАЧЕНО)
        self.assertEqual(driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text, veryf['comment'],
            'ОШИБКА при проверке заявления №%s! Вместо комментария <%s> нашли <%s>' % \
            (veryf['nom'], veryf['comment'], driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text))
        # проверить файл
        fileName = driver.find_element_by_xpath("//table[@id='ctl00_cph_guResp1_InpScDoc_grdScanDoc']/tbody/tr[2]/td[2]").text
        self.assertEqual(fileName, veryf['file'],
            'ОШИБКА при проверке заявления №%s! Вместо <%s> прикреплен <%s>' % (veryf['nom'], veryf['file'], fileName))
        # проверить статус
        status = Select(driver.find_element_by_id('ctl00_cph_guResp1_ddlStatus'))
        self.assertEqual(status.first_selected_option.text, veryf['status'],
            'ОШИБКА при проверке заявления №%s! Вместо статуса <%s> нашли <%s>\n' %
                         (veryf['nom'], veryf['status'], status.first_selected_option.text))

        # выбрать для проверка обращение от 17.03.2016
        veryf = dict(status='Исполнено',
                     comment='Это тестовый статус ИСПОЛНЕНО на заявление №12744214221',
                     file='7NAabNgvl0Q.jpg',
                     nom='12744214221')
        driver.find_element_by_id("x:1276916731.4:mkr:ButtonImage").click()
        driver.find_element_by_css_selector("td.List_FieldAccent").click()
        time.sleep(2)
        # проверить комментаний
        if driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text != veryf['comment']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо комментария <%s> нашли <%s>\n' % \
               (veryf['nom'], veryf['comment'], driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text))
        # проверить файл
        if driver.find_element_by_xpath("//table[@id='ctl00_cph_guResp1_InpScDoc_grdScanDoc']/tbody/tr[2]/td[2]").text != veryf['file']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо <%s> прикреплен <%s>\n ' % \
               (veryf['nom'], veryf['file'], driver.find_element_by_xpath("//table[@id='ctl00_cph_guResp1_InpScDoc_grdScanDoc']/tbody/tr[2]/td[2]").text))
        # проверить статус
        status = Select(driver.find_element_by_id('ctl00_cph_guResp1_ddlStatus'))
        if status.first_selected_option.text != veryf['status']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо статуса <%s> нашли <%s>\n' % \
                   (veryf['nom'], veryf['status'], status.first_selected_option.text))

        # выход из заявки
        driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_SaveExit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()


    def test_8(self):
        """ Проверяе известную ошибку, когда при смене комментария для не отправленного решения сбрасывается его статус.
        Тест проверяет, чтобы этого не происходило."""

        nom = '10734214222'
        driver = self.driver
        # заходит в просмотр ПГУ/МФЦ
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # устанавливает фильтр по ФИО, а мало ли что там стоит
        driver.find_element_by_id("ctl00cphwpFilter_header_img").click()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterFamil").send_keys("Данилов")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterImja").send_keys("Борис")
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").clear()
        driver.find_element_by_id("ctl00_cph_wpFilter_filterOtch").send_keys("Петрович")
        driver.find_element_by_id("ctl00_cph_wpFilter_btnSetFilter").click()

        # зайти в заявку
        driver.find_element_by_id("ctl00_cph_grdMain_ctl02_lbtnGotoZayv").click()
        """ эта часть проверяет заявление с №10734214222.
        Статус = Отказ,
        Комментарий = Это тестовый статус на ОТКАЗ на заявление №10734214222
        Приложен один файл: Файл с пробелом.jpg
        """
        # переключение на таб госуслуги
        driver.find_element_by_id("ctl00_cph_lbtab10").click()

        # выбрать для проверка обращение от 03.03.2016
        veryf = dict(status='Отказ',
                     comment='Это повторный тестовый статус ОТКАЗ на заявление №%s' % nom,
                     file='Голавль.jpg',
                     nom='10734214222')
        driver.find_element_by_id("x:1276916731.4:mkr:ButtonImage").click()
        driver.find_element_by_xpath("//li[@id='x:1276916731.9:adr:1']/table/tbody/tr/td[2]").click()
        # сменить комментарий
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").send_keys("Это повторный тестовый статус ОТКАЗ на заявление №%s" % nom)
        # удалить файл
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_grdScanDoc_ctl02_lbtnDelete").click()
        # нажать добавить файл
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc").click()
        # выбрать файл с лок. машины
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").clear()
        driver.find_element_by_id("ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_FileUploader").send_keys("/home/alexey/Desktop/Голавль.jpg")
        # нажать загрузить
        driver.find_element_by_css_selector("#ctl00_cph_guResp1_InpScDoc_InputFile_wndInputFile_btnOk > b > b").click()
        # подождать окончание загрузки
        for i in range(10):
            try:
                driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_SaveExit")
                break
            except: pass
            time.sleep(1)
        else:
            self.fail("Не удалось дождаться загрузки файла")

        # проверить комментаний
        if driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text != veryf['comment']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо комментария <%s> нашли <%s>\n' % \
                   (veryf['nom'], veryf['comment'], driver.find_element_by_id("ctl00_cph_guResp1_tbGosUsl_Coment").text))
        # проверить файл
        if driver.find_element_by_xpath("//table[@id='ctl00_cph_guResp1_InpScDoc_grdScanDoc']/tbody/tr[2]/td[2]").text != veryf['file']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо <%s> прикреплен <%s>\n ' % \
                   (veryf['nom'], veryf['file'], driver.find_element_by_xpath("//table[@id='ctl00_cph_guResp1_InpScDoc_grdScanDoc']/tbody/tr[2]/td[2]").text))
        # проверить статус
        status = Select(driver.find_element_by_id('ctl00_cph_guResp1_ddlStatus'))
        if status.first_selected_option.text != veryf['status']:
            self.fail('ОШИБКА при проверке заявления №%s! Вместо статуса <%s> нашли <%s>\n' % \
                   (veryf['nom'], veryf['status'], status.first_selected_option.text))
        # выход из заявки без сохранения, данные остаются старыми!
        driver.find_element_by_id("ctl00_cph_TopStr_lbtnTopStr_Exit").click()
        # выход в главное
        driver.find_element_by_id("ctl00_cph_btnExit").click()
        # снова проверяю какой статус по этому заявлению в БД, должна остаться старая информация
        # соединение с БД АСП
        conASP = self.startConASP()
        curASP = conASP.cursor()
        # проверяю что в БД
        nom = '10734214222'
        good = list()
        good.append(dict(status=2, comment=None, file=None))
        good.append(dict(status=4, comment='Это тестовый статус на ОТКАЗ на заявление №10734214222', file='Файл с пробелом.jpg'))
        curASP.execute("select id, state, info from EService_Response where eService_Request_id in (select id from EService_Request where requestId=?) order by id", (nom,))
        bad = list()
        respAll = curASP.fetchall()
        for resp in respAll :
            bad.append(dict(status=resp[1], comment=resp[2]))
        if(len(good) == len(bad)):
            # проверяем статусы и комментарии
            for i in range(0, len(bad)):
                if bad[i]['status']!=good[i]['status'] or  bad[i]['comment']!=good[i]['comment']:
                    self.fail('ОШИБКА! при записи решения по заявлению ПГУ. Образец - статус %s, комментарий %s. '
                            'Записано - статус %s, комментарий %s' % (good[i]['status'], good[i]['comment'], bad[i]['status'], bad[i]['comment']))
        else:
            self.fail('ОШИБКА! При проверке решений по заявлению ПГУ/МФЦ длина списка образцой не совпадает с фактически полученным')
        # проверяю приложенные файлы
        goodFile = 'Файл с пробелом.jpg'
        curASP.execute("select filename from eservice_scandoc where eService_Request_id in (select id from EService_Request where requestId=?) and isResponse = 1", (nom,))
        res = curASP.fetchall()
        badFile = None
        if res:
            badFile = '; '.join(res[0])

        if badFile == goodFile:
            #print('Проверка файлов прошла успешно')
            pass
        else:
            self.fail('ОШИБКА! Есть файлы: %s\nОбразец: %s' % (badFile, goodFile))
        conASP.close()


    def test_9(self):
        """Проверяет ошибку, когда при смене комментария для не отправленного решения сбрасывается его статус. Тест проверяет, чтобы этого не происходило."""
        driver = self.driver
        # соединяется с БД АСП
        conASP = self.startConASP()
        curASP = conASP.cursor()
        # проверим состояние файла ответа до выгрузки для заявления 12744214221
        good =  dict(
                numer='12744214221',
                status='Исполнено',
                file='7NAabNgvl0Q.jpg',
                comment='Это тестовый статус ИСПОЛНЕНО на заявление №12744214221',
                save=None)
        msg = self.otvetCheck(curASP, good)
        if msg:
            self.fail(msg)

        # проверим состояние файла ответа до выгрузки для заявления 10734214222
        good = dict(
                numer='10734214222',
                status='Отказ',
                file='Файл с пробелом.jpg',
                comment='Это тестовый статус на ОТКАЗ на заявление №10734214222',
                save=None)
        msg = self.otvetCheck(curASP, good)
        if msg:
            self.fail(msg)
        # захожу в просмотр ПГУ/МФЦ
        driver.get(self.base_url + "VisitingService/ViewGosUsl.aspx")
        # захожу в выгрузку на ТИ
        driver.find_element_by_id("ctl00_cph_lbtnExport").click()
        # снимаю галочки для выгрузки всего
        checkIdList = ('ctl00_cph_CB_PKU','ctl00_cph_CB_State', 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV')
        for ID in checkIdList:
            checkBox = driver.find_element_by_id(ID)
            if checkBox.is_selected():
                # если выбран, снимаю
                checkBox.click()
        # ставлю галочку на статусы ПГУ
        driver.find_element_by_id('ctl00_cph_CB_State').click()
        # проверяю, что их 2 шт.
        st = driver.find_element_by_id('ctl00_cph_lbl_State_cnt').text
        if st != '2':
            self.fail('ОШИБКА! Кол-во статусов к выгрузке %s, ожидается 2.' % st)
        # перейти на выгрузку с помощью веб-сервиса
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td1').click()
        # нажимаю отправить
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl1_lbSendFilePortal').click()
        # подождать, когда отработает прогресс бар
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        else:
            self.fail("Не дождался окончания выгрузки статусов ПГУ/МФЦ на ТИ")
        # проверить, что по результатам выгрузки, оба должны выгрузится нормально и проставится время выгрузки
        curASP.execute("""SELECT count(id) FROM EService_Response where EService_Request_id
in (select id from EService_request where lastName=? and firstName=? and middleName=?)
and date_Response is not NULL""", ("Данилов", "Борис", "Петрович"))
        st = curASP.fetchone()[0]
        if st != 4:
            msg += 'ОШИБКА! Должно нормально выгрузится 4 статуса, а выгрузилось %s\n' % st
        # проверим состояние файла ответа после выгрузки для заявления 12744214221
        if driver.get_screenshot_as_file('image/t9.png'):
            msg += 'Сделан скриншот - http://192.168.0.104/image/t9.png'
        good =  dict(
                numer='12744214221',
                status='Исполнено',
                file='7NAabNgvl0Q.jpg',
                comment='Это тестовый статус ИСПОЛНЕНО на заявление №12744214221',
                save=1)
        msg = self.otvetCheck(curASP, good)
        if msg:
            self.fail(msg)

        # проверим состояние файла ответа после выгрузки для заявления 10734214222
        good = dict(
                numer='10734214222',
                status='Отказ',
                file='Файл с пробелом.jpg',
                comment='Это тестовый статус на ОТКАЗ на заявление №10734214222',
                save=1)
        msg = self.otvetCheck(curASP, good)
        if msg:
            self.fail(msg)
        conASP.close()


    def otvetCheck(self, cur, good):

        cur.execute("""select top 1 body from EService_Scandoc es
    inner join EService_Request req on req.id = es.eService_Request_id
    inner join EService_Response res on es.EService_Response_id = res.id
    where req.requestId = ? and es.filename like 'otvet.txt' order by res.date_Response""", (good['numer'],))
        bin = cur.fetchone()[0]
        fp = open('otvet.txt', mode='wb')
        fp.write(bin)
        fp.close()

        fp = open('otvet.txt', 'r')
        otvet = fp.read()
        fp.close()
        msg = ""
        # статус
        result = dict(status=None, file=None, comment=None, save=None, numer=good['numer'])
        p = re.compile(r'^Статус: (?P<status>.+$)', re.I|re.M|re.L)
        m = p.search(otvet)
        if m:
            result.update(m.groupdict())

        # файлы
        p = re.compile(r'^Приложенные файлы: (?P<file>.+$)', re.I|re.M|re.L)
        m = p.search(otvet)
        if m:
            result.update(m.groupdict())

        # комментарий
        p = re.compile(r'^Официальный ответ заявителю из ПКУ:\n(?P<comment>.+$)', re.I|re.M|re.L)
        m = p.search(otvet)
        if m:
            result.update(m.groupdict())
        # выгружено
        p = re.compile(r'^Выгружен: (?P<save>.+$)', re.I|re.M|re.L)
        m = p.search(otvet)
        if m:
            result.update(m.groupdict())
        for key in good.keys():
            if key == 'save':
                # проверяем только наличие даты
                if (good[key] is None and result[key] is None) or (good[key] and result[key]):
                    pass
                else:
                    msg += 'ОШИБКА! При проверке файла otvet.txt по заявлению %s. Образец %s, в ответе %s\n' % \
                       (good['numer'], good[key], result[key])
            else:
                if good[key] != result[key]:
                    msg += 'ОШИБКА! При проверке файла otvet.txt по заявлению %s. Образец %s, в ответе %s\n' % \
                       (good['numer'], good[key], result[key])

        return msg


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
        arh_name = 'fig/1/error_%s.png' % n
        while os.path.exists(arh_name):
           n +=1
           arh_name = 'fig/1/error_%s.png' % n
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)


if __name__ == '__main__':
    # Выполняется если файл запускается как программа
    unittest.main()

    exit(0)