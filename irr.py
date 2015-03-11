from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from docutils.nodes import field


class gq_irr(osv.osv):
	
	def _get_uid_partner(self, cr, uid, context=None):
		if context is None:
			context={}
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		partner_id = context.get('partner_id',user.partner_id.id)
		return partner_id

	_name = 'gq.irr'
	_description = "Item Releasing Requests"
	_columns = {
		'name':fields.char('Item Release Request', size=64, readonly=True),
		'date_request':fields.date('Request Date', required=True),
		'date_release':fields.date('Released Date', readonly=True),
		'partner_id':fields.many2one('res.partner', 'Client'),
		'warehouse_id':fields.many2one('stock.warehouse', 'Warehouse'),
		'type':fields.selection([
								('consumables','Consumables'),
								('freebies','Freebies'),
								('start_up','Start Up Inventory'),
								('caravan','Caravan'),
								('installation','Installation')
								],'Release Transaction Type'),
		'group':fields.many2one('account.analytic.account','Group'),
		'state':fields.selection([
								('draft','Draft'),
								('confirmed','Confirmed'),
								('approved','Approved'),
								('released','Released')
								],'State'),
		'notes':fields.text('Notes'),
		'pr_id':fields.many2one('gq.pr','PR Number'),
		'approving_officer':fields.many2one('res.users','Approving Officer', required=True),
		'other_pr':fields.char('Other PR Number', size=16),
		'check_ids':fields.many2many('gq.checkpayment','irr_check_rel','irr_id','check_id', 'Checks'),
	}
	_defaults = {
			'partner_id':_get_uid_partner,
			'name':'New IRR',
			'state':'draft',
			}
	def create(self, cr, uid, vals, context=None):
		name=self.pool.get('ir.sequence').get(cr, uid, 'gq.irr')
		vals.update({'name':name})
		return super(gq_irr, self).create(cr, uid, vals, context=context)
	
gq_irr()

