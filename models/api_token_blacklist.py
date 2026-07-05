from odoo import models, fields

class ApiTokenBlacklist(models.Model):
    _name = 'api.token.blacklist'
    _description = 'JWT Token Blacklist'

    token = fields.Char(string='Token', required=True, index=True)
