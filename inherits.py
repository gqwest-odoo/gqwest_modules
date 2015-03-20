from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp


class account_financial_report_categories(osv.osv):
	_name = 'account.financial.report.category'
	_description = "Financial Report Categories"
	_columns = {
		'name':fields.char('Category Name', size=64),
		'report_type':fields.selection([
								('balance_sheet','Balance Sheet'),
								('income_statement','Income Statement'),
								],'Accounting Report Type'),
		'sequence':fields.integer('Report Sequence'),
		'parent_id':fields.many2one('account.financial.report.category','Parent Category', ondelete='cascade'),
		}
	_order ='report_type asc, parent_id asc, sequence asc'
	_parent_order = "sequence asc"
account_financial_report_categories()


class account_account(osv.osv):
	_inherit = 'account.account'
	_columns = {
		'report_type':fields.selection([
								('balance_sheet','Balance Sheet'),
								('income_statement','Income Statement'),
								],'Accounting Report Type'),
		'report_categ1':fields.many2one('account.financial.report.category','Report Category 1'),
		'report_categ2':fields.many2one('account.financial.report.category','Report Category 2'),
		'report_categ3':fields.many2one('account.financial.report.category','Report Category 3'),
		'receivable_analytic_id':fields.many2one('account.analytic.account','Receivable Analytic Account'),
		}
account_account()

class analytic(osv.osv):
	_inherit = 'account.analytic.account'
	_columns = {
		'normal_account':fields.many2one('account.account','Normal Account'),
		'receivable_sales':fields.many2one('account.account','Sales Receivable Account'),
		}
analytic()

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
	def print_dr(self, cr, uid, ids, context=None):
		context= {'OID':active_id}
		assert len(ids) == 1
		return self.pool['report'].get_action(cr, uid, ids, 'sale_order_dr',context=context)
       
sale_order()