# -*- coding: utf-8 -*-
__author__ = 'alexey'
import time
from selenium.webdriver.support.ui import Select
import platform
import pypyodbc


def checkControl(driver, pre):
    """ Проверяет наличие в контроле Госуслуги обязательных элементов:
    1) кнопки новый ответ - ctl00_cph_guResp1_lbtnNewResponse
    2) выпадающего списка статус ctl00_cph_guResp1_ddlStatus
    3) поля для ввода комментария ctl00_cph_guResp1_tbGosUsl_Coment
    4) места прикрепления файла ctl00_cph_guResp1_InpScDoc_lbtnAddScanDoc
    :param driver: веб-драйвер
    :param pre: префикс для контрола
    :return: значение None или сообщение об ошибке
    """
    msg = ""

    # Проверю наличие кнопки новый ответ заявителю
    id = pre + '_lbtnNewResponse'
    if findElementById(driver, id):
        msg += 'В контроле не нашел кнопки новый ответ.\n'
    else:
        # Активна или нет?
        newResponse = driver.find_element_by_id(id).get_attribute('disabled')

    # Проверю наличие  выпадающего списка со статусом
    id = pre + '_ddlStatus'
    if findElementById(driver, id):
        msg += 'В контроле не нашел выпадающего списка с решением.\n'
    else:
        # Активна или нет?
        status = driver.find_element_by_id(id).get_attribute('disabled')

    # Проверю наличие  поля для комментария
    id = pre + '_tbGosUsl_Coment'
    if findElementById(driver, id):
        msg += 'В контроле не нашел поля для комментария.\n'
    else:
        # Активна или нет?
        comment = driver.find_element_by_id(id).get_attribute('disabled')

    # Проверю наличие  кнопки для прикрепления файла
    id = pre + '_InpScDoc_lbtnAddScanDoc'
    if findElementById(driver, id):
        msg += 'В контроле не нашел кнопки для файла.\n'
    else:
        # Активна или нет?
        file = driver.find_element_by_id(id).get_attribute('disabled')

    # Если до этого все поля найдены, провожу их проверку на активность
    if msg:
        msg += 'При поиске обязательных элементов контрола вознили ошибки, проверка на активность выполнена не будет!\n'
    else:
        if newResponse:
            # Кнопка новый ответ не активна, значит это не выгруженный ответ и в нем можно все редактировать
            if status:
                msg += 'В не выгруженном ответа нельзя редактировать статус.\n'
            if comment:
                msg += 'В не выгруженном ответа нельзя редактировать комментарий.\n'
            if file:
                msg += 'В не выгруженном ответа нельзя добавить файл.\n'
                title = driver.find_element_by_id(id).get_attribute('title')
                if title != 'Для добавления документа сначала создайте новый ответ.':
                    msg += "В title кнопки прикладывания ответа написано %s, должно быть выполнено задания №51302\n" % title
        else:
            # Кнопка новый ответ активна
            if not status:
                msg += 'Новый ответ еще не создан, а редактировать статус можно.\n'
            if not comment:
                msg += 'Новый ответ еще не создан, а редактировать комментарий можно.\n'
            if not file:
                msg += 'Новый ответ еще не создан, а приложить файл можно.\n'
    return msg


