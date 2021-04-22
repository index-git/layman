import os
import time

import pytest

from layman import app, settings, celery as celery_util
from layman.layer import util as util_layer
from layman.map import util as util_map
from layman.util import url_for


def publish_layer(workspace,
                  layername,
                  client,
                  title=None,
                  file_paths=None,
                  ):
    title = title or layername
    file_paths = file_paths or ['tmp/naturalearth/110m/cultural/ne_110m_populated_places.geojson', ]
    with app.app_context():
        rest_path = url_for('rest_workspace_layers.post', username=workspace)

        for fp in file_paths:
            assert os.path.isfile(fp)
        files = []

        try:
            files = [(open(fp, 'rb'), os.path.basename(fp)) for fp in file_paths]
            rv = client.post(rest_path, data={
                'file': files,
                'name': layername,
                'title': title,
            })
            assert rv.status_code == 200, (rv.status_code, rv.get_json())
        finally:
            for fp in files:
                fp[0].close()

    wait_till_layer_ready(workspace, layername)
    return rv.get_json()[0]


@pytest.fixture()
def client():
    client = app.test_client()

    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    app.config['SERVER_NAME'] = settings.LAYMAN_SERVER_NAME
    app.config['SESSION_COOKIE_DOMAIN'] = settings.LAYMAN_SERVER_NAME

    yield client


def delete_layer(workspace, layername, client, headers=None):
    headers = headers or {}
    with app.app_context():
        r_url = url_for('rest_workspace_layers.delete', username=workspace, layername=layername)
        r = client.delete(r_url, headers=headers)
    assert r.status_code == 200, (r.status_code, r.get_json())


def delete_map(workspace, mapname, client, headers=None):
    headers = headers or {}
    with app.app_context():
        r_url = url_for('rest_workspace_maps.delete', username=workspace, mapname=mapname)
        r = client.delete(r_url, headers=headers)
    assert r.status_code == 200, (r.status_code, r.get_json())


def publish_map(workspace,
                mapname,
                client,
                maptitle=None,
                headers=None,
                ):
    maptitle = maptitle or mapname
    headers = headers or {}
    with app.app_context():
        rest_path = url_for('rest_workspace_maps.post', username=workspace)

        file_paths = [
            'sample/layman.map/full.json',
        ]

        for fp in file_paths:
            assert os.path.isfile(fp)
        files = []

        try:
            files = [(open(fp, 'rb'), os.path.basename(fp)) for fp in file_paths]
            rv = client.post(rest_path,
                             data={'file': files,
                                   'name': mapname,
                                   'title': maptitle,
                                   },
                             headers=headers)
            assert rv.status_code == 200, (rv.status_code, rv.get_json())
        finally:
            for fp in files:
                fp[0].close()

    wait_till_map_ready(workspace, mapname)


def wait_till_map_ready(workspace, name):
    last_task = util_map._get_map_task(workspace, name)
    while last_task is not None and not celery_util.is_task_ready(last_task):
        time.sleep(0.1)
        last_task = util_map._get_map_task(workspace, name)


def wait_till_layer_ready(workspace, layername):
    last_task = util_layer._get_layer_task(workspace, layername)
    while last_task is not None and not celery_util.is_task_ready(last_task):
        time.sleep(0.1)
        last_task = util_layer._get_layer_task(workspace, layername)


def ensure_workspace(workspace, client):
    with app.app_context():
        r = client.get(url_for('rest_workspace_layers.post', username=workspace))
    if r.status_code == 404 and r.get_json()['code'] == 40:
        tmp_layername = 'tmp_layername'
        publish_layer(workspace, tmp_layername, client)
        delete_layer(workspace, tmp_layername, client)
    elif r.status_code != 200:
        raise Exception(r.data)
