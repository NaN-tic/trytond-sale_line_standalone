# This file is part of the sale_line_standalone module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond import backend
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, If, Not
from trytond.transaction import Transaction

__all__ = ['Sale', 'SaleLine']


class Sale:
    __metaclass__ = PoolMeta
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        add_remove = [
            ('party', '=', Eval('party')),
            ('currency', '=', Eval('currency')),
            ('company', '=', Eval('company')),
            ('sale', '=', None),
            ]
        add_remove_depends = set(['party', 'currency', 'company'])

        if not cls.lines.add_remove:
            cls.lines.add_remove = add_remove
        else:
            cls.lines.add_remove = [
                add_remove,
                cls.lines.add_remove,
                ]
        cls.lines.depends = list(set(cls.lines.depends) | add_remove_depends)


class SaleLine:
    __metaclass__ = PoolMeta
    __name__ = 'sale.line'
    party = fields.Many2One('party.party', 'Party', select=True,
        domain=[
            ('id',
                If(Bool(Eval('_parent_sale', {}).get('party', 0)),
                    '=', '!='),
                Eval('_parent_sale', {}).get('party', -1)),
            ],
        states={
            'required': Not(Bool(Eval('sale'))),
            },
        depends=['sale'])
    currency = fields.Many2One('currency.currency', 'Currency',
        domain=[
            ('id',
                If(Bool(Eval('_parent_sale', {}).get('currency', 0)),
                    '=', '!='),
                Eval('_parent_sale', {}).get('currency', -1)),
            ],
        states={
            'required': Not(Bool(Eval('sale'))),
            },
        depends=['sale'])
    company = fields.Many2One('company.company', 'Company',
        domain=[
            ('id',
                If(Bool(Eval('_parent_sale', {}).get('company', 0)),
                    '=', '!='),
                Eval('_parent_sale', {}).get('company', -1)),
            ], depends=['sale'], select=True)

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        cls.product.states['readonly'] &= Not(Bool(Eval('party', 0)))
        cls.quantity.states['readonly'] &= Not(Bool(Eval('party', 0)))
        cls.unit.states['readonly'] &= Not(Bool(Eval('party', 0)))
        cls.amount.states['readonly'] &= Not(Bool(Eval('party', 0)))
        for d in cls.taxes.domain:
            if 'company' in d:
                cls.taxes.domain[cls.taxes.domain.index(d)] = (
                        ('company', '=', Eval('company', -1))
                    )
                cls.taxes.depends.append('company')
                break

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        cursor = Transaction().connection.cursor()
        table = TableHandler(cls, module_name)
        sql_table = cls.__table__()
        Sale = Pool().get('sale.sale')
        line = cls.__table__()
        sale = Sale.__table__()

        created_company = not table.column_exist('company')

        super(SaleLine, cls).__register__(module_name)

        if created_company:
            # Fill company field of sale lines if the installation of this
            # module takes place when there are already sales in the database
            # and set it to be required.
            values = (line
                .join(sale, 'LEFT', condition=(line.sale == sale.id))
                .select(
                    sale.company,
                    where=(
                        (line.id == sql_table.id)
                        )
                    )
                )
            cursor.execute(*sql_table.update([sql_table.company], values))
            table = TableHandler(cls, module_name)
            table.not_null_action('company', action='add')

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('party', None)
        return super(SaleLine, cls).copy(lines, default=default)

    @fields.depends('sale')
    def on_change_sale(self):
        if self.sale:
            try:
                super(SaleLine, self).on_change_sale()
            except AttributeError:
                pass
            self.company = self.sale.company
            self.currency = self.sale.currency
            self.party = self.sale.party

    @fields.depends('party', 'currency')
    def on_change_product(self):
        Date = Pool().get('ir.date')

        context = {}
        context['customer'] = self.party.id if self.party else None
        if self.party and hasattr(self.party, 'sale_price_list'):
            context['price_list'] = self.party.sale_price_list.id \
                if self.party.sale_price_list else None
        context['sale_date'] = Date.today()
        with Transaction().set_context(context):
            super(SaleLine, self).on_change_product()

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id
