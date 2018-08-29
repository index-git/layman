import json
import traceback

import requests
from urllib.parse import urljoin

from flask import g, current_app

from . import headers_json
from layman.settings import *


FLASK_WMS_PROXY_KEY = 'layman.geoserver.wms_proxy'


def update_layer(username, layername, layerinfo):
    g.pop(FLASK_WMS_PROXY_KEY, None)
    pass


def delete_layer(username, layername):
    try:
        r = requests.delete(
            urljoin(LAYMAN_GS_REST_WORKSPACES, username +
                    '/layers/' + layername),
            headers=headers_json,
            auth=LAYMAN_GS_AUTH,
            params = {
                'recurse': 'true'
            }
        )
        # app.logger.info(r.text)
        r.raise_for_status()
        g.pop(FLASK_WMS_PROXY_KEY, None)
    except Exception:
        traceback.print_exc()
        pass
    return {}


def get_wms_proxy(username):
    key = FLASK_WMS_PROXY_KEY
    if key not in g:
        wms_url = urljoin(LAYMAN_GS_URL, username + '/ows')
        from .util import wms_proxy
        wms_proxy = wms_proxy(wms_url)
        g.setdefault(key, wms_proxy)
    return g.get(key)

def get_layer_info(username, layername):

    try:
        wms = get_wms_proxy(username)
        wms_proxy_url = urljoin(LAYMAN_GS_PROXY_URL, username + '/ows')

        return {
            'title': wms.contents[layername].title,
            'description': wms.contents[layername].abstract,
            'wms': {
                'url': wms_proxy_url
            },
        }
    except:
        return {}


def get_layer_names(username):
    try:
        wms = get_wms_proxy(username)

        return [*wms.contents]
    except:
        return []