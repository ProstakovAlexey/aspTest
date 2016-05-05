#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest
import pypyodbc
import os
import test_373
import config
from xml.dom.minidom import *
import datetime, time


TI, ASP, LK, err = config.readConfig()
if err > 0:
    print('Ошибка при чтении конфигурационного файла')
    exit(1)
addr = 'http://%s:%s/%s/' % (ASP['adr'], ASP['port'], ASP['url'])

# контрольные люди и их дети
peopleList = list()
peopleList.append(dict(parentFamil='Сидит', parentName='Сребенком', parentOtch='Взрослая',
              parentDrog='1987-11-10', parentSnils='55555555501', parentDoc='70 01 456123',
              pay = [dict(childFamil='Сидит', childName='Ребенок', childOtch='Первый',
              childDrog='2016-01-03', childSnils='55555555500', childDocSeria='5645',
              childDocNomer='444444', startDate='2016-03-20', endDate='2017-07-03'),
                     ],
              control = dict(load1=1)))
peopleList.append(dict(parentFamil='Уход', parentName='Заребенком', parentOtch='Взрослая',
              parentDrog='1986-06-05', parentSnils='55555555502', parentDoc='70 01 789456',
              pay=[dict(childFamil='Уход', childName='Ребенокк', childOtch='Первый',
                        childDrog='2015-07-17', childDoc='5689 456123',
                        startDate='17.07.2015', endDate='17.01.2017'),
                   dict(childFamil='Уход', childName='Ребенок', childOtch='Первая',
                        childDrog='17.01.2016', childDoc='5645 444444',
                        startDate='17.07.2015', endDate='17.01.2017'
                        )],
              control=dict(load1=2)))


def delTI(peopleList):
        """Удаляет загруженные ранее записи для 373 сервиса по тестовым людям с Фамилия = Сидит"""
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
            for people in peopleList:
                print('Удаляю тестового человека для 373 сервиса с ТИ:', people['parentFamil'], people['parentName'], people['parentOtch'])
                cur.execute("""DELETE SMEV_SERVICE_ALLOWANCE_FOR_CHILD where F2_ID in
                (select id from F2 where FAMIL=? and IMJA=? and OTCH=?)""", (people['parentFamil'], people['parentName'], people['parentOtch']))
            conTI.commit()
        except:
            print('При очистке записей для скриптом возникли ошибки')
            conTI.close()
            exit(1)
        conTI.close()


def checkTI(people):
        """Возвращает сколько записей в таблице для 1009 найдено по человеку"""
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
            cur.execute("""select count(id) from SMEV_SERVICE_ALLOWANCE_FOR_CHILD where F2_id in
            (select id from F2 where FAMIL=? and IMJA=? and OTCH=?)""",
                        (people['parentFamil'], people['parentName'], people['parentOtch']))
            count = cur.fetchone()[0]
        except:
            print('При получении записей скриптом возникли ошибки')
            conTI.close()
            exit(1)
        conTI.close()
        return count


