=============================
Sale Line Standalone Scenario
=============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard, Report
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install sale_line_standalone::

    >>> config = activate_modules('sale_line_standalone')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()
    >>> customer2 = Party(name='Customer 2')
    >>> customer2.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create account categories::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

    >>> account_category_tax, = account_category.duplicate()
    >>> account_category_tax.customer_taxes.append(tax)
    >>> account_category_tax.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create sales::

    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale_line = SaleLine()
    >>> sale_line.party = customer
    >>> sale_line.product = product
    >>> sale_line.quantity = 1
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.lines.append(sale_line)
    >>> sale.save()
    >>> sale.state == 'draft'
    True
    >>> len(sale.lines) == 1
    True

    >>> sale_line = SaleLine()
    >>> sale_line.party = customer2
    >>> sale_line.product = product
    >>> sale_line.quantity = 1
    >>> sale2 = Sale()
    >>> sale2.party = customer2
    >>> sale2.payment_term = payment_term
    >>> sale2.lines.append(sale_line)
    >>> sale2.save()
    >>> sale2.state == 'draft'
    True
    >>> len(sale2.lines) == 1
    True

Create lines::

    >>> sale_line = SaleLine()
    >>> sale_line.party = customer
    >>> sale_line.product = product
    >>> sale_line.quantity = 2
    >>> sale_line.save()

    >>> sale_line2 = SaleLine()
    >>> sale_line2.party = customer2
    >>> sale_line2.product = product
    >>> sale_line2.quantity = 2
    >>> sale_line2.save()

    >>> lines = SaleLine.find([('sale', '=', None)])
    >>> len(lines) == 2
    True
    >>> set([l.company for l in lines]) == set([company])
    True

Add new lines in their respective sales::

    >>> sale.party == sale_line.party
    True
    >>> sale2.party == sale_line2.party
    True
    >>> sale.lines.append(sale_line)
    >>> sale.save()
    >>> len(sale.lines) == 2
    True
    >>> sale2.lines.append(sale_line2)
    >>> sale2.save()
    >>> len(sale2.lines) == 2
    True