class gq_irr_item(osv.osv):
	
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		uom_pool = self.pool.get('product.uom')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			uomRead = uom_pool.read(cr, uid, line.uom.id,context=None)
			quantity = line.quantity
			price = line.price_unit * quantity
			res[line.id] = price
		return res
	
	def _remaining(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			remaining = line.quantity
			if line.type=='caravan':
				for caravan in self.pool.get('gq.caravan').search(cr, uid, [('irr_id','=',line.irr_id.id)]):
					print caravan
					for caravan_item in self.pool.get('gq.caravanitems').search(cr, uid,[('caravan_id','=',caravan)
																						('product_id','=',line.product_id.id)
																						]):
						citemRead = self.pool.get('gq.caravanitems').read(cr, uid, caravan_item,context=None)
						print citemRead
						remaining-=citemRead['qty']
					res[line.id]=remaining
			else:
				res[line.id]=remaining
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
       
	_name = 'gq.irr.item'
	_description = 'Items to Release'
	_columns = {
		'product_id':fields.many2one('product.product','Product/Item', required=True),
		'quantity':fields.float('Quantity', required=True),
		'uom':fields.many2one('product.uom','Unit of Measure', required=True),
		'irr_id':fields.many2one('gq.irr','IRR Number', ondelete='cascade'),
		'caravanirr_id':fields.many2one('gq.irr','IRR Number', ondelete='cascade'),
		'installation_id':fields.many2one('gq.irr','IRR Number', ondelete='cascade'),
		'price_unit':fields.function(_line_price, string='Unit Price', digits_compute= dp.get_precision('Account')),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'remaining':fields.function(_remaining, string='Remaining Quantity', digits_compute= dp.get_precision('Account')),
		'type':fields.selection([
								('consumables','Consumables'),
								('freebies','Freebies'),
								('start_up','Start Up Inventory'),
								('caravan','Caravan'),
								('installation','Installation')
								],'Release Transaction Type'),
		'used_qty':fields.float('Consumed Quantity'),
		'remaining':fields.float('Remaining Quantity'),
		'state':fields.selection([
								('draft','Draft'),
								('confirmed','Confirmed'),
								('waiting_availability','Waiting Availability'),
								('available','Available'),
								('released','Released')
								],'State'),
		}
	_defaults = {
		'state':'draft',
		}
	
	def create(self, cr, uid, vals, context=None):
		irr_id = False
		print vals
		checker = False
		if 'irr_id' in vals:
			irrRead = self.pool.get('gq.irr').read(cr, uid, vals['irr_id'], ['type'])
			vals.update({'type':irrRead['type']})
			irr_id = vals['irr_id']
			checker = self.pool.get('gq.irr.item').search(cr, uid, [('product_id','=',vals['product_id']),('irr_id','=',irr_id)])
		elif 'caravanirr_id' in vals:
			irrRead = self.pool.get('gq.irr').read(cr, uid, vals['caravanirr_id'], ['type'])
			vals.update({'type':irrRead['type']})
			irr_id = vals['caravanirr_id']
			checker = self.pool.get('gq.irr.item').search(cr, uid, [('product_id','=',vals['product_id']),('caravanirr_id','=',irr_id)])
		print checker 
		if not checker :
			return super(gq_irr_item, self).create(cr, uid, vals, context=context)
		else:
			raise osv.except_osv(_('Error!'), _('Duplicate products in the list!\n Please verify request list.'))
	
gq_irr_item()

class gq_caravansales(osv.osv):
	_name = 'gq.caravan'
	_description = "Caravan Sales"
	_columns = {
			'name':fields.char('Sales Receipt',size=64, required=True),
			'partner_id':fields.many2one('res.partner','Partner'),
			'journal_id':fields.many2one('account.journal','Journal'),
			'date':fields.date('Receipt Date'),
			'irr_id':fields.many2one('gq.irr','Item Releasing'),
			'release_id':fields.many2one('stock.picking','Release Document'),
			'state':fields.selection([
								('draft','Draft'),
								('confirmed','Confirmed'),
								('audited','Audited')
								],'State'),
			}
	_defaults = {
			'state':'draft',
			}
	def confirm(self, cr, uid, ids, context=None):
		for caravan in self.read(cr, uid, ids, context=None):
			return True
		
gq_caravansales()

class caravan_items(osv.osv):
	
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		uom_pool = self.pool.get('product.uom')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			uomRead = uom_pool.read(cr, uid, line.uom.id,context=None)
			quantity = line.qty
			price = line.unit_price * quantity
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
	
	
	_name = 'gq.caravanitems'
	_description = "Caravan Item Sales"
	_columns = {
		'name':fields.char('Item Name', size=64),
		'product_id':fields.many2one('product.product','Product/Item'),
		'qty':fields.float('Quantity'),
		'uom':fields.many2one('product.uom','Unit of Measure'),
		'unit_price':fields.function(_line_price, string='Unit Price', digits_compute= dp.get_precision('Account')),
		'subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'caravan_id':fields.many2one('gq.caravan','Caravan', ondelete='cascade'),
		}
	
caravan_items()

class caravan(osv.osv):
	_inherit = 'gq.caravan'
	_columns = {
		'item_ids':fields.one2many('gq.caravanitems','caravan_id','Sold Items'),
		}
caravan()

class irr(osv.osv):
	
	_inherit = 'gq.irr'
	_columns = {
		'item_ids':fields.one2many('gq.irr.item','irr_id','Items to Release'),
		'caravanitem_ids':fields.one2many('gq.irr.item','caravanirr_id','Item Requested for Sale'),
		'installation_ids':fields.one2many('gq.irr.item','installation_id','Items for Installation'),
		'caravan_ids':fields.one2many('gq.caravan','irr_id','Sales Receipts'),
		'picking_type':fields.many2one('stock.picking.type','Group'),
		'release_id':fields.many2one('stock.picking','Release Document'),
	}
	
	def confirmOrder(self, cr, uid, ids, context=None):
		for order in self.read(cr, uid, ids, context=None):
		 	items = []
			if order['type']=='caravan':
				items = order['caravanitem_ids']
			elif order['type']=='installation':
				items = order['installation_ids']
			else:
				items = order['item_ids']
			if not items:
				raise osv.except_osv(_('No Item Request!'), _('Kindly list all items requested!'))
			elif items:
				for line in items:
					self.pool.get('gq.irr.item').write(cr, uid, line, {'state':'confirmed'})
			self.write(cr, uid, order['id'], {'state':'confirmed'})
		return True
	
	def approve(self, cr, uid, ids, context=None):
		for order in self.read(cr, uid, ids, context=None):
			typeRead =self.pool.get('stock.picking.type').read(cr, uid, order['picking_type'][0],context=None)
			vals = {
				'partner_id':order['partner_id'][0],
				'move_type':'direct',
				'origin':order['name'],
				'invoice_state':'none',
				'priority':'1',
				'picking_type_id':order['picking_type'][0],
				'state':'draft',
				}
			picking_id = self.pool.get('stock.picking').create(cr, uid, vals)
			items = []
			if order['type']=='caravan':
				items = order['caravanitem_ids']
			elif order['type']=='installation':
				items = order['installation_ids']
			elif order['type'] not in ['installation','caravan']:
				items = order['item_ids']
			for item in items:
				itemRead = self.pool.get('gq.irr.item').read(cr, uid, item, context=None)
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
			self.write(cr, uid, order['id'],{'release_id':picking_id,'state':'approved'})
			#self.pool.get('stock.picking').action_confirm(cr, uid, picking_id)
		return True
	def release(self, cr, uid, ids, context=None):
		for irr in self.read(cr, uid, ids, context=None):
			self.write(cr, uid, irr['id'], {'state':'released'})
		return True
irr()
  

class picking(osv.osv):
	_inherit = 'stock.picking'
	_columns = {
		'irr_id':fields.many2one('gq.irr','Item Releasing'),
		}
picking()