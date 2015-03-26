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
    _name = 'account.payment'
    _description = "Payment Orders"
    _columns = {
        'name':fields.char('Payment Order Number', size=32),
	    'date':fields.date('Date'),
        'check_date':fields.date('Date'),
        'partner_id':fields.many2one('res.partner','Payee', domain=[('supplier','=',True)], required=True),
        'comment':fields.text('Other Info'),
        'requestor_id':fields.many2one('res.users','Requestor'),
        'approving_officer':fields.many2one('res.users','Approving Officer'),
        'checkAssigned':fields.boolean('Check Assigned'),
        'checkAudit':fields.boolean('Audited'),
        'for_liquidation':fields.boolean('For Liquidation'),
        'ca_account_id':fields.many2one('account.account','Charged Account'),
        'funding_date':fields.date('Funding Date'),
        'funded_by':fields.many2one('res.users','Funded by'),
        'releasing_date':fields.date('Releasing Date'),
        'released_by':fields.many2one('res.users','Release by'),
        'editorAudit':fields.boolean('Editor Audit'),
        'type':fields.selection([('for_liquidation','For Liquidation'),
                                 ('expense','Direct Expense'),
                                 ('advances','Advances')], 'Type'),
        'state':fields.selection([
                            ('draft','Draft'),
                            ('confirm','Confirmed'),
                            ('approved','Approved'),
                            ('for_funding','For Funding'),
                            ('funded','Funded'),
                            ('released','Released'),
                            ('for_liquidation','Released for Liquidation'),
                            ('liquidated','Liquidated'),
                            ('cancelled','Cancelled')], 'Request Status'),
        }
    
    _defaults = {
        'name':'NEW',
        'state':'draft',
        'requestor_id':lambda obj, cr, uid, context: uid,
        'editorAudit':True,
        }
    
    def create(self, cr, uid, vals, context=None):
        name=self.pool.get('ir.sequence').get(cr, uid, 'payment.request')
        vals.update({'name':name})
        return super(payment, self).create(cr, uid, vals, context=context)
payment()

class payment_line(osv.osv):
    _name = 'account.payment.line'
    _description  = "Particulars"
    _columns = {
        'name':fields.char('Particulars', size=64, required=True),
        'payment_id':fields.many2one('account.payment','Payment ID', ondelete='cascade'),
        'liquidation_id':fields.many2one('account.payment','Liquidation ID', ondelete='cascade'),
        'ref':fields.char('Reference', size=64),
        'amount':fields.float('Amount', required=True),
        'analytic_id':fields.many2one('account.analytic.account','Class',domain=[('type','=','normal')]),
        }
payment_line()

class payment_deposits(osv.osv):
    _name = 'account.payment.deposit'
    _description  = "Deposits"
    _columns = {
        'name':fields.char('Deposit Slip', size=64, required=True),
        'liquidation_id':fields.many2one('account.payment','Liquidation ID', ondelete='cascade'),
        'amount':fields.float('Amount', required=True),
        'account_id':fields.many2one('account.account','Bank',domain=[('type','=','liquidity')]),
        }
payment_line()

