from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib2


class gq_old_so(osv.osv):
	_name = 'gq.old.so'
	_description = "OpenERP Sales Order"
	_columns = {
		'name':fields.char('Order Reference', size=64),
		'partner_name':fields.char('Partner Name', size=64),
		'partner_id':fields.many2one('res.partner', 'Customer'),
		'store_name':fields.char('Store Name', size=64),
		'order_date':fields.date('Order Date'),
		'profit_center':fields.char('Profit Center', size=64),
		'customer_reference':fields.char('Customer Reference', size=64),
		'salesman_name':fields.char('Salesman Name'),
		'user_id':fields.many2one('res.users','Salesman'),
		'notes':fields.text('Notes'),
		'state':fields.char('State', size=64),
		}
gq_old_so()

class so_items(osv.osv):
	_name = 'gq.old.so.item'
	_description="Order Items"
	_columns = {
		'name':fields.char('Description',size=64),
		'product_uom_qty':fields.float('Quantity'),
		'product_uom':fields.many2one('product.uom', 'Product UOM'),
		'product_id':fields.many2one('product.product','Product'),
		'price_unit':fields.float('Price Unit'),
		'discount':fields.float('Discount'),
		'so_id':fields.many2one('gq.old.so','Order ID', ondelete='cascade'),
		}
so_items()

class so(osv.osv):
	_inherit = 'gq.old.so'
	_columns = {
		'item_ids':fields.one2many('gq.old.so.item','so_id','Items'),
		}
so()