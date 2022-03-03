# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from requests import request
import requests
import base64


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Postnl general shipment fiels
    postnl_barcode = fields.Char(string="Postnl barcode", readonly=True,
                                 help="Barcode of the shipment. This is a unique value.")
    postnl_code = fields.Char(string="Postnl code", readonly=True,
                              help="If there is an error during the shipping request, here will be save the error code")
    postnl_description = fields.Text(string="Postnl description", readonly=True,
                                     help="If there is an error during the shipping request, "
                                          "here will be save the description of the error")

    # Postnl status fields
    postnl_shipping_status = fields.Char(string="Postnl shipping status", readonly=True,
                                         help="The status of the shipment is being updated here")
    postnl_shipping_code = fields.Char(string="Postnl shipping code", readonly=True,
                                       help="It reports the error code for the shipment status")
    postnl_shipping_message = fields.Text(string="Postnl shipping message", readonly=True,
                                         help="Description of the shipping error")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method in order to send shipping via postnl, if postnl carried is being used
        """
        res = super(StockPicking, self).create(vals_list)
        if res.carrier_id.delivery_type == 'delivery_postnl':
            results = self.delivery_postnl_send_shipping(res)
            res.postnl_barcode = results['barcode']
            res.postnl_code = results['code']
            res.postnl_description = results['description']
        return res

    @api.model
    def delivery_postnl_send_shipping(self, picking):
        """
        This is the main function responsible to call the shipping endpoint of postnl API. The aim of the methods
        is to send shipment information to postnl provider and get back the pdf label, along with the barcode and the
        description.
        """
        import pdb; pdb.set_trace()
        postnl_code = False
        barcode = False
        description = False
        try:
            apikey = picking.carrier_id.postnl_apikey
            if picking.carrier_id.prod_environment:
                url = 'https://api.postnl.nl/shipment/?confirm=true'
            else:
                url = 'https://api-sandbox.postnl.nl/v1/shipment?confirm=true'
            headers = {'APIKEY': apikey}
            body = {
                "Customer": {
                    "Address": {
                        "AddressType": "02",
                        "City": picking.carrier_id.company_id.city,
                        "CompanyName": picking.carrier_id.company_id.name,
                        "Countrycode": picking.carrier_id.company_id.country_id.code,
                        "StreetHouseNrExt": picking.carrier_id.company_id.street,
                        "Zipcode": picking.carrier_id.company_id.zip,
                    },
                    "CollectionLocation": picking.carrier_id.collection_location,
                    "ContactPerson": picking.carrier_id.contact_person.name if picking.carrier_id.contact_person else False,
                    "CustomerCode": "DEVC",
                    "CustomerNumber": "11223344",
                    "Email": picking.carrier_id.contact_person.email if picking.carrier_id.contact_person else False,
                    "Name": picking.carrier_id.contact_person.name if picking.carrier_id.contact_person else False,
                },
                "Message": {
                    "MessageID": "1",
                    "MessageTimeStamp": picking.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "Printertype": "GraphicFile|PDF"
                },
                "Shipments": {
                    "Addresses": [
                        {
                            "AddressType": "01",
                            "City": picking.partner_id.city,
                            "Countrycode": picking.partner_id.country_id.code,
                            "FirstName": picking.partner_id.firstname,
                            "Name": picking.partner_id.lastname,
                            "StreetHouseNrExt": picking.partner_id.street,
                            "Zipcode": picking.partner_id.zip,
                        }
                    ],
                    "Contacts": [
                        {
                            "ContactType": "01",
                            "Email": picking.partner_id.email,
                            "SMSNr": picking.partner_id.mobile,
                            "TelNr": picking.partner_id.phone,
                        }
                    ],
                    "DeliveryAddress": "01",
                    "Dimension": {
                        "Weight": picking.weight,
                    },
                    "ProductCodeDelivery": picking.carrier_id.postnl_product,
                }
            }
            response_body = requests.post(url=url, headers=headers, json=body)
            if response_body.status_code == 200:
                # Collect information on postNL shipment
                barcode = response_body.json()['ResponseShipments'][0]['Barcode']
                if 'Code' in response_body.json()['ResponseShipments'][0]['Warnings']:
                    postnl_code = response_body.json()['ResponseShipments'][0]['Warnings'][0]['Code']
                    description = response_body.json()['ResponseShipments'][0]['Warnings'][0]['Description']

                # Add pdf label to the new picking
                pdf = response_body.json()['ResponseShipments'][0]['Labels'][0]['Content']
                attachment = self.env['ir.attachment'].create({
                    'name': 'delivery_{}'.format(barcode),
                    'type': 'binary',
                    'datas': pdf,
                    'datas_fname': 'delivery_{}.pdf'.format(barcode),
                    'store_fname': 'delivery_{}'.format(barcode),
                    'res_model': picking._name,
                    'res_id': picking.id,
                    'mimetype': 'application/x-pdf'
                })
        except Exception as e:
            raise Warning(e)
        return {'barcode': barcode, 'description': description, 'code': postnl_code}

    def action_tracking_shipment(self):
        """
        This is called manually by a button on the form view, but in an advanced version it should be triggered by
        a cron as well
        """
        try:
            apikey = self.carrier_id.postnl_apikey
            if self.carrier_id.prod_environment:
                url = 'https://api.postnl.nl/shipment/v2/status/barcode/{}'.format(self.postnl_barcode)
            else:
                url = 'https://api-sandbox.postnl.nl/shipment/v2/status/barcode/{}'.format(self.postnl_barcode)
            headers = {'APIKEY': apikey}
            response_body = requests.get(url=url, headers=headers)
            if response_body.status_code == 200:
                self.postnl_shipping_status = response_body.json()['CurrentStatus']
                if 'Code' in response_body.json()['Warnings'][0]:
                    self.postnl_shipping_code = response_body.json()['Warnings'][0]['Code']
                    self.postnl_shipping_message = response_body.json()['Warnings'][0]['Message']
            print(response_body)
        except Exception as e:
            raise Warning(e)