class ap(osv.osv):
    _inherit = 'account.payment'
    _columns = {
        'line_ids':fields.one2many('account.payment.line','payment_id','Payment Lines'),
        'liquidation_ids':fields.one2many('account.payment.line','liquidation_id','Liquidation Lines'),
        'deposit_ids':fields.one2many('account.payment.deposit','liquidation_id','Deposits'),
        'bank_id':fields.many2one('account.journal', 'Bank', domain=[('type','=','bank')]),
        'journal_id':fields.many2one('account.journal','Expense Journal', domain=[('type','=','purchase')]),
        'amount_due':fields.float('Amount to Pay'),
        'color': fields.integer('Color Index'),
        'account_no':fields.char('Account No', size=32),
        'check_num':fields.char('Check Number', size=32),
        'payable_entry':fields.many2one('account.move', 'Payable Entry'),
        'pay_entry':fields.many2one('account.move.line', 'Payable ID'), 
        'payable_ids': fields.related('payable_entry','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
        'release_id':fields.many2one('account.move','Release Entry'),
        'release_ids': fields.related('release_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
        }
    
    def funded(self,cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
             date = datetime.now()
             date = date.strftime('%m/%d/%Y')
             self.write(cr, uid, ids, {'state':'funded', 'funded_by':uid,'funding_date':date})
        return True
    
#    def confirm_for_liquidation(self, cr, uid, ids, context=None):
#        for ap in self.read(cr, uid, ids, context=None):
            
    
    def release(self, cr, uid, ids, context=None):
        aml = self.pool.get('account.move.line')
        rec_list_ids = []
        for ap in self.read(cr, uid, ids, context=None):
            if not ap['for_liquidation']:
                periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',ap['date']),('date_stop','>=',ap['date'])], limit=1)
                client_read = self.pool.get('res.partner').read(cr, uid, ap['partner_id'][0],context=None)
                bank_read = self.pool.get('account.journal').read(cr, uid, ap['bank_id'][0],context=None)
                vals = {
                    'ref':ap['name'],
                    'journal_id':ap['bank_id'][0],
                    'partner_id':ap['partner_id'][0],
                    'period_id':periodCheck[0],
                    'date':ap['check_date']
                    }
                entry = self.pool.get('account.move').create(cr, uid, vals)
                aml_vals = {
                            'name':ap['name'],
                            'partner_id':ap['partner_id'][0],
                            'date':ap['check_date'],
                            'journal_id':ap['bank_id'][0],
                            'period_id':periodCheck[0],
                            'account_id':client_read['property_account_payable'][0],
                            'debit':ap['amount_due'],
                            'credit':0.00,
                            'move_id':entry,
                            }
                cc_receivable_id = aml.create(cr, uid, aml_vals)
                name = ap['name'] + '/'+ap['check_num']
                aml_vals = {
                            'name':name,
                            'partner_id':ap['partner_id'][0],
                            'date':ap['check_date'],
                            'journal_id':ap['bank_id'][0],
                            'period_id':periodCheck[0],
                            'account_id':bank_read['default_credit_account_id'][0],
                            'credit':ap['amount_due'],
                            'debit':0.00,
                            'move_id':entry,
                            }
                aml.create(cr, uid, aml_vals)
                rec_ids = [ap['pay_entry'][0],cc_receivable_id]
                rec_list_ids.append(rec_ids)
                self.pool.get('account.move').post(cr, uid, entry)
                for rec_ids in rec_list_ids:
                    if len(rec_ids)>=2:
                        aml.reconcile_partial(cr, uid, rec_ids)
                date = datetime.now()
                date = date.strftime('%m/%d/%Y')
                self.write(cr, uid, ap['id'], {'state':'released', 'released_by':uid,'releasing_date':date,'release_id':entry})
            elif ap['for_liquidation']:
                date = datetime.now()
                date = date.strftime('%m/%d/%Y')
                periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date)], limit=1)
                client_read = self.pool.get('res.partner').read(cr, uid, ap['partner_id'][0],context=None)
                bank_read = self.pool.get('account.journal').read(cr, uid, ap['bank_id'][0],context=None)
                vals = {
                    'ref':ap['name'],
                    'journal_id':ap['bank_id'][0],
                    'partner_id':ap['partner_id'][0],
                    'period_id':periodCheck[0],
                    'date':ap['check_date']
                    }
                entry = self.pool.get('account.move').create(cr, uid, vals)
                aml_vals = {
                            'name':ap['name'],
                            'partner_id':ap['partner_id'][0],
                            'date':date,
                            'journal_id':ap['bank_id'][0],
                            'period_id':periodCheck[0],
                            'account_id':ap['ca_account_id'][0],
                            'debit':ap['amount_due'],
                            'credit':0.00,
                            'move_id':entry,
                            }
                aml.create(cr, uid, aml_vals)
                name = ap['name'] + '/'+ap['check_num']
                aml_vals = {
                            'name':name,
                            'partner_id':ap['partner_id'][0],
                            'date':date,
                            'journal_id':ap['bank_id'][0],
                            'period_id':periodCheck[0],
                            'account_id':bank_read['default_credit_account_id'][0],
                            'credit':ap['amount_due'],
                            'debit':0.00,
                            'move_id':entry,
                            }
                aml.create(cr, uid, aml_vals)
                self.pool.get('account.move').post(cr, uid, entry)
                self.write(cr, uid, ap['id'], {'state':'for_liquidation', 'released_by':uid,'releasing_date':date,'release_id':entry})
        return True            
    
    def assignCheck(self, cr, uid, ids,context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if not ap['for_liquidation']:
                if ap['bank_id']==False or ap['account_no']==False or ap['amount_due']==False or ap['check_num']==False:
                    raise osv.except_osv(_('Undefined Details!'), _('Please complete check details!'))
                else:
                    total_amount = False
                    for line in ap['line_ids']:
                        readLine = self.pool.get('account.payment.line').read(cr, uid, line, ['amount'])
                        total_amount+=readLine['amount']
                    if ap['amount_due']!=total_amount:
                        raise osv.except_osv(_('Unmatched Amounts!'), _('Please check amount to pay!'))
                    else:
                        return self.write(cr, uid, ids, {'checkAssigned':True})
            else:
                return self.write(cr, uid, ids, {'checkAssigned':True})
    def audit(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'checkAudit':True})
    
    def confirm(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if not ap['for_liquidation']:
                if not ap['line_ids']:
                    raise osv.except_osv(_('Undefined Details!'), _('Please define the expense lines!'))
                else:
                    return self.write(cr, uid, ids, {'state':'confirm','editorAudit':False})
            else:
                return self.write(cr, uid, ids, {'state':'confirm','editorAudit':False})
    def approve(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'approved'})
    
    def edit_accts(self, cr, uid, ids, context=None):
        for ap in self.read(cr, uid, ids, context=None):
            if ap['editorAudit']==True:
                return self.write(cr, uid, ids, {'editorAudit':False})
            elif ap['editorAudit']==False:
                return self.write(cr, uid, ids, {'editorAudit':True})
    
    
    def set_for_funding(self, cr, uid, ids, context=None):
        am = self.pool.get('account.move')
        aml = self.pool.get('account.move.line')
        for ap in self.read(cr, uid, ids, context=None):
            if not ap['for_liquidation']:
                payableTotal = False
                journal_id = ap['journal_id'][0]
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
                    lineRead = self.pool.get('account.payment.line').read(cr, uid, line, context=None)
                    if not lineRead['account_id'] or not lineRead['account_id']:
                        raise osv.except_osv(_('Undefined Account/Class!'), _('Please assign an account/class!'))
                for line in ap['line_ids']:
                    lineRead = self.pool.get('account.payment.line').read(cr, uid, line, context=None)
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
                            'name':ap['name'],
                            'partner_id':ap['partner_id'][0],
                            'date':ap['date'],
                            'journal_id':journal_id,
                            'period_id':periodCheck[0],
                            'account_id':client_read['property_account_payable'][0],
                            'credit':payableTotal,
                            'debit':0.00,
                            'move_id':pr_move,
                            }
                payable_id = aml.create(cr, uid, aml_vals)
                #self.pool.get('account.move').post(cr, uid, pr_move)
                self.write(cr, uid, ap['id'], {'state':'for_funding','payable_entry':pr_move,'pay_entry':payable_id})
            else:
                self.write(cr, uid, ap['id'], {'state':'for_funding'})
        return True
    
       
    def cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelled'})
    
