# -*- coding: utf-8 -*-
__author__ = 'alexey'
import time

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


def writeNewResponse(driver, pre):
    """ Пытается ввести новоый ответ.
    1) кнопки новый ответ - _lbtnNewResponse
    2) выпадающего списка статус _guResp1_ddlStatus
    3) поля для ввода комментария _tbGosUsl_Coment
    4) места прикрепления файла _lbtnAddScanDoc
    :param driver: веб-драйвер
    :param pre: префикс для контрола
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

    # если не было ошибок, то продолжим. Пробую дать новый ответ.
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


