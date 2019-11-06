# coding=utf-8


def register_blueprints(app):
    # register regular
    from .regular import blueprint as regular_module
    app.register_blueprint(regular_module)

    # restapi
    from .restapi import blueprint as restapi_module
    app.register_blueprint(restapi_module, url_prefix='/restapi/app')

    # uploads
    from .uploads import blueprint as uploads_module
    app.register_blueprint(uploads_module, url_prefix='/uploads')