ap()

class account_bill(osv.osv):
    _name = 'account.bill'
    _description = "Bills Management"
    _columns = {
        'name':fields.char('Bill Number',size=64, readonly=True),
        'type':fields.selection([
                            ('phone','Telephone/Mobile'),
                            ('creditcard','Credit Card'),
                            ],'Bill Type'),
        'partner_id':fields.many2one('res.partner','Client'),
        'charged':fields.boolean('Charged to Credit Card?'),
        }
account_bill()

class account_bill_phone(osv.osv):
    _name = 'account.bill.phone'
    _description = "PhoneBill Breakdown"
    _columns = {
        'name':fields.char('Description', size=64, required=True),
        'mobile':fields.char('Mobile #', size=11, required=True),
        'account':fields.char('Account #',size=32, required=True),
        'bill_start':fields.date('Bill Period Start'),
        'bill_end':fields.date('Bill Period End'),
        'due_date':fields.date('Due Date'),
        'amount':fields.float('Amount'),
        'bill_id':fields.many2one('account.bill','Bill #', ondelete='cascade'),
        }
account_bill_phone()

class ab(osv.osv):
    _inherit = 'account.bill'
    _columns = {
        'phone_ids':fields.one2many('account.bill.phone', 'bill_id'),
        }
ab()

