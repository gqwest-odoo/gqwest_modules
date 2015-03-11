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
alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
pw_length = 10


class gq_servicing(osv.osv):
	_name = "gq.servicing"
	_description = "Machine Servicing Request"
	_columns = {
		'name':fields.char('MSR Number', size=64),
		'partner_id':fields.many2one('res.partner','Client',required=True, domain=[('customer','=',True)]),
		'request_date':fields.datetime('Request Date',readonly=True, required=True),
        'service_type' : fields.selection([
                                                        ('repair','Repair'),
                                                        ('rework','Rework'),
                                                        ('replacement','Replacement'),
                                                        ('membrane_cleaning','Membrane Cleaning'),
                                                        ('sanitation','Sanitation')], 'Service Type'),
		'state': fields.selection([
                                          ('draft','Draft'),
                                          ('confirm','Confirmed'),
                                          ('approve','Approved'),
                                          ('assigned','Assigned'),
                                          ('in_progress','In Progress'),
                                          ('in_progress2','In Progress'),
                                          ('service_validation','Service Validation'),
                                          ('closed','Closed'),
                                          ('backjob','For Backjob'),
                                          ('hold','Hold'),
                                          ('cancel','Cancelled')],'State'),
		'service_schedule' : fields.date('Service Schedule'),
        'ccd_recommendations' : fields.text('CCD Recommendations'),
        'ccd_requests' : fields.text('CCD Requests'),
        'etd_remarks' : fields.text('Remarks and Recommendations'),
        'tds_source': fields.char('Source',size=15),
        'tds_product': fields.char('Product',size=15),
        'tds_reject': fields.char('Reject',size=15),
        'fr_permeate': fields.char('Permeate',size=15),
        'fr_concentrate': fields.char('Concentrate',size=15),
        'pre_inlet': fields.char('Inlet',size=15),
        'remitted':fields.boolean('Remitted?'),
        'pre_outlet': fields.char('Outlet',size=15),
        'mr_before': fields.char('Before',size=15),
        'mr_after': fields.char('After',size=15),
        'time_in': fields.datetime('Time In'),
        'time_out': fields.datetime('Time Out'),
        'warehouse_id':fields.many2one('stock.warehouse','Warehouse'),
        'release_type':fields.many2one('stock.picking.type','Release Type'),
        'reservation_type':fields.many2one('stock.picking.type','Reservation Type'),
		'service_code':fields.char('Service Code',size=64),
		'verifier':fields.char('Verify Code', size=64),
		'technician_id':fields.many2one('res.users','Assigned Technician'),
		'sourcejob_id':fields.many2one('gq.servicing','Source Job'),
		'cash_amount':fields.float('Cash Payment'),
		'cash_account_id':fields.many2one('account.account','Cash Account', domain=[('type','=','liquidity')]),
		'receivable_id':fields.many2one('account.move','Receivable Entry'),
		'receivable_ids': fields.related('receivable_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
		'payment_id':fields.many2one('account.move','Payment Entry'),
		'payment_ids': fields.related('payment_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
		}
	_defaults = {
		'name':'New MSR',
		'state':'draft',
		'request_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		}
	
	def create(self, cr, uid, vals, context=None):
		name=self.pool.get('ir.sequence').get(cr, uid, 'gq.servicing')
		vals.update({'name':name})
		return super(gq_servicing, self).create(cr, uid, vals, context=context)
	
	def testmail(self, cr, uid, ids, context=None):
		for service in self.read(cr, uid, ids, context=None):
			login = 'odoo@aquabest.biz'
			password = 'satya0969'
			number = '09152489739'
			device = '9433'
			message = 'This is your service code for service request number' + service['name'] +':'+service['service_code']
			url ='http://smsgateway.me/api/v3/messages/send?email='+login+'&password='+password+'&device='+device+'&number='+number+'&message='+message
			print url
			response = urllib2.urlopen(url)
		return True
	
	def approve(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state':'approve'})
	def assign(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state':'assigned'})
	
		
	def login(self, cr, uid, ids, context=None):
		for service in self.read(cr, uid, ids, context=None):
			if service['verifier']==service['service_code']:
				date = datetime.now()
				date = date.strftime('%Y-%m-%d %H:%M:%S')
				self.write(cr, uid, service['id'], {'time_in':date,'verifier':False,'state':'in_progress2'})
			else:
				raise osv.except_osv(_('Wrong Service Code!'), _('Check the service code before servicing!'))
		return True
	
	def backjob(self, cr, uid, ids, context=None):
		for service in self.read(cr, uid, ids, context=None):
			if service['verifier']==service['service_code']:
				date = datetime.now()
				date = date.strftime('%Y-%m-%d %H:%M:%S')
				self.write(cr, uid, service['id'], {'time_out':date,'verifier':False,'state':'backjob'})
				vals = {
					'partner_id':service['partner_id'][0],
					'request_date':date,
					'service_type':'repair',
					'sourcejob_id':service['id'],
					'technician_id':service['technician_id'][0]
					}
				service_new = self.pool.get('gq.servicing').create(cr, uid, vals)
			else:
				raise osv.except_osv(_('Wrong Service Code!'), _('Will be entered by contact person.\n Check the service code after servicing!'))
		return True
	def closed(self, cr, uid, ids, context=None):
		for service in self.read(cr, uid, ids, context=None):
			if service['verifier']==service['service_code']:
				date = datetime.now()
				date = date.strftime('%Y-%m-%d %H:%M:%S')
				self.write(cr, uid, service['id'], {'time_out':date,'verifier':False,'state':'closed'})
			else:
				raise osv.except_osv(_('Wrong Service Code!'), _('Will be entered by contact person.\n Check the service code after servicing!'))
		return True
gq_servicing()

class gq_servicing_item(osv.osv):
	
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		uom_pool = self.pool.get('product.uom')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			uomRead = uom_pool.read(cr, uid, line.uom.id,context=None)
			quantity = line.used
			price = line.price_unit * quantity
			res[line.id] = price
		return res
	
	def _line_price(self, cr, uid, ids, field_name, arg, context=None):
		uom_pool = self.pool.get('product.uom')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			uomRead = uom_pool.read(cr, uid, line.uom.id,context=None)
			prodRead = self.pool.get('product.product').read(cr, uid, line.product_id.id,context=None)
			quantity = prodRead['lst_price']
			if uomRead['uom_type']=='smaller':
				quantity = prodRead['lst_price'] * uomRead['factor']
			if uomRead['uom_type']=='bigger':
				quantity = prodRead['lst_price'] * uomRead['factor_inv']
			res[line.id] = quantity
		return res
	_name="gq.servicing.item"
	_description="Servicing Items"
	_columns = {
		'product_id':fields.many2one('product.product','Product', required=True),
		'quantity':fields.float('Quantity', required=True),
		'uom':fields.many2one('product.uom','Unit of Measure', required=True),
		'used':fields.float('Used Quantity'),
		'price_unit':fields.function(_line_price, string='Unit Price', digits_compute= dp.get_precision('Account')),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'available_qty':fields.float('Available Quantity'),
		'released_qty':fields.float('Released Quantity'),
		'state':fields.selection([
								('draft','Draft'),
								('confirmed','Confirmed'),
								('waiting_availability','Waiting Availability'),
								('available','Available'),
								('released','Released')
								],'State'),
		'service_id':fields.many2one('gq.servicing','MSR'),
		}
gq_servicing_item()

class gq_servicing_issue(osv.osv):
	_name = 'gq.servicing.issue'
	_description="Servicing Issues"
	_columns = {
		'name':fields.char('Subject', size=64),
		'description':fields.text('Description'),
		}
gq_servicing_issue()

class other_charges(osv.osv):
	_name = 'gq.charge'
	_description = 'Other Charges'
	_columns = {
		'name':fields.char('Description',size=64),
		'account_id':fields.many2one('account.account','Account'),
		'analytic_id':fields.many2one('account.analytic.account','Group'),
		'amount':fields.float('amount'),
		'service_id':fields.many2one('gq.servicing','Service Id', ondelete='cascade'),
		}
other_charges()
class gqs(osv.osv):
	_inherit = 'gq.servicing'
	_columns = {
		'item_ids':fields.one2many('gq.servicing.item','service_id','Items Needed'),
		'reported_ids': fields.many2many('gq.servicing.issue','gq_servicing_reported_issue_rel','gq_servicing_id','issue_id','Reported Issues'),
		'actual_ids': fields.many2many('gq.servicing.issue','gq_servicing_actual_issue_rel','gq_servicing_id','issue_id','Actual Issues'),
		'releasing_id':fields.many2one('stock.picking','Releasing'),
		'reservation_id':fields.many2one('stock.picking','Reservation'),
		'charge_ids':fields.one2many('gq.charge','service_id','Other Charges'),
		}
	def confirm(self, cr, uid, ids, context=None):
		for service in self.read(cr, uid, ids, context=None):
			if not service['reported_ids']:
				raise osv.except_osv(_('No Issue Reported!'), _('Please indicate an issue to be done/check!'))
			else:
				pw = ""
				for i in range(pw_length):
					nextIndex = random.randrange(len(alphabet))
					pw = pw+alphabet[nextIndex]
				self.write(cr, uid, service['id'],{'service_code':pw, 'state':'confirm'})
		return True

	def createPicking(self, cr, uid, ids, context=None):
		for gqs in self.read(cr, uid, ids, context=None):
			pick_type = self.pool.get('stock.picking.type').search(cr, uid, [('warehouse_id','=',gqs['warehouse_id'][0])
																			,('code','=','internal'),('name','=','Servicing Items')], limit=1)
			typeRead =self.pool.get('stock.picking.type').read(cr, uid, pick_type[0],context=None)
			vals = {
				'partner_id':gqs['partner_id'][0],
				'move_type':'direct',
				'origin':gqs['name'],
				'invoice_state':'none',
				'priority':'1',
				'picking_type_id':pick_type[0],
				'state':'draft',
				}
			picking_id = self.pool.get('stock.picking').create(cr, uid, vals)
			for item in gqs['item_ids']:
				itemRead = self.pool.get('gq.servicing.item').read(cr, uid, item, context=None)
				vals = {
					'product_id':itemRead['product_id'][0],
					'product_uom_qty':itemRead['quantity'],
					'product_uom': itemRead['uom'][0],
					'name':itemRead['product_id'][1],
					'product_uos_qty':itemRead['quantity'],
					'product_uos':itemRead['uom'][0],
					'invoice_state':'none',
					'priority':'1',
					'location_id':typeRead['default_location_src_id'][0],
					'location_dest_id':typeRead['default_location_dest_id'][0],
					'picking_id':picking_id,
					'state':'draft'
					}
				self.pool.get('stock.move').create(cr, uid, vals)
			self.write(cr, uid, gqs['id'],{'reservation_id':picking_id,'state':'in_progress'})
			self.pool.get('stock.picking').action_confirm(cr, uid, picking_id)
		return True
gqs()
