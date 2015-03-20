from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp

class gq_pr(osv.osv):
	       
	_name = "gq.pr"
	_description = "Provisionary Receipts"
	_columns = {
		'name':fields.char('PR Number', size=64),
		'partner_id':fields.many2one('res.partner','Client',required=True, domain=[('customer','=',True)]),
		'date':fields.date('Received Date', required=True),
		'state': fields.selection([
                                 ('draft','Draft'),
                                 ('confirmed','Confirmed'),
                                 ('posted','Posted'),
                                 ('partial','Partially Paid'),
                                 ('paid','Paid/Cleared')],'State'),
		'cash_amount':fields.float('Cash Payment'),
		'pr_amount':fields.float('Amount to be Paid'),
		'cc_approved_code':fields.char('Approved Code', size=64),
		'cc_amount':fields.float('Amount'),
		'enable_edit':fields.boolean('Edit'),
		'cc_bank_name':fields.char('Bank Name', size=64),
		'cctrans_date':fields.date('Transaction Date'),
		'bank_name':fields.char('Bank Name', size=64),
		'account_no':fields.char('Account No', size=64),
		'notes':fields.text('Notes'),
		'check_warehouse_account':fields.many2one('account.journal', 'Check Warehouse Account', domain=[('type','=','bank')]),
		'move_id':fields.many2one('account.move','Entry'),
		'cash_account_id':fields.many2one('account.journal','Cash Journal', domain=[('type','=','cash')]),
		'cc_account_id':fields.many2one('account.journal','Credit Card Journal', domain=[('type','=','cash')]),
		'cash_entry':fields.many2one('account.move','Cash Payment'),
		'cc_entry':fields.many2one('account.move','Credit Card Payment'),
		'journal_id':fields.many2one('account.journal', string='Journal',readonly=True, states={'draft': [('readonly', False),('required',True)]}, 
        domain=[('type','=','sale')]),
        'receivable_entry':fields.many2one('account.move.line','Receivable Entry'),
		}
	_defaults = {
		'state':'draft',
		'name':'New PR',
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		}
gq_pr()

class gq_checkpayment(osv.osv):
	_name = 'gq.checkpayment'
	_description = "Check Payments"
	_columns = {
		'name':fields.char('Check No.', size=64),
		'bank_name':fields.char('Bank Name', size=64),
		'deposit_account':fields.many2one('account.journal','Bank Account',domain=[('type','=','bank')]),
		'amount':fields.float('Amount'),
		'account_no':fields.char('Account No', size=64),
		'check_type':fields.selection([('local','Local'),('regional','Regional')],'Check Type'),
		'check_date':fields.date('Check Date'),
		'clearing_date':fields.date('Clearing Date'),
		'state': fields.selection([
                                 ('draft','Waiting for Clearing'),
                                 ('cleared','Cleared'),
                                 ('returned','Returned')],'State'),
		'return_reason': fields.selection([
                                 ('closed','Closed Account'),
                                 ('daif','DAIF'),
                                 ('dishonored','Dishonored'),
                                 ('pullout','Pulled Out'),
                                 ('replacement','Replacement')],'Reason for Check Return'),
		'pr_id':fields.many2one('gq.pr','PR Number', ondelete='cascade'),
		'service_id':fields.many2one('gq.servicing','Service Number'),
		
		}
	_defaults = {
		'state':'draft',
		}
gq_checkpayment()

class gq_servicing(osv.osv):
	_inherit = 'gq.servicing'
	_columns = {
		'check_ids':fields.one2many('gq.checkpayment', 'service_id','Checks'),
		}
gq_servicing()

class gq_pr_breakdown(osv.osv):
	_name = 'gq.pr.breakdown'
	_description="PR Income Breakdown"
	_columns = {
		'name':fields.char('Description',size=64),
		'account_id':fields.many2one('account.account','Account',domain=[('type','=','other')]),
		'analytic_id':fields.many2one('account.analytic.account','Class',domain=[('type','=','normal')]),
		'percentage':fields.float('Percentage'),
		'amount':fields.float('Amount'),
		'pr_id':fields.many2one('gq.pr','PR Number', ondelete='cascade'),
		'entry_id':fields.many2one('account.move.line','Entry ID'),
	}
