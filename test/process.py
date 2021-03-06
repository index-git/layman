from multiprocessing import Process
import subprocess
import os
import logging
import time

from test import util
from test.mock.liferay import run
import pytest

from layman import settings, util as layman_util


logger = logging.getLogger(__name__)

SUBPROCESSES = set()
LIFERAY_PORT = 8030

AUTHN_INTROSPECTION_URL = f"http://{settings.LAYMAN_SERVER_NAME.split(':')[0]}:{LIFERAY_PORT}/rest/test-oauth2/introspection?is_active=true"

LAYMAN_CELERY_QUEUE = 'temporary'

AUTHN_SETTINGS = {
    'LAYMAN_AUTHN_MODULES': 'layman.authn.oauth2',
    'OAUTH2_LIFERAY_INTROSPECTION_URL': AUTHN_INTROSPECTION_URL,
    'OAUTH2_LIFERAY_USER_PROFILE_URL': f"http://{settings.LAYMAN_SERVER_NAME.split(':')[0]}:{LIFERAY_PORT}/rest/test-oauth2/user-profile",
}

LAYMAN_SETTING = layman_util.SimpleStorage()
LAYMAN_DEFAULT_SETTINGS = AUTHN_SETTINGS
layman_start_counter = layman_util.SimpleCounter()


@pytest.fixture(scope="session")
def liferay_mock():
    server = Process(target=run, kwargs={
        'env_vars': {
        },
        'app_config': {
            'ENV': 'development',
            'SERVER_NAME': f"{settings.LAYMAN_SERVER_NAME.split(':')[0]}:{LIFERAY_PORT}",
            'SESSION_COOKIE_DOMAIN': f"{settings.LAYMAN_SERVER_NAME.split(':')[0]}:{LIFERAY_PORT}",
            'OAUTH2_USERS': {
                'test_gs_rules_user': None,
                'test_gs_rules_other_user': None,
                'testproxy': None,
                'testproxy2': None,
                'testmissingattr': None,
                'testmissingattr_authz': None,
                'testmissingattr_authz2': None,
                'test_authorize_decorator_user': None,
                'test_patch_gs_access_rights_user': None,
                'test_map_with_unauthorized_layer_user1': None,
                'test_map_with_unauthorized_layer_user2': None,
                'test_public_workspace_variable_user': None,
                'test_wms_ows_proxy_user': None,
                'test_get_publication_info_user': None,
                'test_get_publication_info_without_user': None,
                'test_delete_publications_owner': None,
                'test_delete_publications_deleter': None,
                'test_get_publication_infos_user_owner': None,
                'test_rest_soap_user': None,
                'test_geoserver_remove_users_for_public_workspaces_user': None,
                'test_get_users_workspaces_user': None,
                'test_check_user_wms' + settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX: None,
                'test_get_publications_workspace2': None,
                'test_select_publications_complex_workspace1': None,
                'test_select_publications_complex_workspace2': None,
            },
        },
        'host': '0.0.0.0',
        'port': LIFERAY_PORT,
        'debug': True,  # preserve error log in HTTP responses
        'load_dotenv': False,
        'options': {
            'use_reloader': False,
        },
    })
    server.start()
    util.wait_for_url(AUTHN_INTROSPECTION_URL, 20, 0.1)

    yield server

    server.terminate()
    server.join()


@pytest.fixture(scope='session', autouse=True)
def ensure_layman_session():
    print(f'\n\nEnsure_layman_session is starting\n\n')
    yield
    stop_process(list(SUBPROCESSES))
    print(f'\n\nEnsure_layman_session is ending - {layman_start_counter.get()}\n\n')


def ensure_layman_function(env_vars):
    if LAYMAN_SETTING.get() != env_vars:
        print(f'\nReally starting Layman LAYMAN_SETTING={LAYMAN_SETTING.get()}, settings={env_vars}')
        stop_process(list(SUBPROCESSES))
        start_layman(env_vars)
        LAYMAN_SETTING.set(env_vars)


# If you need fixture with different scope, create new fixture with such scope
@pytest.fixture(scope="class")
def ensure_layman():
    ensure_layman_function(LAYMAN_DEFAULT_SETTINGS)
    yield


@pytest.fixture(scope="module")
def ensure_layman_module():
    ensure_layman_function(LAYMAN_DEFAULT_SETTINGS)
    yield


def start_layman(env_vars=None):
    layman_start_counter.increase()
    print(f'\nstart_layman: Really starting Layman for the {layman_start_counter.get()}th time.')
    # first flush redis DB
    settings.LAYMAN_REDIS.flushdb()
    port = settings.LAYMAN_SERVER_NAME.split(':')[1]
    env_vars = env_vars or {}

    layman_env = os.environ.copy()
    layman_env.update(**env_vars)
    layman_env['LAYMAN_CELERY_QUEUE'] = LAYMAN_CELERY_QUEUE
    cmd = f'flask run --host=0.0.0.0 --port={port} --no-reload'
    layman_process = subprocess.Popen(cmd.split(), shell=False, stdin=None, env=layman_env)

    SUBPROCESSES.add(layman_process)
    rest_url = f"http://{settings.LAYMAN_SERVER_NAME}/rest/current-user"
    util.wait_for_url(rest_url, 200, 0.1)

    celery_env = layman_env.copy()
    celery_env['LAYMAN_SKIP_REDIS_LOADING'] = 'true'
    cmd = f'python3 -m celery -Q {LAYMAN_CELERY_QUEUE} -A layman.celery_app worker --loglevel=info --concurrency=4'
    celery_process = subprocess.Popen(cmd.split(), shell=False, stdin=None, env=layman_env, cwd='src')

    SUBPROCESSES.add(celery_process)

    return [layman_process, celery_process, ]


def stop_process(process):
    if not isinstance(process, list):
        process = {process, }
    for proc in process:
        proc.kill()
        SUBPROCESSES.remove(proc)
    time.sleep(1)
