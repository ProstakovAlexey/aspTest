# -*- coding: utf-8 -*-
__author__ = 'alexey'
import time
import sys
import random
import urllib.request
from xml.dom.minidom import *
import osa
import hashlib


sig = '''<soap:Header>
    <wsse:Security soap:actor="http://smev.gosuslugi.ru/actors/smev">
      <ds:Signature><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" /><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411" /><ds:Reference URI="#body"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" /></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr3411" /><ds:DigestValue>2YU+Jw/J+z2d1oLSBJTeNO+XDQHtqfiKeMNVW/DNW38=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>IoOppmHislVSnMReTswNGvZqqDylHDGtGtqyCWMSK7NJVX5wmkTPwYdiFzN8CCTrQB6EI4JS64mVdKTgO6/yvA==</ds:SignatureValue><ds:KeyInfo><wsse:SecurityTokenReference><wsse:Reference URI="#SenderCertificate" /></wsse:SecurityTokenReference></ds:KeyInfo></ds:Signature>
      <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="SenderCertificate">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</wsse:BinarySecurityToken>
</wsse:Security>
</soap:Header>
  <soap:Body wsu:Id="body">
'''
sigEnv = '''<soapenv:Header>
    <wsse:Security soapenv:actor="http://smev.gosuslugi.ru/actors/smev">
      <ds:Signature><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" /><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411" /><ds:Reference URI="#body"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" /></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr3411" /><ds:DigestValue>2YU+Jw/J+z2d1oLSBJTeNO+XDQHtqfiKeMNVW/DNW38=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>IoOppmHislVSnMReTswNGvZqqDylHDGtGtqyCWMSK7NJVX5wmkTPwYdiFzN8CCTrQB6EI4JS64mVdKTgO6/yvA==</ds:SignatureValue><ds:KeyInfo><wsse:SecurityTokenReference><wsse:Reference URI="#SenderCertificate" /></wsse:SecurityTokenReference></ds:KeyInfo></ds:Signature>
      <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="SenderCertificate">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</wsse:BinarySecurityToken>
</wsse:Security>
</soapenv:Header>
  <soapenv:Body wsu:Id="body">
'''

def getVersion(IS):
    """
    Получает словарь со параметрами для подклчения к ИС, возвращает
    версию и сообщение об ошибки (если ошибок нет, то пустое)
    """
    err = None
    version = 0
    #addr = 'http://%s:%s%sexport.asmx?wsdl' % (IS['adr'], IS['port'], IS['url'])
    addr = 'http://%s:%s%sSMEV/webservice/DBAgent.asmx?wsdl' % (IS['adr'], IS['port'], IS['url'])
    try:
        cl = osa.Client(addr)
        version = cl.service.GetVersion()
    except:
        err = 'При определении версии ТИ возникли ошибки. Адрес: %s' % addr
    return version, err


def get_wsdl(IS, url, name='wsdl.wsdl'):
    '''Получает WSDL и пишет его в файл'''
    addr = 'http://%s:%s%s?wsdl' % (IS['adr'], IS['port'], url)
    err = 0
    file_name = 'Результаты/'+name
    try:
        response = urllib.request.urlopen(addr)
    except urllib.error.HTTPError:
        print ('При получении WSDL возникли ошибки! Не удалось обратится по адресу:', addr)
        err += 1
    else:
        print('WSDL успешно получена по адресу:', addr)
        wsdl = response.read().decode('utf-8')
        # убираем двойной перевод строки
        wsdl = wsdl.replace('\r\n', '\n')
        fp = open(file_name, mode="w", encoding="utf8")
        fp.write(wsdl)
        fp.close()
    return err