def writeNewResponse(driver, pre, data=None):
    """ Пытается ввести новоый ответ.
    1) кнопки новый ответ - _lbtnNewResponse
    2) выпадающего списка статус _guResp1_ddlStatus
    3) поля для ввода комментария _tbGosUsl_Coment
    4) места прикрепления файла _lbtnAddScanDoc
    :param driver: веб-драйвер
    :param pre: префикс для контрола
    :param data: словарь с данными для ответа, если пустой то только контрол проверяет
    :return: значение None или сообщение об ошибке
    """
    msg = ''
    # проверить, что заявление готово к вводу нового ответа
    # Проверю наличие кнопки новый ответ заявителю
    id = pre + '_lbtnNewResponse'
    if findElementById(driver, id):
        msg += 'В контроле не нашел кнопки новый ответ.\n'
    else:
        # Активна или нет?
        if driver.find_element_by_id(id).get_attribute('disabled'):
            msg += 'Кнопка новый ответ не активна.\n'

    # если не было ошибок, то продолжим. Проверим активность нужнух полей.
    if not msg:
        # нажать новый ответ
        driver.find_element_by_id(id).click()
        # после этого поле ввода текста должно стать активно
        id = pre + '_tbGosUsl_Coment'
        if findElementById(driver, id):
            msg += 'В контроле поле ввода нового ответа исчезло после нажатия на ввести новый ответ.\n'
        else:
            # Активна или нет?
            if driver.find_element_by_id(id).get_attribute('disabled'):
                msg += 'В контроле поле ввода нового ответа осталось не активной после нажатия на ввести новый ответ.\n'
    # если не было ошибок, пробую ввести новый ответ
    if not msg and data is not None:
        # ввести комментарий
        id = pre + '_tbGosUsl_Coment'
        driver.find_element_by_id(id).click()
        driver.find_element_by_id(id).clear()
        driver.find_element_by_id(id).send_keys(data['comment'])

        # выбрать статус из выпадающего списка
        id = pre + '_ddlStatus'
        if data['status'] == 'Исполнено':
            Select(driver.find_element_by_id(id)).select_by_visible_text("Исполнено")
            #driver.find_element_by_css_selector("option[value=\"3\"]").click()
        elif data['status'] == 'Отказ':
            Select(driver.find_element_by_id(id)).select_by_visible_text("Отказ")
            #driver.find_element_by_css_selector("option[value=\"4\"]").click()
        else:
            msg += 'Не корректные входные данный для заполнения ответа. Надо указать Исполнено или Отказ.\n'

        # приложить файл
        # нажать добавить новый документ
        driver.find_element_by_xpath(u"//a[@title='Добавить новый сканированный документ']/img").click()
        # очистить название и ввести новое
        f = driver.find_element_by_xpath("//div[2]/div/input")
        f.clear()
        f.send_keys(data['file'])
        # нажать загрузить
        driver.find_element_by_xpath(u"//a[@title='Загрузить файл']/b/b/img[@src='../Images/ok_small2.png']").click()
        # жду загрузки файла и выхожу
        for i in range(30):
            try:
                driver.find_element_by_id("ctl00_lb1")
                break
            except:
                pass
            time.sleep(1)
        else:
            msg += "Не удалось дождаться загрузки файла.\n"
    return msg


def findElementById(driver, id):
    """
    Ищет элемент по ID
    :param driver: веб-драйвер
    :param id: идентификатор
    :return: 1 - не нашел, 0 - нашел
    """
    result = 0
    try:
        driver.find_element_by_id(id)
    except:
        result = 1
    return result


def getDisabled(driver, id):
    """
    Получает значение атрибута disabled, если его не находит, то = enabled. Поэтому перед эти надо проверить наличие
    элемента
    :param driver: драйвер
    :param id: ИД
    :return: 1 если disabled, 0 - если enabled
    """
    atr = driver.find_element_by_id(id).get_attribute('disabled')
    return atr


def getResponseDB(zaiv, cur):
    """
    :param zaiv:  список номеров заявлений
    :param cur:  курсор к БД
    :return: словарь с ответами по заявлению
    """
    zaivBad = dict()
    for key in zaiv:
        # это список словарей для решения из БД
        badList = list()
        # Получаю список статусов и комментариев
        cur.execute("""select id, state, info from EService_Response where eService_Request_id in
                (select id from EService_Request where requestId=?) order by id""", (key,))
        s = cur.fetchall()
        for resp in s:
            bad = dict()
            bad['status'] = resp[1]
            bad['comment'] = resp[2]
            # Получаю список приложенных файлов
            cur.execute("""select filename, id from eservice_scandoc where eService_Request_id in
                    (select id from EService_Request where requestId=?)
                    and isResponse = 1 and EService_Response_id = ? order by id ASC""", (key, resp[0]))
            bad['files'] = list()
            for res in cur.fetchall():
                bad['files'].append(res[0])
            badList.append(bad)
        zaivBad[key] = badList
    return zaivBad


