from celery.utils.log import get_task_logger

from geoserver import util as gs_util
from layman.celery import AbortedException
from layman import celery_app, settings
from layman.common import empty_method_returns_true
from . import wms, wfs, sld
from .. import geoserver

logger = get_task_logger(__name__)


refresh_wms_needed = empty_method_returns_true
refresh_wfs_needed = empty_method_returns_true
refresh_sld_needed = empty_method_returns_true


@celery_app.task(
    name='layman.layer.geoserver.wms.refresh',
    bind=True,
    base=celery_app.AbortableTask
)
def refresh_wms(
        self,
        username,
        layername,
        store_in_geoserver,
        description=None,
        title=None,
        ensure_user=False,
        access_rights=None,
):
    if description is None:
        description = layername
    if title is None:
        title = layername
    geoserver_workspace = wms.get_geoserver_workspace(username)
    if ensure_user:
        geoserver.ensure_workspace(username)

    if self.is_aborted():
        raise AbortedException
    if store_in_geoserver:
        gs_util.delete_wms_layer(geoserver_workspace, layername, settings.LAYMAN_GS_AUTH)
        gs_util.delete_wms_store(geoserver_workspace, settings.LAYMAN_GS_AUTH, wms.get_qgis_store_name(layername))
        geoserver.publish_layer_from_db(username,
                                        layername,
                                        description,
                                        title,
                                        access_rights,
                                        geoserver_workspace=geoserver_workspace,
                                        )
    else:
        gs_util.delete_feature_type(geoserver_workspace, layername, settings.LAYMAN_GS_AUTH)
        geoserver.publish_layer_from_qgis(username,
                                          layername,
                                          description,
                                          title,
                                          access_rights,
                                          geoserver_workspace=geoserver_workspace,
                                          )
    wms.clear_cache(username)

    if self.is_aborted():
        wms.delete_layer(username, layername)
        raise AbortedException


@celery_app.task(
    name='layman.layer.geoserver.wfs.refresh',
    bind=True,
    base=celery_app.AbortableTask
)
def refresh_wfs(
        self,
        username,
        layername,
        description=None,
        title=None,
        ensure_user=False,
        access_rights=None,
):
    if description is None:
        description = layername
    if title is None:
        title = layername
    if ensure_user:
        geoserver.ensure_workspace(username)

    if self.is_aborted():
        raise AbortedException
    geoserver.publish_layer_from_db(username, layername, description, title, access_rights)
    wfs.clear_cache(username)

    if self.is_aborted():
        wfs.delete_layer(username, layername)
        raise AbortedException


@celery_app.task(
    name='layman.layer.geoserver.sld.refresh',
    bind=True,
    base=celery_app.AbortableTask
)
def refresh_sld(self, username, layername, store_in_geoserver):
    if self.is_aborted():
        raise AbortedException
    if store_in_geoserver:
        sld.create_layer_style(username, layername)

    if self.is_aborted():
        sld.delete_layer(username, layername)
        raise AbortedException
