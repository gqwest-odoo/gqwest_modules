from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp


class gq_storeinspection(osv.osv):
	_name = "gq.storeinspection"
	_description = "Store Inspection"
	_columns = {
		'name':fields.char('Inspection Number', size=64),
		'inspection_date':fields.date('Inspection Date'),
		'partner_id':fields.many2one('res.partner','Partner Name/Station ID'),
		'spa_opa':fields.integer('Signage'),
		'spa_opb':fields.integer('Front Panel / Front View'),
		'spa_ipc':fields.integer('Filling/ Washing Area/ AirCon'),
		'spa_ipd':fields.integer('Flooring/ Wall/ Ceiling'),
		'spa_rem':fields.text('REMARKS;'),
		'map_a':fields.integer('Pre-Treatment'),
		'map_b':fields.integer('Main Purification'),
		'map_c':fields.integer('Post-Treatment'),
		'map_d':fields.integer('Alkaline/ Mineral'),
		'map_mp':fields.float('Multimedia Pressure'),
		'map_sp':fields.float('Softener Pressure'),
		'map_cp':fields.float('Carbon Pressure'),
		'map_pi':fields.float('Pressure Inlet'),
		'map_po':fields.float('Pressure Outlet'),
		'map_fp':fields.float('Flowrate Permeate'),
		'map_fc':fields.float('Flowrate Concentrate'),
		'wq_tds':fields.integer('TDS of Product Water (above 015pm no score)'),
		'wq_wtr':fields.integer('Water Test Result'),
		'wq_ptr':fields.float('Products TDS Reading'),
        'wq_phr':fields.float('PH Reading'),
        'wq_wtl':fields.char('Water Testing Laboratory',size=32),
        'wq_str':fields.float('Source TDS Reading'),
		'wq_wtre':fields.float('Waste TDS Reading'),
		
		}
	_defaults = {
		'name':'INSNUM',
		'inspection_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		}
gq_storeinspection()