class account_pettycash(osv.osv):
    _name = 'account.pettycash'
    _description = "Pettycash"
    _columns = {
        'name':fields.char('PC Request', size=64, readonly=True),
        'date':fields.date('Request Date', required=True),
        'liquidated':fields.boolean('Liquidated', readonly=True),
        'journal_id':fields.many2one('account.journal','Pettycash Account', domain=[('type','=','cash')], required=True),
        'comment':fields.text('Notes'),
        'approving_officer':fields.many2one('res.users','Approving Officer', required=True),
        'amount_requested':fields.float('Amount Requested'),
        'amount_remaining':fields.float('Amount Remaining'),
        'amount_approved':fields.float('Approved Amount'),
        'state':fields.selection([
                            ('draft','Draft'),
                            ('confirm','Confirmed'),
                            ('approved','Approved'),
                            ('released','Released'),
                            ('liquidated','Liquidated'),
                            ('cancelled','Cancelled')], 'Request Status'),
        'class_id':fields.many2one('account.analytic.account', 'Department', required=True),
        'requestor_id':fields.many2one('res.users','Requestor'),
        }
    _defaults = {
        'name':'NEW',
        'state':'draft',
        'requestor_id':lambda obj, cr, uid, context: uid,
        }
    
    def create(self, cr, uid, vals, context=None):
        name=self.pool.get('ir.sequence').get(cr, uid, 'gq.apc')
        vals.update({'name':name})
        return super(account_pettycash, self).create(cr, uid, vals, context=context)
    
    def confirm(self, cr, uid, ids, context=None):
        for apc in self.read(cr, uid, ids, context=None):
                self.write(cr, uid, apc['id'], {'state':'confirm'})
        return True
    
    def approve(self, cr, uid, ids, context=None):
        for apc in self.read(cr, uid, ids, context=None):
            self.write(cr, uid, apc['id'],{'state':'approved'})
        return True
    def release(self, cr, uid, ids, context=None):
        for apc in self.read(cr, uid, ids, context=None):
            self.write(cr, uid, apc['id'],{'state':'released'})
        return True
    
    def liquidate(self, cr, uid, ids, context=None):
        for apc in self.read(cr, uid, ids, context=None):
            checkConsumed = apc['amount_approved']-apc['amount_remaining']
            consumedLines = 0.00
            for line in apc['line_ids']:
                lineRead = self.pool.get('account.pettycash.line').read(cr, uid, line, ['amount'])
                consumedLines+=lineRead['amount']
            if consumedLines!=checkConsumed:
                raise osv.except_osv(_('Liquidation Failed!'), _('Please check the liquidation lines!'))
            elif consumedLines==checkConsumed:
                self.write(cr, uid, ids, {'state':'liquidated','liquidated':True})
        return True
account_pettycash()

class account_pettycash_line(osv.osv):
    _name = 'account.pettycash.line'
    _description = "Pettycash Request Details"
    _columns = {
        'name':fields.char('Description',size=64, required=True),
        'ref':fields.char('Reference', size=64, help="Reference numbers for the transaction. i.e. Invoice/Receipts"),
        'amount':fields.float('Amount', required=True),
        'pc_id':fields.many2one('account.pettycash', 'Pettycash Transaction', ondelete='cascade'),
        }