gq_pr_breakdown()

class gq_pr_checks(osv.osv):
	_inherit = 'gq.pr'
	_columns = {
		'check_ids':fields.one2many('gq.checkpayment', 'pr_id','Checks'),
		'breakdown_ids':fields.one2many('gq.pr.breakdown', 'pr_id','PR Breakdown'),
		}
	def postpayments(self, cr, uid, ids, context=None):
		am = self.pool.get('account.move')
		aj = self.pool.get('account.journal')
		aml = self.pool.get('account.move.line')
		rec_list_ids = []
		cash_move = False
		cc_move = False
		for pr in self.read(cr, uid, ids, context=None):
			periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',pr['date']),('date_stop','>=',pr['date'])], limit=1)
			client_read = self.pool.get('res.partner').read(cr, uid, pr['partner_id'][0],context=None)
			if not client_read['property_account_receivable']:
				raise osv.except_osv(_('Undefined Account'), _("Kindly define a receivable account for %s!") % (client_read['name']))
			if pr['cash_amount']>0.00:
				cj = aj.read(cr, uid, pr['cash_account_id'][0], ['default_debit_account_id'])
				cash_vals = {
						'partner_id':pr['partner_id'][0],
						'date':pr['date'],
						'journal_id':pr['cash_account_id'][0],
						'period_id':periodCheck[0],
						'ref':pr['name'],
						}
				cash_move = am.create(cr, uid, cash_vals)
				name = 'Cash Payment for PR Number:' + pr['name'] 
				aml_vals = {
						'partner_id':pr['partner_id'][0],
						'date':pr['date'],
						'journal_id':pr['cash_account_id'][0],
						'period_id':periodCheck[0],
						'move_id':cash_move,
						'name':name,
						'ref':pr['name'],
						'account_id':cj['default_debit_account_id'][0],
						'debit':pr['cash_amount'],
						'credit':0.00,
						}
				aml.create(cr, uid, aml_vals)
				receivable_id = pr['receivable_entry'][0]
				for income in pr['breakdown_ids']:
					incomeRead = self.pool.get('gq.pr.breakdown').read(cr, uid, income, context=None)
					analyticRead = self.pool.get('account.analytic.account').read(cr, uid, incomeRead['analytic_id'][0], context=None)
					receivable_sales_account = analyticRead['receivable_sales'][0]
					normal_account = analyticRead['normal_account'][0]
					accountRead = self.pool.get('account.account').read(cr, uid, normal_account,['tax_ids'])
					tax = False
					income_entry = incomeRead['entry_id']
					if accountRead['tax_ids']:
						tax=accountRead['tax_ids'][0]
					amount = (incomeRead['amount']*incomeRead['percentage'])/100
					
					aml_vals = {
							'partner_id':pr['partner_id'][0],
							'date':pr['date'],
							'journal_id':pr['cash_account_id'][0],
							'period_id':periodCheck[0],
							'move_id':cash_move,
							'name':incomeRead['name'],
							'ref':pr['name'],
							}
					aml_vals.update({
							'account_id':client_read['property_account_receivable'][0],
							'credit':amount,
							'debit':0.00,
							})
					rentry= aml.create(cr, uid, aml_vals)
					rec_ids = [receivable_id,rentry]
					rec_list_ids.append(rec_ids)
					aml_vals.update({
							'account_id':receivable_sales_account,
							'debit':amount,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'credit':0.00,
							})
					rsa = aml.create(cr, uid, aml_vals)
					aml_vals.update({
							'account_id':normal_account,
							'account_tax_id':tax,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'credit':amount,
							'debit':0.00,
							})
					aml.create(cr, uid, aml_vals)
				am.post(cr, uid, cash_move)
			if pr['cc_amount']>0.00:
				cj = aj.read(cr, uid, pr['cc_account_id'][0], ['default_debit_account_id'])
				cash_vals = {
						'partner_id':pr['partner_id'][0],
						'date':pr['date'],
						'journal_id':pr['cc_account_id'][0],
						'period_id':periodCheck[0],
						'ref':pr['name'],
						}
				cc_move = am.create(cr, uid, cash_vals)
				name = 'Credit Card Payment for PR Number:' + pr['name'] 
				aml_vals = {
						'partner_id':pr['partner_id'][0],
						'date':pr['date'],
						'journal_id':pr['cc_account_id'][0],
						'period_id':periodCheck[0],
						'move_id':cc_move,
						'name':name,
						'ref':pr['name'],
						'account_id':cj['default_debit_account_id'][0],
						'debit':pr['cc_amount'],
						'credit':0.00,
						}
				aml.create(cr, uid, aml_vals)
				receivable_id = pr['receivable_entry'][0]
				for income in pr['breakdown_ids']:
					incomeRead = self.pool.get('gq.pr.breakdown').read(cr, uid, income, context=None)
					analyticRead = self.pool.get('account.analytic.account').read(cr, uid, incomeRead['analytic_id'][0], context=None)
					receivable_sales_account = analyticRead['receivable_sales'][0]
					normal_account = analyticRead['normal_account'][0]
					accountRead = self.pool.get('account.account').read(cr, uid, normal_account,['tax_ids'])
					tax = False
					income_entry = incomeRead['entry_id']
					if accountRead['tax_ids']:
						tax=accountRead['tax_ids'][0]
					amount = (incomeRead['amount']*incomeRead['percentage'])/100
					
					aml_vals = {
							'partner_id':pr['partner_id'][0],
							'date':pr['date'],
							'journal_id':pr['cc_account_id'][0],
							'period_id':periodCheck[0],
							'move_id':cc_move,
							'name':incomeRead['name'],
							'ref':pr['name'],
							}
					aml_vals.update({
							'account_id':client_read['property_account_receivable'][0],
							'credit':amount,
							'debit':0.00,
							})
					rentry= aml.create(cr, uid, aml_vals)
					rec_ids = [receivable_id,rentry]
					rec_list_ids.append(rec_ids)
					aml_vals.update({
							'account_id':receivable_sales_account,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'debit':amount,
							'credit':0.00,
							})
					rsa = aml.create(cr, uid, aml_vals)
					aml_vals.update({
							'account_id':normal_account,
							'account_tax_id':tax,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'credit':amount,
							'debit':0.00,
							})
					aml.create(cr, uid, aml_vals)
				am.post(cr, uid, cc_move)
			for rec_ids in rec_list_ids:
				if len(rec_ids)>=2:
					aml.reconcile_partial(cr, uid, rec_ids)
			state='paid'
			if pr['check_ids']:
				state='partial'
			self.write(cr, uid, pr['id'],{'state':state,'cash_entry':cash_move, 'cc_entry':cc_move})
		return True
		
	def postPR(self, cr, uid, ids, context=None):
		am = self.pool.get('account.move')
		aml = self.pool.get('account.move.line')
		rec_list_ids = []
		for pr in self.read(cr, uid, ids, context=None):
			periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',pr['date']),('date_stop','>=',pr['date'])], limit=1)
			am_vals = {
					'partner_id':pr['partner_id'][0],
					'date':pr['date'],
					'journal_id':pr['journal_id'][0],
					'period_id':periodCheck[0],
					'ref':pr['name'],
					}
			pr_move = am.create(cr, uid, am_vals)
			client_read = self.pool.get('res.partner').read(cr, uid, pr['partner_id'][0],context=None)
			if not client_read['property_account_receivable']:
				raise osv.except_osv(_('Undefined Account'), _("Kindly define a receivable account for %s!") % (client_read['name']))
			aml_vals = {
						'partner_id':pr['partner_id'][0],
						'date':pr['date'],
						'journal_id':pr['journal_id'][0],
						'period_id':periodCheck[0],
						'move_id':pr_move,
						}
			for income in pr['breakdown_ids']:
				incomeRead = self.pool.get('gq.pr.breakdown').read(cr, uid, income, context=None)
				analyticRead = self.pool.get('account.analytic.account').read(cr, uid, incomeRead['analytic_id'][0], context=None)
				receivable_sales_account = analyticRead['receivable_sales'][0]
				normal_account = analyticRead['normal_account'][0]
				aml_vals.update({
					'name':incomeRead['name'],
					'account_id':receivable_sales_account,
					'analytic_account_id':incomeRead['analytic_id'][0],
					'credit':incomeRead['amount'],
					'debit':0.00,
					})
				income_entry = aml.create(cr, uid, aml_vals)
				self.pool.get('gq.pr.breakdown').write(cr, uid, income, {'entry_id':income_entry})
			rcv_vals = {
					'name':pr['name'],
					'partner_id':pr['partner_id'][0],
					'date':pr['date'],
					'journal_id':pr['journal_id'][0],
					'period_id':periodCheck[0],
					'account_id':client_read['property_account_receivable'][0],
					'move_id':pr_move,
					'debit':pr['pr_amount'],
					'credit':0.00,
					}
			receivable_id = aml.create(cr, uid, rcv_vals)
			if pr['check_ids']:
				for check in pr['check_ids']:
					self.pool.get('gq.checkpayment').write(cr, uid, check, {'deposit_account':pr['check_warehouse_account'][0]})
			selfVals = {
				'state':'posted',
				'receivable_entry':receivable_id,
				'move_id':pr_move,
				'enable_edit':False
				}
			self.write(cr, uid, ids, selfVals)
			am.post(cr, uid, pr_move)
			if pr['cash_account_id']!=False or pr['cc_account_id']!=False:
				self.postpayments(cr, uid, ids)
		return True
	
	def checkTotalIncome(self,cr, uid, ids, context=None):
		for pr in self.read(cr, uid, ids, context=None):
			pr_amount = pr['pr_amount']
			total_income = 0.00
			cash_amount = pr['cash_amount']
			cc_amount = pr['cc_amount']
			total_check_amount = 0.00
			for income in pr['breakdown_ids']:
				incomeRead = self.pool.get('gq.pr.breakdown').read(cr, uid, income, ['amount'])
				percentage = incomeRead['amount']/pr['pr_amount']
				percentage = percentage*100
				self.pool.get('gq.pr.breakdown').write(cr, uid, income, {'percentage':percentage})
				total_income += incomeRead['amount']
			if pr_amount !=total_income:
				raise osv.except_osv(_('Invalid PR Details!'), _('Amount to be Paid must be equal to the details of the transaction!'))
			for check in pr['check_ids']:
				checkRead = self.pool.get('gq.checkpayment').read(cr, uid, check, ['amount'])
				total_check_amount += checkRead['amount']
			total_amountPaid = cash_amount + cc_amount + total_check_amount
			if pr_amount != total_amountPaid:
				raise osv.except_osv(_('Payment Mismatch!'), _('Total payments is not equal to the amount to be paid! Kindly check all payment options!'))
			if cash_amount > 0.00:
				if not pr['cash_account_id']:
					raise osv.except_osv(_('Undefined Account!'), _('Kindly define a cash account!'))
			if cc_amount > 0.00:
				if not pr['cc_account_id']:
					raise osv.except_osv(_('Undefined Account!'), _('Kindly define a credit card account!'))
			self.write(cr, uid, pr['id'],{'state':'confirmed'})
		return True
	
