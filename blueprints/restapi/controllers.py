# coding=utf-8

from flask import current_app, g
import math

from utils.response import output_json
from utils.request import get_param, get_args
from utils.model import make_dotted_dict
from utils.misc import parse_int

from helpers.app import run_hook
from helpers.content import (parse_page_metas,
                             query_by_files,
                             query_segments,
                             search_by_files,
                             find_content_file,
                             parse_page_content,
                             helper_wrap_languages,
                             helper_wrap_category,
                             helper_wrap_menu,
                             helper_wrap_slot)


@output_json
def get_view_metas(app_id):
    config = current_app.config
    curr_app = g.curr_app

    theme_meta = curr_app['theme_meta']
    site_meta = curr_app['meta']

    config['site_meta'] = site_meta
    config['theme_meta'] = theme_meta

    run_hook('config_loaded', config=_hook_config())

    site_meta['slug'] = curr_app['slug']
    site_meta['type'] = curr_app['type']

    languages = curr_app['languages']
    locale = curr_app['locale']

    context = {
        'site_meta': site_meta,
        'theme_meta': theme_meta,
        'base_url': g.curr_base_url,
        'theme_url': config.get('THEME_URL', ''),
        'res_url': config.get('RES_URL', ''),
        'lang': locale.split('_')[0],
        'locale': locale,
        'languages': helper_wrap_languages(languages, locale),
        'menu': helper_wrap_menu(curr_app, g.curr_base_url),
        'content_type': curr_app['content_types'],
        'slot': helper_wrap_slot(curr_app)
    }
    return context


@output_json
def get_view_category(app_id):
    term_keys = get_args('term_keys', default=False, multiple=True)
    return {
        'category': helper_wrap_category(g.curr_app, term_keys)
    }


@output_json
def get_view_tags(app_id, type_slug=None):
    pass


@output_json
def search_view_contents(app_id):
    content_type = get_param('content_type', str, True)
    keywords = get_param('keywords', list, default=[])
    perpage = get_param('perpage', int, default=0)
    paged = get_param('paged', int, default=0)

    run_hook('config_loaded', config=_hook_config())

    theme_opts = g.curr_app['theme_meta'].get('options', {})

    if not perpage:
        perpage = theme_opts.get('perpage')

    perpage, paged = _safe_paging(perpage, paged)

    limit = perpage
    offset = max(perpage * (paged - 1), 0)

    results, total_count = search_by_files(content_type=content_type,
                                           keywords=keywords,
                                           offset=offset,
                                           limit=limit)

    max_pages = max(int(math.ceil(total_count / float(perpage))), 1)
    paged = min(max_pages, paged)

    pages = [parse_page_metas(p) for p in results]
    run_hook('get_pages', pages=pages, current_page_id=None)

    return output_result(contents=pages, perpage=perpage, paged=paged,
                         total_pages=max_pages, total_count=total_count)


@output_json
def query_view_contents(app_id):
    attrs = get_param('attrs', list, False, [])
    content_type = get_param('content_type', str, default='')
    sortby = get_param('sortby', list, False, [])
    perpage = get_param('perpage', int, False, 1)
    paged = get_param('paged', int, False, 0)
    with_content = get_param('with_content', bool, default=False)
    term = get_param('term')
    tag = get_param('tag')

    run_hook('config_loaded', config=_hook_config())

    theme_meta = g.curr_app['theme_meta']
    theme_opts = theme_meta.get('options', {})

    # set default params
    if not content_type:
        content_type = current_app.db.Document.STATIC_TYPE

    if not sortby:
        sortby = theme_opts.get('sortby', 'updated')

    if not perpage:
        perpage = theme_opts.get('perpage')

    perpage, paged = _safe_paging(perpage, paged)

    # position
    limit = perpage
    offset = max(perpage * (paged - 1), 0)

    # query content files
    results, total_count = query_by_files(attrs=attrs,
                                          content_type=content_type,
                                          term=term,
                                          tag=tag,
                                          offset=offset,
                                          limit=limit,
                                          sortby=sortby)
    pages = []
    for p in results:
        p_content = p.get('content', '')
        p = parse_page_metas(p)
        if with_content:
            p['content'] = parse_page_content(p_content)
        pages.append(p)
    run_hook('get_pages', pages=pages, current_page_id=None)

    max_pages = max(int(math.ceil(total_count / float(perpage))), 1)

    return output_result(contents=pages, perpage=perpage, paged=paged,
                         total_pages=max_pages, total_count=total_count)


