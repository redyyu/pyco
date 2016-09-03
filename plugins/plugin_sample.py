# coding=utf-8
from __future__ import absolute_import


def config_loaded(config):
    print "config loaded"
    return


def request_url(request):
    print "request url"
    return


def before_load_content(path):
    print "before load content"
    return


def after_load_content(path, file):
    print "after load content"
    return


def before_404_load_content(path):
    print "before 404 load content"
    return


def after_404_load_content(path, file):
    print "after 404 load content"
    return


def before_parse_content(content):
    print "before parse content"
    return


def after_parse_content(content):
    print "after parse content"
    return


def before_read_page_meta(headers):
    print "before read page meta"
    return


def after_read_page_meta(page_meta, redirect_to):
    print "after read page meta"
    return


def get_page_data(data):
    print "get page data"
    return


def get_pages(pages, current_page):
    print "get pages"
    return


def before_render(var, template):
    print "before render"
    return


def after_render(output):
    print "after render"
    return
