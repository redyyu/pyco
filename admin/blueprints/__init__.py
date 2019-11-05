# coding=utf-8
from __future__ import absolute_import


def register_admin_blueprints(app):

    from admin.blueprints.dashboard import blueprint as dashboard_module
    app.register_blueprint(dashboard_module)

    # from admin.blueprints.media import blueprint as media_module
    # app.register_blueprint(media_module, url_prefix='/media')

    from admin.blueprints.configuration import blueprint as conf_module
    app.register_blueprint(conf_module, url_prefix='/configuration')