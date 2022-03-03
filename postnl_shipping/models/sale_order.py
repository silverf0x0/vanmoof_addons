# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from requests import request


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _action_confirm(self):
        """
        Overriding method in order to add logic to check customer address if delivery type is PostNL
        """
        if self.env.context.get('send_email'):
            self.force_quotation_send()

        # ********************** START NEW ************************** #
        if self.carrier_id.delivery_type == 'delivery_postnl' and self.prod_environment:
            self.check_address()
        # ************************ END NEW ************************** #
        # create an analytic account if at least an expense product
        for order in self:
            if any([expense_policy not in [False, 'no'] for expense_policy in
                    order.order_line.mapped('product_id.expense_policy')]):
                if not order.analytic_account_id:
                    order._create_analytic_account()
        return True

    def check_address(self):
        """
        This method is used to check the customer address before validation. This can only be used by business accounts
        """
        try:
            apikey = self.carrier_id.postnl_apikey
            url = "https://api.postnl.nl/address/national/v1/validate"
            headers = {"Content-Type": "application/json",
                       'APIKEY': apikey}
            # Collect json data to send to postNL api
            body = {
                "PostalCode": self.partner_id.zip,
                "City": self.partner_id.city,
                "Street": self.partner_id.street,
            }
            response_body = request(method='POST', url=url, headers=headers, data=body)
            print(response_body)
        except Exception as e:
            raise Warning(e)

    