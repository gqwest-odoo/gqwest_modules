from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp

class payment(osv.osv):
    
    def _get_company(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        return company_id or False
    _name = 'account.payment.items'
    _description = "Payment Orders"
    _columns = {
        'name':fields.char('Payment Order Number', size=32),
	    'date':fields.date('Date'),
        'check_date':fields.date('Date'),
        'partner_id':fields.many2one('res.partner','Payee', domain=[('supplier','=',True)], required=True),
        'comment':fields.text('Other Info'),
        'checkAssigned':fields.boolean('Check Assigned'),
        'checkAudit':fields.boolean('Audited'),
        'funding_date':fields.date('Funding Date'),
        'funded_by':fields.many2one('res.users','Funded by'),
        'releasing_date':fields.date('Releasing Date'),
        'released_by':fields.many2one('res.users','Release by'),
        'editorAudit':fields.boolean('Editor Audit'),
        'state':fields.selection([
                            ('draft','Draft'),
                            ('confirm','Confirmed'),
                            ('fetched','Invoices Fetched'),
                            ('approved','Approved'),
                            ('for_funding','For Funding'),
                            ('funded','Funded'),
                            ('released','Released'),
                            ('cancelled','Cancelled')], 'Request Status'),
        'date_start':fields.date('Period Start',required=True),
        'date_end':fields.date('Period End',required=True)
        }
    
    _defaults = {
        'name':'NEW',
        'state':'draft',
        }
    
    def create(self, cr, uid, vals, context=None):
        name=self.pool.get('ir.sequence').get(cr, uid, 'payment.request.items')
        vals.update({'name':name})
        if vals['partner_id']:
            if not self.pool.get('account.payment.items').search(cr, uid, [('partner_id','=',vals['partner_id']),('state','in',['draft','confirm','fetched'])]):
                return super(payment, self).create(cr, uid, vals, context=context)
            else:
                raise osv.except_osv(_('Pending Transaction!'), _('There is a pending transaction for this partner!'))
payment()

class payment_line(osv.osv):
    _name = 'account.payment.items.line'
    _description  = "Particulars"
    _columns = {
        'name':fields.char('Particulars', size=64, required=True),
        'payment_id':fields.many2one('account.payment.items','Payment ID', ondelete='cascade'),
        'moveline_id':fields.many2one('account.move.line','Entry'),
        'ref':fields.char('Reference', size=64),
        'amount':fields.float('Amount', required=True),
        'amount_residual':fields.float('Unpaid Amount', required=True),
        'amount_topay':fields.float('Amount to Pay'),
        'account_id':fields.many2one('account.account','Account'),
        }
payment_line()

class ap(osv.osv):
    _inherit = 'account.payment.items'
    _columns = {
        'line_ids':fields.one2many('account.payment.items.line','payment_id','Payment Lines'),
        'bank_id':fields.many2one('account.journal', 'Bank', domain=[('type','=','bank')]),
        'amount_due':fields.float('Amount to Pay'),
        'account_no':fields.char('Account No', size=32),
        'fetched':fields.boolean('Fetched'),
        'check_num':fields.char('Check Number', size=32),
        'payable_entry':fields.many2one('account.move', 'Payable Entry'),
        'payable_ids': fields.related('payable_entry','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
        }
    
    def confirm(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if not ap['line_ids']:
                raise osv.except_osv(_('Undefined Details!'), _('Please define the expense lines!'))
            else:
                return self.write(cr, uid, ids, {'state':'confirm'})
    def fetchInvoices(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            client_read = self.pool.get('res.partner').read(cr, uid, ap['partner_id'][0],context=None)
            payables = self.pool.get('account.move.line').search(cr, uid,[('partner_id','=',ap['partner_id'][0]),
                                                                        ('date','<=',ap['date_end']),
                                                                        ('account_id','=',client_read['property_account_payable'][0]),
                                                                        ('date','>=',ap['date_start']),
                                                                        ('debit','=',0.00),
                                                                        ('invoice','!=',False),
                                                                        ('reconcile_id','=',False)])
            for payable in payables:
                payableRead = self.pool.get('account.move.line').read(cr, uid, payable, context=None)
                invoiceRead = self.pool.get('account.invoice').read(cr, uid, payableRead['invoice'][0],context=None)
                print payableRead
                print '\n'
                vals = {
                    'moveline_id':payable,
                    'name':payableRead['ref'],
                    'payment_id':ap['id'],
                    'account_id':payableRead['account_id'][0],
                    'ref':invoiceRead['supplier_invoice_number'],
                    'amount':payableRead['credit'],
                    'amount_residual':payableRead['amount_residual']
                    }
                self.pool.get('account.payment.items.line').create(cr, uid, vals)
            self.write(cr, uid, ap['id'],{'state':'fetched'})
        return True
    def set_for_funding(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            for line in ap['line_ids']:
                lineRead = self.pool.get('account.payment.items.line').read(cr, uid, line, context=None)
                if lineRead['amount_residual']<lineRead['amount_topay']:
                    raise osv.except_osv(_('Over!'), _('Amount to pay is over the residual amount!'))
        return self.write(cr, uid, ids,{'state':'for_funding'})
    
    def edit_accts(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if ap['editorAudit']==True:
                return self.write(cr, uid, ids, {'editorAudit':False})
            elif ap['editorAudit']==False:
                return self.write(cr, uid, ids, {'editorAudit':True})
                
    def assignCheck(self, cr, uid, ids,context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if ap['bank_id']==False or ap['account_no']==False or ap['amount_due']==False or ap['check_num']==False:
                raise osv.except_osv(_('Undefined Details!'), _('Please complete check details!'))
            else:
                total_amount = False
                for line in ap['line_ids']:
                    readLine = self.pool.get('account.payment.line').read(cr, uid, line, ['amount_topay'])
                    total_amount+=readLine['amount_topay']
                if ap['amount_due']!=total_amount:
                    raise osv.except_osv(_('Unmatched Amounts!'), _('Please check amount to pay!'))
                else:
                    return self.write(cr, uid, ids, {'checkAssigned':True})
    
    def audit(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'checkAudit':True})
    
    def approve(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'approved'})
    
    def approve2(self, cr, uid, ids, context=None):
        am = self.pool.get('account.move')
        aml = self.pool.get('account.move.line')
        for ap in self.read(cr, uid, ids, context=None):
            payableTotal = False
            journal_id = ap['bank_id'][0]
            periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',ap['date']),('date_stop','>=',ap['date'])], limit=1)
            client_read = self.pool.get('res.partner').read(cr, uid, ap['partner_id'][0],context=None)
            am_vals = {
                    'partner_id':ap['partner_id'][0],
                    'date':ap['date'],
                    'journal_id':journal_id,
                    'period_id':periodCheck[0],
                    'ref':ap['name'],
                    }
            pr_move = am.create(cr, uid, am_vals)
            for line in ap['line_ids']:
                lineRead = self.pool.get('account.payment.items.line').read(cr, uid, line, context=None)
                payableTotal+=lineRead['amount']
                aml_vals = {
                        'name':lineRead['name'],
                        'partner_id':ap['partner_id'][0],
                        'date':ap['date'],
                        'journal_id':journal_id,
                        'period_id':periodCheck[0],
                        'account_id':lineRead['account_id'][0],
                        'analytic_account_id':lineRead['analytic_id'][0],
                        'debit':lineRead['amount'],
                        'credit':0.00,
                        'move_id':pr_move,
                        }
                aml.create(cr, uid, aml_vals)
            aml_vals = {
                        'name':lineRead['name'],
                        'partner_id':ap['partner_id'][0],
                        'date':ap['date'],
                        'journal_id':journal_id,
                        'period_id':periodCheck[0],
                        'account_id':client_read['property_account_payable'][0],
                        'credit':payableTotal,
                        'debit':0.00,
                        'move_id':pr_move,
                        }
            aml.create(cr, uid, aml_vals)
            self.write(cr, uid, ids, {'state':'approved','payable_entry':pr_move})
        return True
    
    def cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelled'})
    
ap()