def getResponse(people, start, end, numer=0):
    """Направляет запрос на человека и его ребенка за указанный период. numer - номер ребенка в списке
    Получает ответ, анализирует его. Если не получал - выдает 0, иначе кол-во месяцев"""
    good_result = dict(codeKind="21", docDatKind="2000-01-01",
                       docDataCiv="1970-01-01", endDate="2010-01-01",
                       fNameCiv="Иван", fNameKind="Иван", iNameCiv="Иванов",
                       iNameKind="Иванов", mNameCiv="Иванович",
                       mNameKind="Иванович", monthsNumber="3",
                       nameOrganizationFrom="ФСС-1",
                       nameOrganizationTo="ФСС-2", nbDoc="00",
                       obtainingGrants2="true", regionFrom="01",
                       regionTo="02", sbDoc="00", seriesNumber="0000000000",
                       snils="000-000-000 00", startDate="2000-01-01")

    # это строка запроса, в которую будем делать подстановку
    requestString = '''codeKind="21" docDatKind="#docDatKind#" docDataCiv="#docDataCiv#" endDate="#endDate#"
    fNameCiv="#fNameCiv#" fNameKind="#fNameKind#" iNameCiv="#iNameCiv#" iNameKind="#iNameKind#"
    mNameCiv="#mNameCiv#" mNameKind="#mNameKind#" nameOrganizationFrom="ФСС-1" nameOrganizationTo="ФСС-2"
    nbDoc="#nbDoc#" regionFrom="01" regionTo="02" sbDoc="#sbDoc#" seriesNumber="#seriesNumber#"
    snils="#snils#" startDate="#startDate#"'''
    # подстановки родителя
    # фамилия родителя
    s = requestString.replace("#iNameCiv#", people['parentFamil'])
    # имя родителя
    s = s.replace("#fNameCiv#", people['parentName'])
    # отчество родителя
    s = s.replace("#mNameCiv#", people['parentOtch'])
    # дата рождения родителя
    s = s.replace("#docDataCiv#", people['parentDrog'])
    # серия и номер паспорта родителя
    s = s.replace("#seriesNumber#", people['parentDoc'])
    # СНИЛС родителя
    s = s.replace("#snils#", people['parentSnils'])

    # подстановака ребенка
    # фамилия ребенка
    s = s.replace("#iNameKind#", people['pay'][numer]['childFamil'])
    # имя ребенка
    s = s.replace("#fNameKind#", people['pay'][numer]['childName'])
    # отчество ребенка
    s = s.replace("#mNameKind#", people['pay'][numer]['childOtch'])
    # дата рождения ребенка
    s = s.replace("#docDatKind#", people['pay'][numer]['childDrog'])
    # номер свидетельства о рождении ребенка
    s = s.replace("#nbDoc#", people['pay'][numer]['childDocNomer'])
    # серия свидетельства о рождении
    s = s.replace("#sbDoc#", people['pay'][numer]['childDocSeria'])

    # дата начало периода запроса
    s = s.replace("#startDate#", start)
    # дата окончания периода запроса
    s = s.replace("#endDate#", end)

    with open('Шаблоны/373-Request.xml', mode='r', encoding="utf-8") as f:
        req = f.read()
    req = req.replace('#requestString#', s)
    fileName = "%s_%s_%s_%s" % (people['parentFamil'], people['parentName'], people['parentOtch'], numer)
    result = test_373.service_373(req, TI, fileName)
    count = 0
    if result:
        an = parseString(result).getElementsByTagName('ResponseDocument').item(0)
    else:
        an = None
    if an == None:
        # пришел пустой
        print("Тест RESULT. Пришел пустой ответ")
    else:
        pay = an.getAttribute('obtainingGrants2')
        if pay == 'true':
            # получал
            count = an.getAttribute('monthsNumber')
            count = int(count)
    return count


