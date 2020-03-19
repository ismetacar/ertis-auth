from functools import wraps

#: from src.utils.mmdb_helpers import get_location_info


def resolve_ip():
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            #: ip_address = request.headers.get('x-ertis-ip')
            #: kwargs['ip_address'] = ip_address
            #: if ip_address:
            #:     try:
            #:         ip_info = get_location_info(ip_address)
            #:     except Exception:  #: handle unknown geoip error and set ip_info as {}
            #:         ip_info = {}

            #:     ip_info['ip_address'] = ip_address
            #:     kwargs['ip_info'] = ip_info

            response = await f(request, *args, **kwargs)
            return response
        return decorated_function
    return decorator
