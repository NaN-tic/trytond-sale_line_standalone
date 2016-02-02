# This file is part of the sale_line_standalone module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite
import unittest


class SaleLineStandaloneTestCase(ModuleTestCase):
    'Test Sale Line Standalone module'
    module = 'sale_line_standalone'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            SaleLineStandaloneTestCase))
    return suite
