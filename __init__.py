# This file is part of the sale_line_standalone module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import sale


def register():
    Pool.register(
        sale.Sale,
        sale.SaleLine,
        module='sale_line_standalone', type_='model')
