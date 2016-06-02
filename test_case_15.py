# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, datetime
import os, sys
import config
import forSeleniumTests
from pymongo import MongoClient



TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])
fio = ('Предоставление', 'Cоциальных', 'Услуг')
# соединение с БД для записи протокола
BD = {'adr': 'localhost', 'BD': 'testResult', 'collection': 'firstTest'}


class case15(unittest.TestCase):
    """Проверяет выгрузку из АСП на ТИ. Пока проверяет только выгрузку статусов"""

    @classmethod
    def setUpClass(cls):
        # очистить папки
        dirList = ('fig/15/',)
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)
        # создать вебдрайвер
        cls.base_url = addr
        cls.driver = webdriver.Firefox()
        cls.driver.implicitly_wait(30)
        # зайти в АСП
        cls.verificationErrors = []
        cls.accept_next_alert = True


    def setUp(self):
        self.timeStart = datetime.datetime.now()
        self.timeBegin = time.time()
        self.testDict = {'name': self.id().split('.')[-2:], 'start': datetime.datetime.now()}
        print('%s Выполняю тест: %s' % (self.testDict['start'], self.testDict['name']))
        # соединяюсь с ТИ
        self.conTI = forSeleniumTests.getConnection(TI)
        self.curTI = self.conTI.cursor()
        # соединяюсь с АСП
        self.conASP = forSeleniumTests.getConnection(ASP)
        self.curASP = self.conASP.cursor()
        self.goMainASP()


    def goMainASP(self):
        """ Входит в главное меню АСП"""
        driver = self.driver
        self.driver.get(self.base_url + 'Login.aspx')
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


    def test_1(self):
        """Пытается выгрузить статусы заявлений ПГУ через файл"""
        # Заходит в госуслуги
        driver = self.driver
        driver.get(self.base_url + "Reports/SocPortal.aspx?Action=Export")
        # Перейти на вкладку выгрузки через файл
        driver.find_element_by_id('ctl00_cph_UltraWebTab1td0').click()
        # Сбросить галочки для всех пунктов выгрузки: ЛК, статусы, СМЭВ запросы, ПКУ для СМЭВ
        self.clearCheck(driver, ('ctl00_cph_CB_PKU', 'ctl00_cph_CB_State',
                                 'ctl00_cph_CB_SMEV', 'ctl00_cph_CB_PKU_SMEV'))
        # Установить для выгрузки статусов ПГУ
        driver.find_element_by_id('ctl00_cph_CB_State').click()
        # Проверить сколько там статусов (ожидаем 4-ре)
        s = driver.find_element_by_id('ctl00_cph_lbl_State_cnt').text
        self.assertEqual('4', s, 'Ожидали 4 решения, нашлось %s' % s)
        # Нажать на кнопку получить файл
        driver.find_element_by_id('ctl00_cph_UltraWebTab1__ctl0_lbExport').click()
        # Подождать прогресс бар
        for i in range(10):
            try:
                driver.find_element_by_css_selector("b > b").click()
                break
            except:
                pass
            time.sleep(1)
        # Ищу кнопку загрузить файл
        s = driver.find_element_by_id('ctl00_cph_AJTran1_PopupDiv_PrintLink').text
        self.assertEqual('Открыть файл!', s, 'Ожидали кнопку открыть файл, получили %s' % s)
        # Нажимаю отмена, т.к. файл не нужен
        driver.find_element_by_id('ctl00_cph_AJTran1_PopupDiv_CloseButton').click()
        # Вернулись назад, проверим что есть кнопка получить файл
        self.assertTrue(self.is_element_present('By.Id', 'ctl00_cph_UltraWebTab1__ctl0_lbExport'),
                        'Ожидали появление кнопки Получить файл')



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
        arh_name = 'fig/15/%s.png' % '.'.join(self.testDict['name'])
        self.driver.save_screenshot(arh_name)
        #self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        self.testDict['time'] = int(time.time() - self.timeBegin)
        print(self.testDict)
        print('Выполнил тест: %s за %s секунд.' % (self.testDict['name'], self.testDict['time']))
        '''
        # запись результат в БД
        try:
            client = MongoClient(BD['adr'])
            db = client[BD['BD']]
            collection = db[BD['collection']]
        except:
            print("Ошибка при соединении с БД. Программа остановлена")
            Type, Value, Trace = sys.exc_info()
            print("""Тип ошибки: %s Текст: %s""" % (Type, Value))
            exit(2)
        else:
            r = collection.insert_one(self.testDict)
            print('Результат записан в БД:', r)
            client.close()
        '''
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)
