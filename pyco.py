# coding=utf-8
from __future__ import absolute_import

import argparse
import os
import sys
import traceback

from flask import Flask, current_app, request, abort, g
from flask.json import JSONEncoder
from jinja2 import FileSystemLoader

from utils.misc import route_inject
from utils.response import make_json_response

from routes import urlpatterns
from loaders import load_config, load_plugins, load_uploads


__version_info__ = ('2', '0', '0')
__version__ = '.'.join(__version_info__)

# parse args
parser = argparse.ArgumentParser(
    description='Options of starting Pyco server.')

args, unknown = parser.parse_known_args()

# create app
app = Flask(__name__)
app.version = __version__

load_config(app)

# make importable for plugin folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, app.config.get("PLUGIN_DIR")))

# init app
app.debug = app.config.get("DEBUG", True)
app.template_folder = os.path.join(app.config.get("THEMES_DIR"),
                                   app.config.get("THEME_NAME"))

app.static_folder = app.config.get("THEMES_DIR")
app.static_url_path = "/{}".format(app.config.get("STATIC_PATH"))

# jinja env
app.jinja_env.autoescape = False
app.jinja_env.finalize = lambda x: '' if hasattr(x, '__call__') else x
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
# app.jinja_env.add_extension('jinja2.ext.i18n')
app.jinja_env.add_extension('jinja2.ext.do')
app.jinja_env.add_extension('jinja2.ext.with_')
# app.jinja_env.install_gettext_callables(gettext, ngettext, newstyle=True)

app.json_encoder = JSONEncoder

# config
load_config(app)
# plugins
load_plugins(app)

# routes
route_inject(app, urlpatterns)

# static
app.add_url_rule(
    app.static_url_path + '/<path:filename>',
    view_func=app.send_static_file,
    endpoint='static'
)
# uplaods
app.add_url_rule(
    "/{}/<path:filepath>".format(app.config.get('UPLOADS_DIR')),
    view_func=load_uploads,
    methods=['GET']
)


@app.before_request
def before_request():
    if request.method == "OPTIONS":
        resp = current_app.make_default_options_response()
        return resp
    elif request.path.strip("/") in current_app.config.get('SYS_ICON_LIST'):
        abort(404)

    base_url = current_app.config.get("BASE_URL")
    uploads_dir = current_app.config.get("UPLOADS_DIR")

    g.curr_base_url = base_url
    g.request_path = request.path
    g.request_url = "{}/{}".format(g.curr_base_url, g.request_path)
    g.uploads_url = "{}/{}".format(base_url, uploads_dir)

    if current_app.debug:
        # change template folder
        themes_dir = current_app.config.get("THEMES_DIR")
        theme_name = current_app.config.get("THEME_NAME")
        current_app.template_folder = os.path.join(themes_dir, theme_name)
        # change reload template folder
        current_app.jinja_env.cache = None
        tpl_folder = current_app.template_folder
        current_app.jinja_loader = FileSystemLoader(tpl_folder)


@app.errorhandler(Exception)
def errorhandler(err):
    curr_file = ''
    if 'current_file' in dir(err):
        curr_file = err.current_file
    err_msg = "{}: {}\n{}".format(repr(err),
                                  curr_file,
                                  traceback.format_exc())
    err_html_msg = "<h1>{}: {}</h1><p>{}</p>".format(repr(err),
                                                     curr_file,
                                                     traceback.format_exc())
    current_app.logger.error(err_msg)
    return make_json_response(err_html_msg, 500)


if __name__ == "__main__":
    host = app.config.get("HOST")
    port = app.config.get("PORT")

    print "-------------------------------------------------------"
    print "Pyco: {}".format(app.version)
    print "-------------------------------------------------------"

    if app.debug:
        debug_msg = "\n".join(["Pyco is running in DEBUG mode !!!",
                               "Jinja2 template folder is about to reload."])
        print(debug_msg)

    app.run(host=host, port=port, debug=True, threaded=True)
