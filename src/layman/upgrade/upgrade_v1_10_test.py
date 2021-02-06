import pytest
import shutil

from . import upgrade_v1_10
from layman import app, settings
from layman.http import LaymanError
from layman.common import prime_db_schema
from layman.layer.prime_db_schema import table as prime_db_schema_table
from layman.layer import geoserver as gs_layer
from layman.layer.geoserver import wms
from layman.common import geoserver as gs_common
from layman.layer import db
from layman.uuid import generate_uuid
from layman.map.filesystem import input_file, thumbnail
from test import process_client, util


@pytest.mark.usefixtures('ensure_layman')
def test_check_usernames_for_wms_suffix():
    username = 'test_check_usernames_for_wms_suffix'
    username_wms = 'test_check_usernames_for_wms_suffix' + settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX

    with app.app_context():
        prime_db_schema.ensure_workspace(username)
        upgrade_v1_10.check_usernames_for_wms_suffix()

        prime_db_schema.ensure_workspace(username_wms)
        with pytest.raises(LaymanError) as exc_info:
            upgrade_v1_10.check_usernames_for_wms_suffix()
        assert exc_info.value.data['workspace'] == username_wms


@pytest.fixture()
def ensure_layer():
    def ensure_layer_internal(workspace, layer):
        with app.app_context():
            uuid_str = generate_uuid()
            prime_db_schema_table.post_layer(workspace,
                                             layer,
                                             {'read': [settings.RIGHTS_EVERYONE_ROLE], 'write': [settings.RIGHTS_EVERYONE_ROLE], },
                                             layer,
                                             uuid_str,
                                             None)
            file_path = '/code/tmp/naturalearth/110m/cultural/ne_110m_admin_0_countries.geojson'
            db.ensure_workspace(workspace)
            db.import_layer_vector_file(workspace, layer, file_path, None)

            created = gs_common.ensure_workspace(workspace, settings.LAYMAN_GS_AUTH)
            if created:
                gs_common.create_db_store(workspace, settings.LAYMAN_GS_AUTH, db_schema=workspace)
            gs_layer.publish_layer_from_db(workspace, layer, layer, layer, None, workspace)

            sld_file_path = 'sample/style/generic-blue.xml'
            with open(sld_file_path, 'rb') as sld_file:
                gs_common.post_workspace_sld_style(workspace, layer, sld_file)

    yield ensure_layer_internal


@pytest.mark.usefixtures('ensure_layman')
def test_migrate_layers_to_wms_workspace(ensure_layer):
    workspace = 'test_migrate_layers_to_wms_workspace_workspace'
    layer = 'test_migrate_layers_to_wms_workspace_layer'
    expected_file = 'sample/style/countries_wms_blue.png'
    ensure_layer(workspace, layer)

    layer_info = process_client.get_layer(workspace, layer)

    assert layer_info['wms']['status'] == 'NOT_AVAILABLE'
    assert layer_info['wfs']['url'] == f'http://localhost:8000/geoserver/{workspace}/wfs'
    assert layer_info['db_table'] == layer

    all_workspaces = gs_common.get_all_workspaces(settings.LAYMAN_GS_AUTH)
    assert workspace in all_workspaces
    wms_workspace = wms.get_geoserver_workspace(workspace)
    assert wms_workspace not in all_workspaces
    sld_wfs_r = gs_common.get_workspace_style_response(workspace, layer, auth=settings.LAYMAN_GS_AUTH)
    assert sld_wfs_r.status_code == 200

    old_wms_url = f"http://{settings.LAYMAN_SERVER_NAME}/geoserver/" \
                  f"{workspace}/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&STYLES=&" \
                  f"LAYERS={workspace}:{layer}&SRS=EPSG:3857&WIDTH=768&HEIGHT=752&" \
                  f"BBOX=-30022616.05686392,-30569903.32873383,30022616.05686392,28224386.44929134"

    obtained_file = 'tmp/artifacts/test_migrate_layers_to_wms_workspace_before_migration.png'
    util.assert_same_images(old_wms_url, obtained_file, expected_file, 2000)

    with app.app_context():
        upgrade_v1_10.migrate_layers_to_wms_workspace(workspace)

    layer_info = process_client.get_layer(workspace, layer)
    assert layer_info['wms']['url'] == f'http://localhost:8000/geoserver/{wms_workspace}/ows'
    assert layer_info['wfs']['url'] == f'http://localhost:8000/geoserver/{workspace}/wfs'
    assert layer_info['sld']['url'] == f'http://layman_test_run_1:8000/rest/{workspace}/layers/{layer}/style'

    all_workspaces = gs_common.get_all_workspaces(settings.LAYMAN_GS_AUTH)
    assert workspace in all_workspaces
    assert wms_workspace in all_workspaces
    sld_wfs_r = gs_common.get_workspace_style_response(workspace, layer, auth=settings.LAYMAN_GS_AUTH)
    assert sld_wfs_r.status_code == 404
    sld_wms_r = gs_common.get_workspace_style_response(wms_workspace, layer, auth=settings.LAYMAN_GS_AUTH)
    assert sld_wms_r.status_code == 200

    sld_stream = process_client.get_layer_style(workspace, layer)
    assert sld_stream

    new_wms_url = f"http://{settings.LAYMAN_SERVER_NAME}/geoserver/" \
                  f"{wms_workspace}/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&STYLES=&" \
                  f"LAYERS={wms_workspace}:{layer}&SRS=EPSG:3857&WIDTH=768&HEIGHT=752&" \
                  f"BBOX=-30022616.05686392,-30569903.32873383,30022616.05686392,28224386.44929134"
    obtained_file2 = 'tmp/artifacts/test_migrate_layers_to_wms_workspace_after_migration.png'
    util.assert_same_images(new_wms_url, obtained_file2, expected_file, 2000)

    process_client.delete_layer(workspace, layer)


