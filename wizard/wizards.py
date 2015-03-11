# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class gq_pr_check_clear(osv.osv_memory):
    """
        close period
    """
    _name = "gq.pr.check.clear"
    _description = "Check Clearing"
    _columns = {
        'date_start':fields.date('Date Start'),
        'date_stop':fields.date('Date End'),
        'bank_id':fields.many2one('account.journal','Bank Name', required=True, domain=[('type','=','bank')]),
    }
    
    def clearDate(self, cr, uid, ids, context=None):
        am = self.pool.get('account.move')
        aml = self.pool.get('account.move.line')
        for form in self.read(cr, uid, ids, context=context):
            journal_read = self.pool.get('account.journal').read(cr, uid,form['bank_id'][0],['default_debit_account_id'])
            checkSearch = self.pool.get('gq.checkpayment').search(cr, uid, [('check_date','>=',form['date_start']),('check_date','<=',form['date_stop']),('state','=','draft')])
            periodCheck = self.pool.get('account.period').search(cr, uid, [('date_start','<=',form['date_start']),('date_stop','>=',form['date_stop'])])
            print periodCheck
            if len(periodCheck)>=2:
                raise osv.except_osv(_('Invalid Period!'), _('Dates should be the same month!'))
            for check in checkSearch:
                checkRead = self.pool.get('gq.checkpayment').read(cr, uid, check, context=None)
                prRead = self.pool.get('gq.pr').read(cr, uid, checkRead['pr_id'][0],context=None)
                check_name = checkRead['name'] + ' / ' + checkRead['account_no'] + ' / ' +prRead['name']
                am_vals = {
                    'partner_id':prRead['partner_id'][0],
                    'date':checkRead['check_date'],
                    'journal_id':form['bank_id'][0],
                    'period_id':periodCheck[0],
                    'ref':check_name,
                    }
                pr_move = am.create(cr, uid, am_vals)
                receivable_id = prRead['receivable_entry'][0]
                entryRead = self.pool.get('account.move.line').read(cr, uid, prRead['receivable_entry'][0], ['account_id'])
                check_vals = {
                    'name':check_name,
                    'partner_id':prRead['partner_id'][0],
                    'date':checkRead['check_date'],
                    'journal_id':form['bank_id'][0],
                    'period_id':periodCheck[0],
                    'account_id':journal_read['default_debit_account_id'][0],
                    'move_id':pr_move,
                    'debit':checkRead['amount'],
                    'credit':0.00,
                    }
                aml.create(cr, uid, check_vals)
                rcv_vals = {
                    'name':check_name,
                    'partner_id':prRead['partner_id'][0],
                    'date':checkRead['check_date'],
                    'journal_id':form['bank_id'][0],
                    'period_id':periodCheck[0],
                    'account_id':entryRead['account_id'][0],
                    'move_id':pr_move,
                    'credit':checkRead['amount'],
                    'debit':0.00,
                        }
                cc_receivable_id = aml.create(cr, uid, rcv_vals)
                rec_ids = [receivable_id,cc_receivable_id]
                aml.reconcile_partial(cr, uid, rec_ids)
                
                    
                    
        return {'type': 'ir.actions.act_window_close'}            

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
