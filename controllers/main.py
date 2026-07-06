import jwt
import datetime
from odoo import http, tools
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

def get_secret_key():
    # Retrieve secret key from odoo.conf, fallback to a default if not found
    return tools.config.get('jwt_secret_key', 'fallback-secure-secret-key-12345')

def validate_token(token):
    try:
        secret = get_secret_key()
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Check blacklist
        blacklisted = request.env['api.token.blacklist'].sudo().search([('token', '=', token)], limit=1)
        if blacklisted:
            return {'error': 'Token invalidated'}
            
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expired'}
    except Exception as e:
        _logger.warning("JWT Validation error: %s", str(e))
        return {'error': 'Invalid token'}

class ApiAuthToken(http.Controller):

    @http.route('/api/login', type='json', auth="public", methods=['POST'], csrf=False)
    def api_login(self, **kwargs):
        username = kwargs.get('username')
        password = kwargs.get('password')
        if not username or not password:
            return {'error': 'Missing credentials'}
            
        try:
            credential = {'type': 'password', 'login': username, 'password': password}
            db = request.db or (request.env.registry.db_name if hasattr(request.env, 'registry') else None)
            if not db:
                raise Exception("Database not found")
            auth_info = request.session.authenticate(db, credential)
            uid = auth_info.get('uid')
            user = request.env['res.users'].sudo().browse(uid)
        except Exception as e:
            _logger.error("Login Error: %s", str(e))
            return {'error': 'Invalid credentials', 'details': str(e)}
            
        if user:
            payload = {
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            token = jwt.encode(payload, get_secret_key(), algorithm='HS256')
            return {'token': token}
        return {'error': 'Invalid credentials'}

    @http.route('/api/register', type='json', auth="public", methods=['POST'], csrf=False)
    def api_register(self, **kwargs):
        name = kwargs.get('name')
        email = kwargs.get('email')
        password = kwargs.get('password')
        
        if not name or not email or not password:
            return {'error': 'Missing required fields: name, email, password'}
            
        try:
            # Check if user already exists
            existing_user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if existing_user:
                return {'error': 'Email is already registered'}
                
            # Create user (give portal access by default)
            portal_group = request.env.ref('base.group_portal', raise_if_not_found=False)
            groups_id = [(6, 0, [portal_group.id])] if portal_group else []
            
            user = request.env['res.users'].sudo().create({
                'name': name,
                'login': email,
                'password': password,
                'groups_id': groups_id
            })
            
            # Generate JWT token for auto-login
            payload = {
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            token = jwt.encode(payload, get_secret_key(), algorithm='HS256')
            
            return {
                'success': True,
                'message': 'User registered successfully',
                'token': token,
                'user_id': user.id
            }
        except Exception as e:
            _logger.error("Registration Error: %s", str(e))
            return {'error': 'Registration failed', 'details': str(e)}

    @http.route('/api/user/profile', type='json', auth="public", methods=['GET', 'POST'], csrf=False)
    def user_profile(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        user = request.env['res.users'].sudo().browse(payload['user_id'])
        if not user.exists():
            return {'error': 'User not found'}
            
        base_url = request.httprequest.url_root.rstrip('/')
            
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone or '',
            'profile_image': f"{base_url}/web/image/res.partner/{user.partner_id.id}/image_1920" if user.image_1920 else None
        }

    @http.route('/api/user/profile/image', type='json', auth="public", methods=['POST'], csrf=False)
    def update_profile_image(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        user = request.env['res.users'].sudo().browse(payload['user_id'])
        if not user.exists():
            return {'error': 'User not found'}
            
        image_base64 = kwargs.get('image')
        if not image_base64:
            return {'error': 'Missing image data. Expected a base64 string in the "image" key.'}
            
        try:
            # In Odoo, base64 data for binary fields can sometimes contain the "data:image/jpeg;base64," prefix.
            # Odoo's binary fields usually handle standard base64 strings directly. 
            # If the frontend sends the prefix, we can optionally strip it, but standard practice 
            # is to send just the base64 string itself.
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
                
            user.write({'image_1920': image_base64})
            
            # Ensure the attachment is publicly accessible so the mobile app can read it
            attachment = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', user.partner_id.id),
                ('res_field', '=', 'image_1920')
            ], limit=1)
            if attachment:
                attachment.sudo().write({'public': True})
                
            base_url = request.httprequest.url_root.rstrip('/')
            return {
                'success': True,
                'message': 'Profile image updated successfully',
                'profile_image': f"{base_url}/web/image/res.partner/{user.partner_id.id}/image_1920"
            }
        except Exception as e:
            _logger.error("Profile Image Update Error: %s", str(e))
            return {'error': 'Failed to update profile image', 'details': str(e)}

    @http.route('/api/user/bookings', type='json', auth="public", methods=['GET', 'POST'], csrf=False)
    def user_bookings(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        user = request.env['res.users'].sudo().browse(payload['user_id'])
        bookings = request.env['tour.booking'].sudo().search([('partner_id', '=', user.partner_id.id)])
        
        return [{
            'id': b.id,
            'name': b.name,
            'state': b.state,
            'start_date': str(b.calendar_id.date_start) if b.calendar_id and b.calendar_id.date_start else None,
            'end_date': str(b.calendar_id.date_end) if b.calendar_id and b.calendar_id.date_end else None
        } for b in bookings]

    @http.route('/api/user/calendar', type='json', auth="public", methods=['GET', 'POST'], csrf=False)
    def user_calendar(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        user = request.env['res.users'].sudo().browse(payload['user_id'])
        bookings = request.env['tour.booking'].sudo().search([
            ('partner_id', '=', user.partner_id.id),
            ('state', '=', 'confirmed')  # Usually calendar only shows confirmed bookings
        ])
        
        return [{
            'title': b.name,
            'start': str(b.calendar_id.date_start) if b.calendar_id and b.calendar_id.date_start else None,
            'end': str(b.calendar_id.date_end) if b.calendar_id and b.calendar_id.date_end else None
        } for b in bookings if b.calendar_id]

    @http.route('/api/refresh', type='json', auth="public", methods=['POST'], csrf=False)
    def refresh_token(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        new_payload = {
            'user_id': payload['user_id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        new_token = jwt.encode(new_payload, get_secret_key(), algorithm='HS256')
        return {'token': new_token}

    @http.route('/api/user/logout', type='json', auth="public", methods=['POST'], csrf=False)
    def api_logout(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        # Log out the Odoo session
        request.session.logout()
        
        # Note: JWTs are stateless, so true invalidation requires a token blacklist database.
        # We are now adding the token to the blacklist model!
        request.env['api.token.blacklist'].sudo().create({'token': token})
        
        # This endpoint logs out the Odoo session and confirms the client should delete the token on their end.
        return {'success': True, 'message': 'Logged out successfully. Token has been invalidated.'}

    @http.route('/api/packages', type='json', auth="public", methods=['GET', 'POST'], csrf=False)
    def api_get_packages(self, **kwargs):
        packages = request.env['tour.package'].sudo().search([('active', '=', True)])
        base_url = request.httprequest.host_url.rstrip('/')
        return [{
            'id': p.id,
            'name': p.name,
            'category': p.category_id.name if p.category_id else None,
            'price': p.price,
            'duration': p.duration,
            'availability_status': p.availability_status,
            'cover_image': f"{base_url}/web/image/tour.package/{p.id}/cover_image?unique={int(p.write_date.timestamp()) if p.write_date else 0}" if p.cover_image else f"{base_url}/tour_package/static/images/default_cover.png",
        } for p in packages]

    @http.route('/api/package/book', type='json', auth="public", methods=['POST'], csrf=False)
    def api_book_package(self, **kwargs):
        token_header = request.httprequest.headers.get('Authorization')
        if not token_header or not token_header.startswith('Bearer '):
            return {'error': 'Missing or invalid token'}
            
        token = token_header.split(' ')[1]
        payload = validate_token(token)
        if 'error' in payload:
            return payload
            
        user = request.env['res.users'].sudo().browse(payload['user_id'])
        if not user.exists():
            return {'error': 'User not found'}
            
        calendar_id = kwargs.get('calendar_id')
        seats = int(kwargs.get('seats', 1))
        
        if not calendar_id:
            return {'error': 'Missing calendar_id'}
            
        calendar = request.env['tour.calendar'].sudo().browse(int(calendar_id))
        if not calendar.exists() or calendar.state != 'open':
            return {'error': 'Tour date not found or closed'}
            
        if calendar.remaining_seats < seats:
            return {'error': 'Not enough seats available'}
            
        try:
            booking = request.env['tour.booking'].sudo().create({
                'calendar_id': calendar.id,
                'partner_id': user.partner_id.id,
                'user_id': user.id,
                'seats': seats,
            })
            return {
                'success': True,
                'booking_id': booking.id,
                'message': 'Booking created successfully'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/package/detail', type='json', auth="public", methods=['POST'], csrf=False)
    def api_package_detail(self, **kwargs):
        package_id = kwargs.get('package_id')
        if not package_id:
            return {'error': 'Missing package_id'}
            
        package = request.env['tour.package'].sudo().browse(int(package_id))
        if not package.exists():
            return {'error': 'Package not found'}
            
        calendars = []
        for cal in package.calendar_ids:
            calendars.append({
                'id': cal.id,
                'date_start': str(cal.date_start) if cal.date_start else None,
                'date_end': str(cal.date_end) if cal.date_end else None,
                'state': cal.state,
                'remaining_seats': cal.remaining_seats
            })

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        gallery = [f"{base_url}/web/image/{img.id}?unique={img.checksum}" for img in package.image_ids] if package.image_ids else []

        return {
            'id': package.id,
            'name': package.name,
            'category': package.category_id.name if package.category_id else None,
            'description': package.description,
            'price': package.price,
            'duration': package.duration,
            'availability_status': package.availability_status,
            'cover_image': f"{base_url}/web/image/tour.package/{package.id}/cover_image?unique={int(package.write_date.timestamp()) if package.write_date else 0}" if package.cover_image else f"{base_url}/tour_package/static/images/default_cover.png",
            'video_url': package.video_url,
            'gallery': gallery,
            'calendars': calendars
        }
