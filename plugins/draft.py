# coding=utf-8
from __future__ import absolute_import

_CONFIG = {}


def config_loaded(config):
    global _CONFIG
    _CONFIG = config
    return


def single_page_meta(page_meta, redirect_to):
    if not page_meta:
        return
    page_meta['status'] = int(page_meta.get("status", 1))
    return


def get_page_data(data):
    if not data:
        return
    data["status"] = int(data.get("status", 1))
    return


def get_pages(pages, current_page):
    new_pages = [page for page in pages if page.get("status") is 1]
    del pages[:]
    for page in new_pages:
        pages.append(page)
    return
