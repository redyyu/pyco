#coding=utf-8
from __future__ import absolute_import

_CONFIG = {}
_DEFAULT_ADDITIONAL_METAS = ["nav","link","target","parent","thumbnail"]
_ADDITIONAL_METAS = None
_ORDER_DESC = False
_ORDER_BY = 'date'
_navs = []

def config_loaded(config):
    global _CONFIG, _ADDITIONAL_METAS, _ORDER_BY, _ORDER_DESC

    _CONFIG = config
    
    if _CONFIG.get('POST_ORDER') == 'desc':
        _ORDER_DESC = True

    _ORDER_BY = _CONFIG.get('POST_ORDER_BY') or _ORDER_BY
    
    _ADDITIONAL_METAS = set(_CONFIG.get("ADDITIONAL_METAS",[]) + _DEFAULT_ADDITIONAL_METAS)
    return


def get_post_data(data, post_meta):
    for key in _ADDITIONAL_METAS:
        data[key] = post_meta.get(key)
    return


def get_posts(posts, current_post, prev_post, next_post):
    # global _navs
 #    _navs = [post for post in posts if post.get("nav")]
 #
 #    for item in _navs:
 #        try:
 #            order = int(item.get('order'))
 #        except Exception:
 #            order = None
 #
 #        item['order'] =  order or 0
 #    _navs=sorted(posts,key=lambda x: (x['order'], x[_ORDER_BY]),reverse=_ORDER_DESC)
    
    return


def before_render(var,template):
    # var["navigation"] = _navs
    return