@pytest.fixture()
def ensure_map():

    def ensure_map_internal(workspace, map, layer_workspace, layer):
        geojson_files = ['/code/tmp/naturalearth/110m/cultural/ne_110m_admin_0_countries.geojson']
        style_file = 'sample/style/generic-blue.xml'
        source_map_file_path = '/code/src/layman/upgrade/upgrade_v1_10_test_map.json'
        process_client.publish_layer(layer_workspace,
                                     layer,
                                     file_paths=geojson_files,
                                     style_file=style_file)
        process_client.publish_map(workspace,
                                   map,
                                   )

        with app.app_context():
            input_file.ensure_map_input_file_dir(workspace, map)
            map_file_path = input_file.get_map_file(workspace, map)
            shutil.copyfile(source_map_file_path, map_file_path)
            thumbnail.generate_map_thumbnail(workspace, map, '')

    yield ensure_map_internal


@pytest.mark.usefixtures('ensure_layman')
def test_migrate_maps_on_wms_workspace(ensure_map):
    layer_workspace = 'test_migrate_maps_on_wms_workspace_layer_workspace'
    layer = 'test_migrate_maps_on_wms_workspace_layer'
    workspace = 'test_migrate_maps_on_wms_workspace_workspace'
    map = 'test_migrate_maps_on_wms_workspace_map'
    expected_file = 'sample/style/test_sld_style_applied_in_map_thumbnail_map.png'

    ensure_map(workspace, map, layer_workspace, layer)

    with app.app_context():
        map_json = input_file.get_map_json(workspace, map)
        assert map_json['layers'][0]['url'] == 'http://localhost:8000/geoserver/test_migrate_maps_on_wms_workspace_layer_workspace/ows',\
            map_json
        thumbnail_path = thumbnail.get_map_thumbnail_path(workspace, map)
    diffs_before = util.compare_images(expected_file, thumbnail_path)
    shutil.copyfile(thumbnail_path, '/code/tmp/artifacts/upgrade_v1_10_map_thumbnail_before.png')
    assert 28000 < diffs_before < 35000

    with app.app_context():
        upgrade_v1_10.migrate_maps_on_wms_workspace()

    with app.app_context():
        map_json = input_file.get_map_json(workspace, map)
        assert map_json['layers'][0][
            'url'] == 'http://localhost:8000/geoserver/test_migrate_maps_on_wms_workspace_layer_workspace_wms/ows', map_json
        thumbnail.generate_map_thumbnail(workspace, map, '')
    diffs_after = util.compare_images(expected_file, thumbnail_path)
    shutil.copyfile(thumbnail_path, '/code/tmp/artifacts/upgrade_v1_10_map_thumbnail_after.png')
    assert diffs_after < 1000

    process_client.delete_layer(layer_workspace, layer)
    process_client.delete_map(workspace, map)