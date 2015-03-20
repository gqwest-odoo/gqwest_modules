# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
'name': 'GQWEST Odoo Modules',
'version': '1.0',
'category': 'Custom Modules',
'sequence':'',
'summary': 'Site Inspection, Servicing, Machine Upgrades, Advance Payments (PDCs)',
'description': """

""",
'author': 'Roxly Rivero',
'website': '',
'images': [],
'depends': ['sale','account','stock'],
'data': ['servicing_view.xml','store_inspection_view.xml','prpayments_view.xml',
         'sale_order_view.xml',
         'payment_sequence.xml','payment_view.xml','payment_view_items.xml','irr_view.xml','inherits_view.xml', 'wizard/wizards_view.xml'],
'demo': [],
'test': [],
'installable': True,
'auto_install': False,
'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
