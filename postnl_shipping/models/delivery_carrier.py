# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # Adding field that will be used for postnl configuration and management
    delivery_type = fields.Selection(selection_add=[('delivery_postnl', 'PostNL')])
    delivery_type_postnl = fields.Selection(
        [('fixed', 'PostNL Fixed Price'), ('base_on_rule', 'PostNL Based on Rules')], string='PostNL Pricing',
        default='fixed')
    postnl_product = fields.Selection(
        [('3085', '3085-Standard shipment'),
         ('3385', '3385-Deliver to stated address only'),
         ('3090', '3090-Delivery to neighbour'),
         # Destination EU
         ('4940', '4940-EU Pack Special to business')],
        string="Product Code Delivery", default='3085', help="Product code of the shipment. Form ")
    postnl_customer_code = fields.Char("Customer Code", copy=False,
                                       help="Customer code as known at PostNL Pakketten  Example:'ABCD'")
    postnl_customer_number = fields.Char("Customer Number", copy=False,
                                         help="Customer number as known at PostNL Pakketten. Example:'11223344' ")
    postnl_apikey = fields.Char("APIKEY", help="APIKEY Provided by postnl")

    collection_location = fields.Char(string="Collection Location",
                                      help="Code of delivery location at PostNL Pakketten")
    contact_person = fields.Many2one('res.partner', string="Contact Person", help="Name of customer contact person")
    customer_code = fields.Char("Customer Code", copy=False,
                                       help="Customer code as known at PostNL Pakketten")
    customer_number = fields.Char("Customer Number", copy=False,
                                         help="Customer number as known at PostNL Pakketten")

    _sql_constraints = [('user_unique', 'unique(customer_number)', 'User already exists.')]

