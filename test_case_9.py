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
import test_1005
import config
import smev


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])


def delTI():
        """Удаляет загруженные ранее записи для 1005 сервиса по району 159"""
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД АСП")
            exit(1)
        cur = conTI.cursor()
        cur.execute("delete SMEV_SERVICE_TRANSPORT where eservice_users_id=159")
        conTI.commit()
        conTI.close()


def checkTI(people):
        """Возвращает сколько записей в таблице для 1005 найдено по человеку"""
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

            cur.execute("select count(id) from SMEV_SERVICE_TRANSPORT where famil=? and imja=? and OTCH=?", (people['lastName'], people['firstName'], people['middleName']))
            count = cur.fetchone()[0]
        except:
            print('При получении записей для %s %s %s скриптом возникли ошибки'
                  % (people['lastName'], people['firstName'], people['middleName']))
        conTI.close()
        return count


class case9(unittest.TestCase):
    """Проверяет сервис 1005 - льготы на проезд. Проверяет контрольные примеры, делает выгрузку по человеку, проверяет
    ответ по ФИО+ДР и по ФИО+ДР+Номер паспорта. """
    @staticmethod
    def setUpClass():
        # очистить папки
        dirList = ('fig/9/', 'Результаты/')
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)


    def setUp(self):
        pass


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

    #@unittest.skip('Временно пропущен')
    def test_1_kp(self):
        """Направляет запрос на контрольные примеры"""
        post = test_1005.test_1005(TI)
        self.assertEqual(post['errors'], 0, 'При выполнении контрольных примеров к 1005 сервису возникли ошибки. %s' % TI['adr'])


    #@unittest.skip('Временно пропущен')
    def test_2_ask1005(self):
        """Направляет запрос на тестового человека, проверит что сервис ответил о неполучении, в запросе ФИО+ДР+ДУЛ"""
        # образец
        people = dict(lastName='Ежемесячные',
                    firstName='Денежные',
                    middleName='Выплаты',
                    birthday='1960-09-03',
                    documentType='',
                    series='6705',
                    number='517705',
                    exist='0',
                    paySource='',
                    dateEnd='',
                    cardExist='',
                    TransCardNum='',
                    test='1005_1')
        # очищаю данные по району
        delTI()
        # проверим, что очистилось нормально
        count = checkTI(people)
        self.assertEqual(count, 0, 'Ожидали, что для %s %s %s будут удалены данные 1005 сервиса, но остально %s строк' %
                         (people['lastName'], people['firstName'], people['middleName'], count))
        # отправит запрос на 1005 сервис
        with open('Шаблоны/Request_1005.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        req = smev.change(shablon, people)
        req = smev.change(req, TI)
        print("Отрабатываем пример", people['test'])
        res = test_1005.service_1005(req, TI, people['test'])
        resDict = test_1005.print_1005(res)
        err = test_1005.equal_1005(people, resDict)
        # проверит, что ответ совпадает с образцом
        if err:
            self.fail('Ответ сервиса отличается от образца!\n %s' % err)


    #@unittest.skip('Временно пропущен')
    def test_3_load_2014(self):
        """ Выгружает ПКУ для 1005 сервиса"""
        self.base_url = addr
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.driver.get(self.base_url + 'Login.aspx')
        self.verificationErrors = []
        self.accept_next_alert = True
        self.goMainASP()
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
        driver.find_element_by_id('ctl00_cph_CB_s1005').click()
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
            self.fail("Не дождался окончания выгрузки ПКУ для 1005")
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
        arh_name = 'fig/9/test_9.png'
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        # проверяю на ТИ, что загрузилась одна строка
        # проверим, что очистилось нормально
        people = dict(lastName='Ежемесячные',
                      firstName='Денежные',
                      middleName='Выплаты'
                      )
        count = checkTI(people)
        self.assertEqual(count, 1, 'Ожидали, что для %s %s %s будет загружена одна запись, но оказалось %s' %
                         (people['lastName'], people['firstName'], people['middleName'], count))


    #@unittest.skip('Временно пропущен')
    def test_4_ask1005(self):
        """Направляет запрос на тестового человека, проверит, что ответил транспортной картой, в запросе ФИО+ДР+ДУЛ"""
        # образец
        people = dict(lastName='Ежемесячные',
                    firstName='Денежные',
                    middleName='Выплаты',
                    birthday='1960-09-03',
                    documentType='',
                    series='6705',
                    number='517705',
                    exist='1',
                    paySource='Средства регионального бюджета',
                    dateEnd='2020-02-29',
                    cardExist='1',
                    TransCardNum='1234567890',
                    test='1005_4')
        # отправит запрос на 1005 сервис
        with open('Шаблоны/Request_1005.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        req = smev.change(shablon, people)
        req = smev.change(req, TI)
        print("Отрабатываем пример", people['test'])
        res = test_1005.service_1005(req, TI, people['test'])
        resDict = test_1005.print_1005(res)
        err = test_1005.equal_1005(people, resDict)
        # проверит, что ответ совпадает с образцом
        if err:
            self.fail('Ответ сервиса отличается от образца!\n %s' % err)

    #@unittest.skip('Временно пропущен')
    def test_5_ask1005(self):
        """Направляет запрос на тестового человека, проверит, что ответил транспортной картой, в запросе ФИО+ДР"""
        # образец
        people = dict(lastName='Ежемесячные',
                      firstName='Денежные',
                      middleName='Выплаты',
                      birthday='1960-09-03',
                      documentType='',
                      series='',
                      number='',
                      exist='1',
                      paySource='Тестовый скрипт',
                      dateEnd='2022-11-10',
                      cardExist='1',
                      TransCardNum='1234560',
                      test='1005_5')
        DB = TI
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
        try:
            conTI = pypyodbc.connect(conS)
        except:
            print("Возникла ошибка при соединении с БД АСП")
            exit(1)
        cur = conTI.cursor()
        try:
            cur.execute("""insert into SMEV_SERVICE_TRANSPORT
            (FAMIL, IMJA, OTCH, DROG, Exist, DateEnd, TransCardNum, PaySource, eservice_users_id, TransCard)
            values(?, ?, ?, '1960-09-03', 1, '2022-11-10', '1234560', ?, 159, 1)""",
                        (people['lastName'], people['firstName'], people['middleName'],'Тестовый скрипт'))

            conTI.commit()
        except:
            print('При создании тестового человека возникли ошибки')
        cur.execute("select count(id) from SMEV_SERVICE_TRANSPORT where famil=? and imja=? and OTCH=?",
                        (people['lastName'], people['firstName'], people['middleName']))
        count = cur.fetchone()[0]
        self.assertEqual(count, 2, 'Должно быть в БД 2 человека, получилось %s' % count)

        # отправит запрос на 1005 сервис
        with open('Шаблоны/Request_1005.xml', mode='r', encoding='utf-8') as f:
            shablon = f.read()
        req = smev.change(shablon, people)
        req = smev.change(req, TI)
        print("Отрабатываем пример", people['test'])
        res = test_1005.service_1005(req, TI, people['test'])
        resDict = test_1005.print_1005(res)
        err = test_1005.equal_1005(people, resDict)
        # проверит, что ответ совпадает с образцом
        if err:
            self.fail('Ответ сервиса отличается от образца!\n %s' % err)


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
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