def checkResponse(goodDict, badDict):
    """ Сравнивает информацию по 2-м заявлениям: статус, комментарий, приложенные файлы. Структкра входных данных:
    словарь, с ключем по номеру заявления; значение - список решений. Каждое решение должно содержать информацию
    по статусу, комментарию, приложенным файлам. Порядок решений важен.
    :param goodDict: словарь с образцами
    :param badDict: словарь с для сравнения
    :return: сообщение об ошибке
    """
    msg = ''
    for key in goodDict.keys():
        if key in badDict:
            goodList = goodDict[key]
            badList = badDict[key]
            if len(goodList) != len(badList):
                msg += 'Длина списка для ответов для образца и результата из БД не совпадает. Образец = %s, из БД = %s\n' % (goodList, badList)
                continue
            for i in range(0, len(goodList)):
                good = goodList[i]
                bad = badList[i]
                # такое заявлени существует, пробуем сравнить статусы
                id = 'status'
                if (id in good) and (id in bad):
                    if good[id] != bad[id]:
                        msg += 'Статусы образца и заявления из БД не совпадают. Образец = %s, из БД = %s\n' % (good[id], bad[id])
                else:
                    msg += 'В образце или заявлении из БД отсутствует инф. о статусе. Образец = %s, из БД = %s\n' % (good, bad)

                # Пробуем сравнить комментарииъ
                id = 'comment'
                if (id in good) and (id in bad):
                    if good[id] != bad[id]:
                        msg += 'Комментарии образца и заявления из БД не совпадают. Образец = %s, из БД = %s\n' \
                               % (good[id], bad[id])
                else:
                    msg += 'В образце или заявлении из БД отсутствует инф. о комментарии. Образец = %s, из БД = %s\n' % (good, bad)

                # Пробуем сравнить спискеи приложенных файлов
                id = 'files'
                if (id in good) and (id in bad):
                    if good[id] != bad[id]:
                        msg += 'Приложенные файлы образца и заявления из БД не совпадают. Образец = %s, из БД = %s\n' \
                               % (good[id], bad[id])
                else:
                    msg += 'В образце или заявлении из БД отсутствует инф. о приложенных файлах. Образец = %s, из БД = %s\n' % (good, bad)
        else:
            msg += 'Нет информации по заявлению %s\n' % key
    return msg


def getResponseGUI(driver, status, comment, file):
    """Получает ответ на заявление ПГУ считывая из графического интерфейса. Возвращает словарь с:
    статусом, комментарием, приложенным файлом.
    :param status: ID для проверки статуса
    :param comment: ID для проверки комментария
    :param file: xpath для проверки файла
    :return: словарь ответом
    """
    resList = list()
    res = dict()
    # проверить статус
    res['status'] = Select(driver.find_element_by_id(status)).first_selected_option.text
    # получить комментаний
    res['comment'] = driver.find_element_by_id(comment).text
    # проверить файл
    res['files'] = [driver.find_element_by_xpath(file).text]
    resList.append(res)
    return resList


def getConnection (DB):
    """ Соединяется с БД, возвращает коннектион. Если не получается, то завершает работу.
    :param DB: словарь с параметрами для соединения
    :return: коннект
    """
    # определяет, на какой ОС запущен
    os = platform.system()
    if os == 'Linux':
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['DB_address'], DB['DB_port'], DB['DB_name'], DB['DB_password'])
    elif os == 'Windows':
        # на windows 2003 тут нужно указать другую версию клиента
        conS = 'DRIVER={SQL Server Native Client 11.0}; SERVER=%s; DATABASE=%s; UID=sa; PWD=%s' \
               % (DB['DB_address'], DB['DB_name'], DB['DB_password'])
    else:
        print('Запущен на не известной ОС. Работает только с Linux и Windows.')
        exit(1)
    try:
        # пробую соединится
        con = pypyodbc.connect(conS)
    except:
        print("Возникла ошибка при соединении с БД ТИ, строка соединения %s" % conS)
        exit(1)
    return con




