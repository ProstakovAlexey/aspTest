# -*- coding: utf-8 -*-
__author__ = 'alexey'

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
        newResponse = getDisabled(driver, id)

    # Проверю наличие  выпадающего списка со статусом
    id = pre + '_ddlStatus'
    if findElementById(driver, id):
        msg += 'В контроле не нашел выпадающего списка с решением.\n'
    else:
        # Активна или нет?
        status = getDisabled(driver, id)

    # Проверю наличие  поля для комментария
    id = pre + '_tbGosUsl_Coment'
    if findElementById(driver, id):
        msg += 'В контроле не нашел поля для комментария.\n'
    else:
        # Активна или нет?
        comment = getDisabled(driver, id)

    # Проверю наличие  кнопки для прикрепления файла
    id = pre + '_InpScDoc_lbtnAddScanDoc'
    if findElementById(driver, id):
        msg += 'В контроле не нашел кнопки для файла.\n'
    else:
        # Активна или нет?
        file = getDisabled(driver, id)

    # Если до этого все поля найдены, провожу их проверку на активность
    if msg:
        msg += 'При поиске обязательных элементов контрола вознили ошибки, проверка на активность выполнена не будет!\n'
    else:
        if newResponse:
            # Кнопка новый ответ не активна, значит это не выгруженный ответ и в нем можно все редактировать
            if not status:
                msg += 'В не выгруженном ответа нельзя редактировать статус.\n'
            if not comment:
                msg += 'В не выгруженном ответа нельзя редактировать комментарий.\n'
            if not file:
                msg += 'В не выгруженном ответа нельзя добавить файл.\n'
                title = driver.find_element_by_id(id).get_attribute('title')
                if title != 'Для добавления документа сначала создайте новый ответ.':
                    msg += "В title кнопки прикладывания ответа написано %s, должно быть выполнено задания №51302\n" % title
        else:
            # Кнопка новый ответ активна
            if status:
                msg += 'Новый ответ еще не создан, а редактировать статус можно.\n'
            if comment:
                msg += 'Новый ответ еще не создан, а редактировать комментарий можно.\n'
            if file:
                msg += 'Новый ответ еще не создан, а приложить файл можно.\n'
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
    result = 0
    atr = driver.find_element_by_id(id).get_attribute('disabled')
    if atr == 'disabled':
        result = 1
    return result