account_pettycash_line()

class account_pettycash_liquidation(osv.osv):
    _name = 'account.pettycash.liquidation'
    _description = "Pettycash Liquidation"
    _columns = {
        'name':fields.char('Liquidation', size=64, readonly=True),
        'pc_id':fields.many2one('account.journal','Pettycash Account', domain=[('type', '=', 'cash')]),
        'date':fields.date('Liquidation Date',required=True),
        'fetched':fields.boolean('Fetched'),
        'date_start':fields.date('Date Start'),
        'date_stop':fields.date('Date End'),
        'state':fields.selection([
                            ('draft','Draft'),
                            ('confirm','Confirmed'),
                            ('approved','Approved'),
                            ('released','Released'),
                            ('cancelled','Cancelled')], 'Request Status'), 
        }
    _defaults ={
        'state':'draft',
        }
    
    def create(self, cr, uid, vals, context=None):
        name=self.pool.get('ir.sequence').get(cr, uid, 'gq.apcl')
        vals.update({'name':name})
        return super(account_pettycash_liquidation, self).create(cr, uid, vals, context=context)
    
    def fetchData(self, cr, uid, ids, context=None):
        for pcl in self.read(cr, uid, ids, context=None):
            getLiquidations = self.pool.get('account.pettycash').search(cr, uid, [('date','>=',pcl['date_start']),('date','<=',pcl['date_stop'])])
            if not getLiquidations:
                raise osv.except_osv(_('No Existing Liquidations!'), _('There are no pettycash liquidations for the specified period!'))
            elif getLiquidations:
                for liquidation in getLiquidations:
                    liquidationRead = self.pool.get('account.pettycash').read(cr, uid, liquidation, context=None)
                    for line in liquidationRead['line_ids']:
                        lineRead = self.pool.get('account.pettycash.line').read(cr, uid, line, context=None)
                        vals = {
                            'name':lineRead['name'],
                            'ref':lineRead['ref'],
                            'apc_id':liquidation,
                            'requestor_id':liquidationRead['requestor_id'][0],
                            'date':liquidationRead['date'],
                            'amount':lineRead['amount'],
                            'analytic_id':liquidationRead['class_id'][0],
                            'pcl_id':pcl['id'],
                            }
                        self.pool.get('account.pettycash.liquidation.line').create(cr, uid, vals)
        return True
account_pettycash_liquidation()

class apcll(osv.osv):
    _name = 'account.pettycash.liquidation.line'
    _description = "Liquidation Lines"
    _columns = {
        'name':fields.char('Description',size=64),
        'ref':fields.char('Reference',size=64),
        'apc_id':fields.many2one('account.pettycash','Pettycash Request'),
        'requestor_id':fields.many2one('res.users', 'Requestor'),
        'date':fields.date('Request Date'),
        'amount':fields.float('Amount'),
        'account_id':fields.many2one('account.account', 'Account'),
        'analytic_id':fields.many2one('account.analytic.account', 'Class'),
        'pcl_id':fields.many2one('account.pettycash.liquidation', 'Liquidation', ondelete='cascade'),
        }
apcll()

