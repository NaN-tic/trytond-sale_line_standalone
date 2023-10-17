# This file is part of the sale_line_standalone module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, If, Not
from trytond.transaction import Transaction


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        add_remove = [
            ('currency', '=', Eval('currency')),
            ('company', '=', Eval('company')),
            ('sale', '=', None),
            ('party', '=', Eval('party', -1)),
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


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'
    party = fields.Many2One('party.party', 'Party',
        domain=['OR',
            ('id', If(Bool(Eval('_parent_sale', {}).get('party', 0)),
                '=', '!='), Eval('_parent_sale', {}).get('party', -1)),
            ('id', If(Bool(Eval('_parent_sale', {}).get('shipment_party', 0)),
                '=', '!='), Eval('_parent_sale', {}).get('shipment_party', -1)),
            ],
        states={
            'required': Not(Bool(Eval('sale'))),
            },
        context={
            'company': Eval('company'),
            },
        depends=['sale', 'company'])

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        readonly_eval = If(Not(Eval('sale')), Not(Bool(Eval('party', 0))), False)
        cls.sale.required = False
        cls.product.states['readonly'] |= readonly_eval
        cls.quantity.states['readonly'] |= readonly_eval
        cls.unit.states['readonly'] |= readonly_eval
        if cls.amount.states.get('readonly'):
            cls.amount.states['readonly'] |= readonly_eval
        else:
            cls.amount.states['readonly'] = readonly_eval

        for field in ('product', 'quantity', 'unit', 'amount'):
            for depend in ('sale', 'party'):
                if depend not in getattr(cls, field).depends:
                    getattr(cls, field).depends.add(depend)

        for d in cls.taxes.domain:
            if 'company' in d:
                cls.taxes.domain[cls.taxes.domain.index(d)] = (
                        ('company', '=', Eval('company', -1))
                    )
                cls.taxes.depends.add('company')
                break

        # company and currency function field / set + searcher
        cls.company.setter = 'set_company'
        cls.company.searcher = 'searcher_company'
        # currency function field and m2o
        cls.currency.setter = 'set_currency'
        cls.currency.searcher = 'searcher_currency'

        # remove sale in __access__ / issue9903
        if 'sale' in cls.__access__:
            cls.__access__.remove('sale')

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        Sale = pool.get('sale.sale')
        sale_table = Sale.__table_handler__(module_name)
        table = cls.__table_handler__(module_name)
        super(SaleLine, cls).__register__(module_name)

        # Migration from 5.6: drop required on sale
        sale_table.not_null_action('sale', action='remove')

        if not table.column_exist('company'):
            table.add_column('company', 'INTEGER')
        if not table.column_exist('currency'):
            table.add_column('currency', 'INTEGER')

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_sale_state():
        return 'draft'

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id

    def get_rec_name(self, name):
        if self.product and not self.sale:
            return '%s' % (self.product.rec_name)
        elif not self.sale:
            return '(%s)' % (self.id)
        return super(SaleLine, self).get_rec_name(name)

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('party', None)
        return super(SaleLine, cls).copy(lines, default=default)

    @fields.depends('sale')
    def on_change_with_company(self, name=None):
        if self.sale:
            return super(SaleLine, self).on_change_with_company()
        table = self.__table__()
        cursor = Transaction().connection.cursor()
        sql_where = (table.id == self.id)
        cursor.execute(*table.select(table.company, where=sql_where, limit=1))
        company_id = cursor.fetchone()
        if company_id:
            return company_id[0]

    @classmethod
    def set_company(cls, lines, name, value):
        # set company from transaction
        company = Transaction().context.get('company')
        table = cls.__table__()
        cursor = Transaction().connection.cursor()
        sql_where = (table.id.in_([l.id for l in lines]))
        cursor.execute(*table.update(
            columns=[table.company],
            values=[company],
            where=sql_where))

    @classmethod
    def searcher_company(cls, name, clause):
        Operator = fields.SQL_OPERATORS[clause[1]]
        table = cls.__table__()
        query = table.select(table.id,
            where=Operator(table.company, clause[2]))
        return [('id', 'in', query)]

    @fields.depends('sale')
    def on_change_with_currency(self, name=None):
        if self.sale:
            return super(SaleLine, self).on_change_with_currency()
        table = self.__table__()
        cursor = Transaction().connection.cursor()
        sql_where = (table.id == self.id)
        cursor.execute(*table.select(table.currency, where=sql_where, limit=1))
        company_id = cursor.fetchone()
        if company_id:
            return company_id[0]

    @classmethod
    def set_currency(cls, lines, name, value):
        # set currency from company transaction
        Company = Pool().get('company.company')

        company = Transaction().context.get('company')
        if not company:
            return

        company = Company(company)
        table = cls.__table__()
        cursor = Transaction().connection.cursor()
        sql_where = (table.id.in_([l.id for l in lines]))
        cursor.execute(*table.update(
            columns=[table.currency],
            values=[company.currency.id],
            where=sql_where))

    @classmethod
    def searcher_currency(cls, name, clause):
        Operator = fields.SQL_OPERATORS[clause[1]]
        table = cls.__table__()
        query = table.select(table.id,
            where=Operator(table.currency, clause[2]))
        return [('id', 'in', query)]

    @fields.depends('sale', '_parent_sale.company', '_parent_sale.currency',
        '_parent_sale.party')
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
        pool = Pool()
        Date = pool.get('ir.date')
        Company = pool.get('company.company')

        context = Transaction().context
        customer = self.party.id if self.party else None
        price_list = None
        if self.party and hasattr(self.party, 'sale_price_list'):
            price_list = (self.party.sale_price_list.id
                            if self.party.sale_price_list else None)
        sale_date = context.get('sale_date', Date.today())

        with Transaction().set_context(customer=customer, price_list=price_list,
                sale_date=sale_date):
            super(SaleLine, self).on_change_product()

        if not self.currency:
            if self.sale:
                self.currency = self.sale.currency
            else:
                if Transaction().context.get('company'):
                    company = Company(Transaction().context['company'])
                    self.currency = company.currency

    @fields.depends('sale')
    def on_change_with_sale_state(self, name=None):
        if not self.sale:
            return 'draft'
        return super(SaleLine, self).on_change_with_sale_state(name)
