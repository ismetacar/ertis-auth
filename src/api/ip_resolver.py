from sanic.response import json

from src.plugins.resolve_ip import resolve_ip
from src.utils.country_info import all_countries


def init_ip_resolver_api(app, settings):
    @app.route('/api/v1/ip-resolver', methods=['GET'])
    @resolve_ip()
    async def ip_resolver(request, **kwargs):
        ip_info = kwargs.get('ip_info', {})
        if not ip_info.get('iso_code', None):
            return json(kwargs.get('ip_info', {}))

        for country in all_countries:
            if country['iso3166_1_alpha_2'] != ip_info['iso_code']:
                continue
            ip_info['alpha_3_code'] = country['iso3166_1_alpha_3']

        return json(kwargs.get('ip_info', {}))
