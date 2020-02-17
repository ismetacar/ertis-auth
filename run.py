import optparse
from pprint import pprint

from configs.develop import develop_config
from configs.local import local_config
from configs.test import test_config
from src import create_sanic_app

CONFIG_LOOKUP = {
    'local': local_config,
    'test': test_config,
    'develop': develop_config
}

parser = optparse.OptionParser()
parser.add_option("--config", default="develop")


def config_settings(config_name=None):
    if config_name:
        return CONFIG_LOOKUP[config_name]
    options, _ = parser.parse_args()
    return CONFIG_LOOKUP[options.config]


settings = config_settings()
pprint(settings)

app = create_sanic_app(settings)
app.debug = settings['debug']
app.secret_key = settings['application_secret']
app.host = settings['host']
app.port = settings['port']
app.env = settings['environment']

if __name__ == '__main__':
    app.run(host=app.host, port=app.port)