@output_json
def get_view_content_list(app_id, type_slug=None):
    perpage = get_args('perpage', default=0)
    paged = get_args('paged', default=0)
    sortby = get_args('sortby', default='', multiple=True)
    priority = get_args('priority', default=True)
    term = get_args('term')
    tag = get_args('tag')

    run_hook('config_loaded', config=_hook_config())

    theme_opts = g.curr_app['theme_meta'].get('options', {})
    priority = bool(priority)

    # set default params
    if not sortby:
        sortby = theme_opts.get('sortby', 'updated')
        if isinstance(sortby, str):
            sortby = [sortby]
        elif not isinstance(sortby, list):
            sortby = []

    if not perpage:
        perpage = theme_opts.get('perpage')

    if not type_slug:
        type_slug = current_app.db.Document.STATIC_TYPE

    perpage, paged = _safe_paging(perpage, paged)

    # position
    limit = perpage
    offset = max(perpage * (paged - 1), 0)

    # query content files
    results, total_count = query_by_files(content_type=type_slug,
                                          term=term,
                                          tag=tag,
                                          offset=offset,
                                          limit=limit,
                                          sortby=sortby)
    curr_index = offset

    pages = []
    for p in results:
        p = parse_page_metas(p)
        pages.append(p)
    run_hook('get_pages', pages=pages, current_page_id=None)

    max_pages = max(int(math.ceil(total_count / float(perpage))), 1)

    for p in pages:
        _add_cursor(content=p,
                    index=curr_index,
                    perpage=perpage,
                    paged=paged,
                    total_pages=max_pages,
                    total_count=total_count)
        curr_index += 1

    return pages


@output_json
def get_view_content(app_id, type_slug, slug):
    content_file = find_content_file(type_slug, slug)
    if not content_file:
        Exception('content file not found.')

    run_hook('config_loaded', config=_hook_config())

    page_content = {'content': content_file.get('content', '')}
    page_content['content'] = parse_page_content(page_content['content'])
    run_hook('get_page_content', pack=page_content)

    page_meta = parse_page_metas(content_file)
    run_hook('get_page_meta', meta=page_meta, redirect=None)

    return {
        'id': content_file['_id'],
        'meta': page_meta,
        'content': page_content['content']
    }


@output_json
def get_view_segments(app_id):
    content_type = get_args('content_type', default='page')
    parent = get_args('parent', default='index')

    app = g.curr_app

    run_hook('config_loaded', config=_hook_config())

    results = query_segments(app, content_type, parent)
    pages = []
    for p in results:
        p_content = p.get('content', '')
        p = parse_page_metas(p)
        p['content'] = parse_page_content(p_content)
        pages.append(p)

    run_hook('get_pages', pages=pages, current_page_id=None)

    return pages


# helpers
def _add_cursor(content, index, perpage, paged, total_pages, total_count):
    content.update({
        '_num': index + 1,
        '_index': index,
        '_perpage': perpage,
        '_paged': paged,
        '_page_range': [p for p in range(1, total_pages + 1)],
        '_total_pages': total_pages,
        '_total_count': total_count,
        '_has_prev': paged > 1,
        '_has_next': paged < total_pages,
        '_more': paged < total_pages,
        '_count': total_count,
    })
    return content


def _safe_paging(perpage, paged):
    max_perpage = current_app.db.Document.MAXIMUM_QUERY
    perpage = parse_int(perpage, 12, True)
    paged = parse_int(paged, 1, True)
    return min(perpage, max_perpage), paged


def _hook_config():
    config = current_app.config
    config['site_meta'] = g.curr_app['meta']
    config['theme_meta'] = g.curr_app['theme_meta']
    return make_dotted_dict(config)


# outputs
def output_result(contents, perpage, paged, total_pages, total_count):
    return {
        'contents': contents,
        'perpage': perpage,
        'paged': paged,
        'total_pages': total_pages,
        'total_count': total_count,
        'page_range': [p for p in range(1, total_pages + 1)],
        'has_prev': paged > 1,
        'has_next': paged < total_pages,
    }
