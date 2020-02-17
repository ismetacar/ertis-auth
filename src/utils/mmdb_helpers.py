import os
import geoip2.database

current_dir = os.path.dirname(os.path.realpath(__file__))
mmdb_path = os.path.join(
    current_dir,
    '../',
    'utils/GeoIP2-City-20171206.mmdb'
)

reader = geoip2.database.Reader(mmdb_path)


def get_location_info(ip_address):
    response = reader.city(ip_address)
    return {
        'city': response.city.name,
        'country': response.country.name,
        'iso_code': response.country.iso_code
    }