class apl(osv.osv):
    _inherit = 'account.pettycash.liquidation'
    _columns = {
        'liquidation_lines':fields.one2many('account.pettycash.liquidation.line','pcl_id','Liquidation Lines'),
        'bank_id':fields.many2one('account.journal', 'Bank', domain=[('type','=','bank')]),
        'checkAmount':fields.float('Check Amount'),
        'account_no':fields.char('Account No', size=64),
        'check_no':fields.char('Check No', size=64), 
        }
    
    def confirm(self, cr, uid, ids, context=None):
        for apl in self.read(cr, uid, ids, context=None):
            currentAPC = False
            currentAPCtotal = 0.00
            previousAPC = False
            previousAPCtotal = 0.00
            for line in apl['liquidation_lines']:
                lineRead = self.pool.get('account.pettycash.liquidation.line').read(cr, uid, line, context=None)
                pcrRead = self.pool.get('account.pettycash').read(cr, uid, lineRead['apc_id'][0],context=None)
                if currentAPC!=lineRead['apc_id'][0]:
                    currentAPC = lineRead['apc_id'][0]
                    currentAPCtotal = lineRead['amount']
                elif currentAPC==lineRead['apc_id'][0]:
                    currentAPCtotal += lineRead['amount']
                periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',pcrRead['date']),('date_stop','>=',pcrRead['date'])], limit=1)
                if not pcrRead['move_id']:
                    vals = {
                        'ref':pcrRead['name'],
                        'period_id':periodCheck[0],
                        'date':pcrRead['date'],
                        'journal_id':pcrRead['journal_id'][0]
                        }
                    pcrMove = self.pool.get('account.move').create(cr, uid, vals)
                    self.pool.get('account.pettycash').write(cr, uid, lineRead['apc_id'][0],{'move_id':pcrMove,'liquidation_id':apl['id']})
                    if not lineRead['account_id']:
                        raise osv.except_osv(_('Account Missing!'), _('Please define the account for the liquidation line!'))
                    else:
                        name = lineRead['name'] + lineRead['ref']
                        vals = {
                            'name':name,
                            'ref':pcrRead['name'],
                            'period_id':periodCheck[0],
                            'date':pcrRead['date'],
                            'journal_id':pcrRead['journal_id'][0],
                            'account_id':lineRead['account_id'][0],
                            'analytic_account_id':lineRead['analytic_id'][0],
                            'debit':lineRead['amount'],
                            'credit':0.00,
                            'move_id':pcrMove,
                            }
                        self.pool.get('account.move.line').create(cr, uid, vals)
                elif pcrRead['move_id']:
                    name = lineRead['name'] + lineRead['ref']
                    vals = {
                        'name':name,
                        'ref':pcrRead['name'],
                        'period_id':periodCheck[0],
                        'date':pcrRead['date'],
                        'journal_id':pcrRead['journal_id'][0],
                        'account_id':lineRead['account_id'][0],
                        'analytic_account_id':lineRead['analytic_id'][0],
                        'debit':lineRead['amount'],
                        'credit':0.00,
                        'move_id':pcrMove,
                        }
                    self.pool.get('account.move.line').create(cr, uid, vals)
            checkAllLiquidations = self.pool.get('account.pettycash').search(cr, uid, [('liquidation_id','=',apl['id'])])
            for apc in checkAllLiquidations:
                apcRead = self.pool.get('account.pettycash').read(cr, uid, apc, context=None)
                journalRead = self.pool.get('account.journal').read(cr, uid, apcRead['journal_id'][0],['default_credit_account_id'])
                periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',apcRead['date']),('date_stop','>=',apcRead['date'])], limit=1)
                totaldebit = False
                for line in  apcRead['move_ids']:
                    lineRead = self.pool.get('account.move.line').read(cr, uid, line, ['debit'])
                    totaldebit+=lineRead['debit']
                vals = {
                        'name':apcRead['name'],
                        'ref':apcRead['name'],
                        'period_id':periodCheck[0],
                        'date':apcRead['date'],
                        'journal_id':pcrRead['journal_id'][0],
                        'account_id':journalRead['default_credit_account_id'][0],
                        'credit':totaldebit,
                        'debit':0.00,
                        'move_id':apcRead['move_id'][0],
                        }
                self.pool.get('account.move.line').create(cr, uid, vals)
        return True
                
                
apl()

class pc_trans(osv.osv):
    _inherit = 'account.pettycash'
    _columns = {
            'line_ids':fields.one2many('account.pettycash.line', 'pc_id', 'Pettycash Details'),
            'move_id':fields.many2one('account.move','Journal Entry'),
            'move_ids': fields.related('move_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
            'liquidation_id':fields.many2one('account.pettycash.liquidation','Liquidation'),
            }
pc_trans()        