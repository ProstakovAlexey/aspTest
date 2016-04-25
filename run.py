# -*- coding: utf-8 -*-
import unittest
import test_case_1
import test_case_2
import test_case_3
import test_case_4
import test_case_5
import test_case_6
import test_case_7
import test_case_9

import HTMLTestRunner

loader = unittest.TestLoader()
suite1 = loader.loadTestsFromModule(test_case_1)
suite1.addTests(loader.loadTestsFromModule(test_case_2))
suite1.addTests(loader.loadTestsFromModule(test_case_3))
suite1.addTests(loader.loadTestsFromModule(test_case_4))
suite1.addTests(loader.loadTestsFromModule(test_case_5))
suite1.addTests(loader.loadTestsFromModule(test_case_6))
suite1.addTests(loader.loadTestsFromModule(test_case_7))
suite1.addTests(loader.loadTestsFromModule(test_case_9))
runner = unittest.TextTestRunner(verbosity=2)
outfile = open('/home/alexey/Программы/Тестирование/Анализ результатов/html/report.html', 'w')
runner = HTMLTestRunner.HTMLTestRunner(
    stream=outfile,
    title='Test Report',
    description='ASP'
)
runner.run(suite1)