gq_pr_checks()

class checkpayment(osv.osv):
	_inherit = 'gq.checkpayment'
	_columns = {
		'pr_line_ids': fields.related('pr_id','breakdown_ids', type='one2many', relation='gq.pr.breakdown', string='PR Breakdown', readonly=True),
		'entry_id':fields.many2one('account.move','Payment Entry'),
		'reversal_entry':fields.many2one('account.move','Bounce Entry'),
		'entry_ids': fields.related('entry_id','line_id', type='one2many', relation='account.move.line', string='Clearing Entries', readonly=True),
		}
	
	def checkClearing(self, cr, uid, ids, context=None):
		am = self.pool.get('account.move')
		aml = self.pool.get('account.move.line')
		rec_list_ids = []
		for check in self.read(cr, uid, ids, context=None):
			date = datetime.now()
			date = date.strftime('%Y-%m-%d')
			periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date)], limit=1)
			if check['check_date']<=date:
				prRead = self.pool.get('gq.pr').read(cr, uid, check['pr_id'][0],context=None)
				receivable_id = prRead['receivable_entry'][0]
				ref = check['account_no'] + '(' + check['name']+')'
				print prRead
				am_vals = {
					'partner_id':prRead['partner_id'][0],
					'date':date,
					'journal_id':check['deposit_account'][0],
					'period_id':periodCheck[0],
					'ref':ref,
					}
				check_move = am.create(cr, uid, am_vals)
				client_read = self.pool.get('res.partner').read(cr, uid, prRead['partner_id'][0],context=None)
				journal_read = self.pool.get('account.journal').read(cr, uid , check['deposit_account'][0], context=None)
				aml_vals = {
							'name':ref,
							'partner_id':prRead['partner_id'][0],
							'date':date,
							'journal_id':check['deposit_account'][0],
							'period_id':periodCheck[0],
							'account_id':journal_read['default_debit_account_id'][0],
							'debit':check['amount'],
							'credit':0.00,
							'move_id':check_move,
							}
				rentry = aml.create(cr, uid, aml_vals)
				rec_ids = [receivable_id,rentry]
				rec_list_ids.append(rec_ids)
				for income in check['pr_line_ids']:
					incomeRead = self.pool.get('gq.pr.breakdown').read(cr, uid, income, context=None)
					analyticRead = self.pool.get('account.analytic.account').read(cr, uid, incomeRead['analytic_id'][0], context=None)
					receivable_sales_account = analyticRead['receivable_sales'][0]
					normal_account = analyticRead['normal_account'][0]
					accountRead = self.pool.get('account.account').read(cr, uid, normal_account,['tax_ids'])
					tax = False
					income_entry = incomeRead['entry_id']
					if accountRead['tax_ids']:
						tax=accountRead['tax_ids'][0]
					amount = (check['amount']*incomeRead['percentage'])/100
					aml_vals = {
							'partner_id':prRead['partner_id'][0],
							'date':prRead['date'],
							'journal_id':check['deposit_account'][0],
							'period_id':periodCheck[0],
							'move_id':check_move,
							'name':incomeRead['name'],
							'ref':prRead['name'],
							}
					aml_vals.update({
							'account_id':client_read['property_account_receivable'][0],
							'credit':amount,
							'debit':0.00,
							})
					rentry= aml.create(cr, uid, aml_vals)
					rec_ids = [receivable_id,rentry]
					rec_list_ids.append(rec_ids)
					aml_vals.update({
							'account_id':receivable_sales_account,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'debit':amount,
							'credit':0.00,
							})
					rsa = aml.create(cr, uid, aml_vals)
					aml_vals.update({
							'account_id':normal_account,
							'account_tax_id':tax,
							'analytic_account_id':incomeRead['analytic_id'][0],
							'credit':amount,
							'debit':0.00,
							})
					aml.create(cr, uid, aml_vals)
			for rec_ids in rec_list_ids:
				if len(rec_ids)>=2:
					continue
					aml.reconcile_partial(cr, uid, rec_ids)
			self.write(cr, uid, ids, {'state':'cleared', 'entry_id':check_move})
			self.pool.get('account.move').post(cr, uid, check_move)
			
		return True
	
checkpayment()