class case5(unittest.TestCase):
    """Проверяет сервис 373 - получение пособия. Перед выполнением удаляет тестового человека"""

    @staticmethod
    def setUpClass():
        # очистить папки
        dirList = ('fig/5/', 'Результаты/')
        for dir in dirList:
            for f in os.listdir(dir):
                os.remove(dir+f)
        # удалить тестового человеа
        delTI(peopleList)


    def setUp(self):
        """Выполнятся для каждого теста"""
        self.timeStart = datetime.datetime.now()
        self.timeBegin = time.time()
        print('%s Выполняю тест: %s' % (self.timeStart, self.id()))
        self.base_url = addr
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.driver.get(self.base_url + 'Login.aspx')
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

    #@unittest.skip('Временно отключен')
    def test_1_kp(self):
        """Направляет запрос на контрольные примеры из документации:
        ответ с данными, данные не найдены, ошибка в дате рождения, ошибка в GUID"""
        err = test_373.test_373(TI)
        self.assertEqual(err, 0, 'При выполнении контрольных примеров к 373 сервису возникли ошибки. %s' % TI['adr'])


    def test_2_load(self):
        """ Выгружает ПКУ для СМЭВ из АСП в ЛК за период с 01.03.2016 по 30.04.2016. В БД в справочнике уже
        должна быть выбрана заявка """
        # перед выгрузкой проверить, что информации по человеку нет
        for people in peopleList:
            count = checkTI(people)
            self.assertEqual(count, 0, 'У человека %s %s %s не удалилась информация по детским (SMEV_SERVICE_ALLOWANCE_FOR_CHILD)'
                             % (people['parentFamil'], people['parentName'], people['parentOtch']))
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
        # ставлю галочку на 373
        driver.find_element_by_id('ctl00_cph_CB_s373').click()
        # установливаю период с
        p = driver.find_element_by_id('igtxtctl00_cph_wdtS_s373')
        p.click()
        p.send_keys('01032016')
        # установливаю период по
        p = driver.find_element_by_id('igtxtctl00_cph_wdtPO_s373')
        p.click()
        p.send_keys('30042016')
        # проверить, что установлены путевки
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR,
                                                "option[value=\"Заявка на ежемес.пособие по уходу за реб.до 1,5лет\"]"),
                        'Не правильно установлен вид социальной поддержки для 373. Вручную поставьте только Заявка на ежемес.пособие по уходу за реб.до 1,5лет')
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
            self.fail("Не дождался окончания выгрузки ПКУ для 373")
        # проверяет, что прогрессбар успешно завершился
        s = driver.page_source
        if s.find('Операция завершена') == -1:
            self.fail('После загрузки ПКУ для 373 возникла ошибка на прогрессбаре')
        # нажать на ОК на прогрессбаре
        p.click()
        # проверяет, что выгрузка прошла успешно
        self.assertEqual("1. Соединение с ИТ. ОК\n2. Передача информации на ИТ СМЭВ+ПГУ. OK",
                         driver.find_element_by_id("ctl00_cph_L_Res").text,
                         'Передача ПКУ для СМЭВ прошла не успешно')
        # проверяю на ТИ, что загрузилась одна строка
        for people in peopleList:
            count = checkTI(people)
            control = people['control']['load1']
            self.assertEqual(count, control,
                'У человека %s %s %s добавилась информация по детским (SMEV_SERVICE_ALLOWANCE_FOR_CHILD)=%s'
                             % (people['parentFamil'], people['parentName'], people['parentOtch'], count))


    def test_3_request(self):
        """Проверить, что весь загруженный период отдается, если он попадает в период запроса"""
        #Направляет запрос на родителя: Сидит Сребенком Взрослая,
        #ребенок: Сидит Ребенок Первый, период 2016-03-20 по 2017-07-03,
        #До этого загружали с 01.03.2016 по 30.04.2016 (2 месяца)"""
        count = getResponse(peopleList[0], start='2016-03-20', end='2017-03-31', numer=0)
        self.assertEqual(count, 2, """Запрос на родителя: Сидит Сребенком Взрослая,
        ребенок: Сидит Ребенок Первый, период 2016-03-20 по 2017-07-03,т.к. загружали 01.03.2016 по 30.04.2016
        должен ответить, что за 2 месяца получал""")


    def test_4_request(self):
        """Проверить, что если в периоде запроса указать только часть загруженного периода, то отдает только
        часть"""
        #Направляет запрос на родителя: Сидит Сребенком Взрослая,
        #родителя: Сидит Ребенок Первый, период 2016-01-01 по 2017-03-31,
        #т.к. загружали 01.03.2016 по 01.04.2016 должен ответить, что за 1 месяц получал
        count = getResponse(peopleList[0], start='2016-01-01', end='2016-03-31', numer=0)
        self.assertEqual(count, 1, """Запроса на Сидит Сребенком Взрослая, ребенок Сидит Ребенок Первый,
        период 2016-01-01 по 2016-03-31. Ожидали, что кол-во месяцев придет 1""")

    @unittest.skip('Не работает, задание №51139')
    def test_5_request(self):
        """Проверяет, что данные извлекаются из нашей БД, а не из запроса. В запросе направляет не правильную
        ДР (1987-11-11), должен вернуть правильную (1987-11-10)"""
        people = dict(parentFamil='Сидит', parentName='Сребенком', parentOtch='Взрослая',
                      parentDrog='1987-11-11', parentSnils='55555555501', parentDoc='70 01 456123',
                      pay=[dict(childFamil='Сидит', childName='Ребенок', childOtch='Первый',
                                childDrog='2016-01-03', childSnils='55555555500', childDocSeria='5645',
                                childDocNomer='444444', startDate='2016-03-01', endDate='2017-07-03'),
                           ],
                      control=dict(load1=1))
        numer = 0
        start = '2016-01-01'
        end = '2016-03-31'

        # это строка запроса, в которую будем делать подстановку
        requestString = '''codeKind="21" docDatKind="#docDatKind#" docDataCiv="#docDataCiv#" endDate="#endDate#"
            fNameCiv="#fNameCiv#" fNameKind="#fNameKind#" iNameCiv="#iNameCiv#" iNameKind="#iNameKind#"
            mNameCiv="#mNameCiv#" mNameKind="#mNameKind#" nameOrganizationFrom="ФСС-1" nameOrganizationTo="ФСС-2"
            nbDoc="#nbDoc#" regionFrom="01" regionTo="02" sbDoc="#sbDoc#" seriesNumber="#seriesNumber#"
            snils="#snils#" startDate="#startDate#"'''
        # подстановки родителя
        # фамилия родителя
        s = requestString.replace("#iNameCiv#", people['parentFamil'])
        # имя родителя
        s = s.replace("#fNameCiv#", people['parentName'])
        # отчество родителя
        s = s.replace("#mNameCiv#", people['parentOtch'])
        # дата рождения родителя
        s = s.replace("#docDataCiv#", people['parentDrog'])
        # серия и номер паспорта родителя
        s = s.replace("#seriesNumber#", people['parentDoc'])
        # СНИЛС родителя
        s = s.replace("#snils#", people['parentSnils'])

        # подстановака ребенка
        # фамилия ребенка
        s = s.replace("#iNameKind#", people['pay'][numer]['childFamil'])
        # имя ребенка
        s = s.replace("#fNameKind#", people['pay'][numer]['childName'])
        # отчество ребенка
        s = s.replace("#mNameKind#", people['pay'][numer]['childOtch'])
        # дата рождения ребенка
        s = s.replace("#docDatKind#", people['pay'][numer]['childDrog'])
        # номер свидетельства о рождении ребенка
        s = s.replace("#nbDoc#", people['pay'][numer]['childDocNomer'])
        # серия свидетельства о рождении
        s = s.replace("#sbDoc#", people['pay'][numer]['childDocSeria'])

        # дата начало периода запроса
        s = s.replace("#startDate#", start)
        # дата окончания периода запроса
        s = s.replace("#endDate#", end)

        with open('Шаблоны/373-Request.xml', mode='r', encoding="utf-8") as f:
            req = f.read()
        req = req.replace('#requestString#', s)
        fileName = "%s_%s_%s_%s" % (people['parentFamil'], people['parentName'], people['parentOtch'], numer)
        result = test_373.service_373(req, TI, fileName)
        if result:
            an = parseString(result).getElementsByTagName('ResponseDocument').item(0)
        else:
            an = None
        if an == None:
            # пришел пустой
            print("Тест RESULT. Пришел пустой ответ")
            self.fail('Пришел пустой ответ')
        else:
            drog = an.getAttribute('docDataCiv')
            self.assertEqual(drog, '1987-11-10', "В запросе направляет не правильную ДР(1987 - 11 - 11), "
                                                 "должен вернуть правильную(1987 - 11 - 10)")


    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e:
            return False
        return True


    def is_alert_present(self):
        try:
            self.driver.switch_to_alert()
        except NoAlertPresentException as e:
            return False
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
        finally:
            self.accept_next_alert = True


    def tearDown(self):
        arh_name = 'fig/1/%s.png' % self.id()
        self.driver.save_screenshot(arh_name)
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        print('Выполнил тест: %s за %s секунд.' % (self.id(), int(time.time() - self.timeBegin)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