def snils(init=0):
    """ Функция генерирует СНИСЛ, начинающийся с 002 (чтобы легче было искать) остальные
    числа случайные, контрольное число вычисляется
    Страховой номер индивидуального лицевого счета страхового свидетельства обязательного пенсионного страхования(он же СНИЛС) проверяется на валидность контрольным числом. СНИЛС имеет вид: «XXX-XXX-XXX YY», где XXX-XXX-XXX — собственно номер, а YY — контрольное число. Алгоритм формирования контрольного числа СНИЛС таков:
    1) Проверка контрольного числа Страхового номера проводится только для номеров больше номера 001-001-998
    2) Контрольное число СНИЛС рассчитывается следующим образом:
    2.1) Каждая цифра СНИЛС умножается на номер своей позиции (позиции отсчитываются с конца)
    2.2) Полученные произведения суммируются
    2.3) Если сумма меньше 100, то контрольное число равно самой сумме
    2.4) Если сумма равна 100 или 101, то контрольное число равно 00
    2.5) Если сумма больше 101, то сумма делится по остатку на 101 и контрольное число определяется остатком от деления аналогично пунктам 2.3 и 2.4
    ПРИМЕР: Указан СНИЛС 112-233-445 95
    Проверяем правильность контрольного числа:
    цифры номера        1 1 2 2 3 3 4 4 5
    номер позиции       9 8 7 6 5 4 3 2 1
    Сумма = 1×9 + 1×8 + 2×7 + 2×6 + 3×5 + 3×4 + 4×3 + 4×2 + 5×1 = 95
    95 ÷ 101 = 0, остаток 95.
    Контрольное число 95 — указано верно """
    if init != 0:
        random.seed(init)
    # заполняем начальные числа СНИСЛ
    arr = [0, 0, 2]
    # res - переменная для результата
    res = ""
    contr = 0
    for i in range(3, 9):
        arr.append(random.randint(0, 9))
    for i in range(0, 9):
        contr += arr[i] * (9 - i)
        res += str(arr[i])
    if contr > 99:
        if contr == 100 or contr == 101:
            contr = 0
        else:
            contr %= 101
    if contr < 10:
        res += "0" + str(contr)
    else:
        res += str(contr)
    return res


def get_smev_date():
    """ Возвращает текущую дату, в формате СМЭВ """
    # возвращает текущее время в struct_time
    now = time.localtime()
    # форматирование к виду 2014-01-16T14:51:45.566+04:00
    return time.strftime("%Y-%m-%dT%H:%M:%S+04:00", now)


def case_num(n=6, init=0):
    '''Возвращает случайный номер состоящий из n цифр'''
    if init != 0:
        random.seed(init)
    result = ''
    for i in range(0, n):
        s = random.randint(0, 9)
        result += str(s)
    return result


def change(s, IS):
    """Проводит замены в строке, возвращает готовую
    s: входная строка
    IS: сведения об ИС Наименование, Мнемоника, ОКТМО (словарь)
    """
    s = s.replace('#VERSION#', 'rev120315')
    s = s.replace('#SERVICE_MNEMONIC#', 'TestMnemonic')
    s = s.replace('#SERVICE_VERSION#', '2.01')
    #print(s)
    for key in IS.keys():
        # все символы делает заглавными и решетки
        st = "#%s#" % key.upper()
        #print('st=', st)
        s = s.replace(st, IS[key])
    s = s.replace('#DATE#', get_smev_date())
    # добавить подпись
    if s.find(r':Header') == -1:
        s = s.replace(r'<soap:Body wsu:Id="body">', sig)
        s = s.replace(r'<soapenv:Body wsu:Id="body">', sigEnv)
    return s


def check(req, name, contr):
    """
    :param req: XML текст
    :param sum: контрольная сумма
    :return: 1 - ошибка, 0 - ок.
    """
    err = 1
    i = req.find('<smev:MessageData>')
    if i > 0:
        # блок с ответом найден
        summ = hashlib.md5(req[i:].encode())
        if contr == summ.hexdigest():
            err = 0
        else:
            print("Контрольная сумма для %s=%s" % (name, summ.hexdigest()))
    return err


def write_file(s, metod, code=None):
    """ Записывает файл. Вход - имя строка для записи в файл и префикс"""
    err = 0

    try:
        file_name = parseString(s).getElementsByTagName('smev:Status')[0]
        file_name = file_name.firstChild.nodeValue
    except:
        try:
            file_name = parseString(s).getElementsByTagName('rev:Status')[0]
            file_name = file_name.firstChild.nodeValue
        except:
            Type, Value, Trace = sys.exc_info()
            file_name = "FAULT"
            print("Не удалось распарсить файл. Вероятно xml структура повреждена. Файл будет сохранен как %s, выполнение продолжено" % (file_name))
            print("Ошибка Тип:", Type, "Значение:", Value)
            err += 1
    if code:
        file_name = 'Результаты/%s(%s)_%s.xml' % (metod, code, file_name)
    else:
        file_name = 'Результаты/'+metod+'_'+file_name+'.xml'
    # добавляем строку с кодировкой если ее нет
    if s.startswith('<?xml version="1.0" encoding="utf-8"?>') == False:
        s = '<?xml version="1.0" encoding="utf-8"?>\n'+s
    fp = open(file_name, mode="w", encoding="utf-8")
    fp.write(s)
    fp.close()
    return err
