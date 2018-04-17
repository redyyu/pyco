# coding=utf-8
from __future__ import absolute_import

from flask import current_app, Markup, g

import re

from utils.validators import url_validator
from utils.misc import parse_int, match_cond, sortedby, parse_sortby


def query_by_files(content_type=None, attrs=None, taxonomy=None,
                   offset=0, limit=1, sortby=None):
    # query
    files = _query(g.files, content_type, attrs, taxonomy)
    total_count = len(files)

    # sorting
    sorting = _sorting(files, parse_sortby(sortby))

    limit = parse_int(limit, 1, True)
    offset = parse_int(offset, 0, 0)

    if sorting:
        ids = [item['_id'] for item in sorting[offset:offset + limit]]
        order_dict = {_id: index for index, _id in enumerate(ids)}
        files = [f for f in files if f['_id'] in ids]
        files.sort(key=lambda x: order_dict[x['_id']])
    else:
        files = files[offset:offset + limit]
    return files, total_count


# segments
def query_segments(app, type_slug, parent_slug):
    _config = app['theme_meta']
    _opts = _config.get('options', {})
    sortby = parse_sortby(_opts.get('sortby', 'updated'))
    tmpls = [tmpl.replace('^', '') for tmpl in _config.get('templates', [])
             if tmpl.startswith('^')]

    if parent_slug == current_app.config.get('DEFAULT_INDEX_SLUG'):
        parent_slugs = ['', parent_slug]
    else:
        parent_slugs = [parent_slug]

    if tmpls:
        segments = [f for f in g.files if f['template'] in tmpls and
                    f['parent'] in parent_slugs and
                    f['content_type'] == type_slug]
        segments = sortedby(segments, [('priority', 1), sortby])[:60]
    else:
        segments = []
    return segments


# search
def search_by_files(keywords, content_type=None,
                    offset=0, limit=0, use_tags=True):
    if content_type:
        files = [f for f in g.files if f['content_type'] == content_type]
    else:
        files = g.files

    if not keywords:
        results = files
    else:
        results = []
        if isinstance(keywords, basestring):
            keywords = keywords.split()
        elif not isinstance(keywords, list):
            keywords = []

        def _search_match(keyword, f):
            if keyword in f['tags'] and keyword in f['participle']:
                return True
            return False

        results = files
        for kw in keywords:
            results = [f for f in results if _search_match(kw, f)]

    limit = parse_int(limit, 1, True)
    offset = parse_int(offset, 0, 0)

    return results[offset:offset + limit], len(results)


def find_content_file_by_id(file_id):
    if not file_id:
        return None
    for f in g.files:
        if f['_id'] == file_id:
            return f
    return None


def find_content_file(type_slug, file_slug):
    if not type_slug:
        type_slug = 'page'
    for f in g.files:
        if f['slug'] == file_slug and f['content_type'] == type_slug:
            return f
    return None


def parse_page_content(content_string):
    return Markup(content_string)


def parse_page_metas(page, current_id=None):
    data = dict()
    meta = page.get('meta')
    for m in meta:
        data[m] = meta[m]
    data['id'] = unicode(page['_id'])
    data['app_id'] = unicode(page['app_id'])
    data['slug'] = page['slug']
    data['type'] = data['content_type'] = page['content_type']
    data['template'] = page['template']
    data['parent'] = page['parent']
    data['priority'] = page['priority']
    data['status'] = page['status']
    data['date'] = page['date']
    data['value'] = page['value']
    data['tags'] = page['tags']
    data['taxonomy'] = page['taxonomy']
    data['valuation'] = page['valuation']
    data['updated'] = page['updated']
    data['creation'] = page['creation']
    data['excerpt'] = gen_file_excerpt(page['content'])
    data['description'] = meta.get('description') or data['excerpt']
    data['url'] = gen_page_url(page)
    data['path'] = gen_page_path(page)

    # content marks
    config = current_app.config
    if data['slug'] == config.get('DEFAULT_INDEX_SLUG'):
        data['is_front'] = True
    if data['slug'] == config.get('DEFAULT_404_SLUG'):
        data['is_404'] = True
    if unicode(data['id']) == unicode(current_id):
        data['is_current'] = True

    return data


def gen_file_excerpt(content, excerpt_length=144):
    excerpt_ellipsis = u'&hellip;'
    excerpt = re.sub(r'<.*?>', '', content).strip()
    return u'{}{}'.format(excerpt[0:excerpt_length], excerpt_ellipsis)


def gen_page_path(data, static_type='page', index='index'):
    slug = data.get('slug')
    if data['content_type'] == static_type:
        if slug == index:
            slug = ''
        path = u'/{}'.format(slug)
    else:
        path = u'/{}/{}'.format(data['content_type'], slug)
    return path


def gen_page_url(data, static_type='page', index='index'):
    slug = data.get('slug')
    if data.get('content_type') == static_type:
        if slug == index:
            slug = ''
        url = u'{}/{}'.format(g.curr_base_url, slug)
    else:
        url = u'{}/{}/{}'.format(g.curr_base_url, data['content_type'], slug)
    return url


# menus
def helper_wrap_menu(menus, base_url=u''):
    if not menus:
        return {}

    def process_menu_url(menu):
        for item in menu:
            link = item.get('link', '')
            if link:
                # url
                if url_validator(link):
                    item['url'] = link
                else:
                    item['url'] = u'{}/{}'.format(base_url, link.strip('/'))
                # path
                if url_validator(link):
                    if link.startswith(base_url):
                        _path = link.replace(base_url, '')
                        item['path'] = u'/{}'.format(_path)
                    else:
                        item['path'] = u''
                elif not link.startswith('/'):
                    item['path'] = u'/{}'.format(link)
                else:
                    item['path'] = link
                # hash
                if not url_validator(link):
                    _relpath = link.strip('/')
                    _hashtag = '' if _relpath.startswith('#') else '#'
                    item['hash'] = u'{}{}'.format(_hashtag, _relpath)
                else:
                    item['hash'] = u''
            else:
                item['url'] = u''
                item['hash'] = u''
                item['path'] = u''

            # name
            item['name'] = item['name'] or item['key']

            # nodes
            item['nodes'] = process_menu_url(item.get('nodes', []))
        return menu

    menu_dict = {}
    for slug, nodes in menus.iteritems():
        nodes = process_menu_url(nodes)
        menu_dict[slug] = nodes
    return menu_dict


# socials
def helper_wrap_socials(socials):
    """ socials data sample
    [
       {
            'key': 'facebook',
            'name':'Facebook',
            'url':'http://....',
            'figure':'http://....',
            'script': '....'
       },
       {
            'key': 'twitter',
            'name':'Twitter',
            'url':'http://....',
            'figure':'http://....',
            'script': '....'
       }
    ]
    """

    if not socials or not isinstance(socials, list):
        return []

    return [social for social in socials if social.get('key')]


# taxonomy
def helper_pack_taxonomies(taxonomies, content_type=None):
    if not taxonomies:
        return {}
    tax_map = {}
    for k, v in taxonomies.iteritems():
        if content_type and content_type not in v['content_types']:
            continue
        tax_map[k] = {
            'title': v['title'],
            'content_types': v['content_types']
        }
    return tax_map


def helper_wrap_taxonomy(taxonomies, tax_slug):
    if not taxonomies or not taxonomies.get(tax_slug):
        return {}

    tax = taxonomies[tax_slug]

    def _parse_term(term, is_parent=True):
        term.setdefault('parent', u'')
        term.setdefault('priority', 0)
        term.setdefault('status', 1)
        term.setdefault('meta', {})
        term['meta'].setdefault('name', u'...')
        term['meta'].setdefault('figure', u'')
        if is_parent:
            term.setdefault('nodes', [])
            term['nodes'] = [_parse_term(child, False)
                             for child in term['nodes']
                             if child.get('key')]
        return term

    return {
        'slug': tax_slug,
        'title': tax.get('title'),
        'content_types': tax.get('content_types', []),
        'terms': [_parse_term(term) for term in tax['terms']
                  if term.get('key')],
    }


# slot
def helper_wrap_slot(slots):
    if not slots:
        return {}
    slots_map = {}
    for k, v in slots.iteritems():
        slots_map[k] = {
            'name': v.get('src', u''),
            'src': v.get('src', u''),
            'route': v.get('route', u''),
            'scripts': v.get('scripts', u''),
        }
    return slots_map


# translates
def helper_wrap_translates(languages, locale):
    """ languages data sample
    [
       {'key': 'zh_CN', 'name': '汉语', 'url': 'http://.....'},
       {'key': 'en_US', 'name': 'English', 'url': 'http://.....'}
    ]
    """

    if not languages or not isinstance(languages, list):
        return []

    trans_list = [trans for trans in languages if trans.get('key')]
    lang = locale.split('_')[0]

    for trans in trans_list:
        trans_key = trans['key'].lower()
        if trans_key == locale.lower() or trans_key == lang.lower():
            trans['active'] = True

    return trans_list


# helpers
def _query(files, content_type=None, attrs=None, taxonomy=None):
    QUERYABLE_FIELD_KEYS = current_app.config.get('QUERYABLE_FIELD_KEYS')
    RESERVED_SLUGS = current_app.config.get('RESERVED_SLUGS')

    if content_type:
        files = [f for f in files if f['content_type'] == content_type]

    if isinstance(attrs, (basestring, dict)):
        attrs = [attrs]
    elif not isinstance(attrs, list):
        attrs = []

    for attr in attrs[:5]:  # max fields key is 5
        opposite = False
        force = False
        attr_key = None
        attr_value = ''

        if isinstance(attr, basestring):
            attr_key = attr.lower()
        elif isinstance(attr, dict):
            opposite = bool(attr.pop('not', False))
            force = bool(attr.pop('force', False))
            if attr:
                attr_key = attr.keys()[0]
                attr_value = attr[attr_key]
            else:
                continue

        if attr_key is None:
            continue

        if attr_key not in QUERYABLE_FIELD_KEYS and '.' not in attr_key:
            attr_key = 'meta.{}'.format(attr_key)
        files = [f for f in files
                 if f['slug'] not in RESERVED_SLUGS and
                 match_cond(f, attr_key, attr_value, force, opposite)]

    if taxonomy:
        tax_slug = taxonomy.get('tax')
        term_key = taxonomy.get('term')
        output = []

        for file in files:
            if term_key in file['taxonomy'].get(tax_slug, []):
                output.append(file)
    else:
        output = files

    return output


def _sorting(files, sort):
    SORTABLE_FIELD_KEYS = current_app.config.get('SORTABLE_FIELD_KEYS')

    sorts = [('priority', 1)]
    if isinstance(sort, tuple):
        sort_key = sort[0]
        if sort_key in SORTABLE_FIELD_KEYS:
            sorts.append(sort)

    sorting = []
    for f in files:
        new_entry = {'_id': f['_id']}
        for sort in sorts:
            new_entry[sort[0]] = f[sort[0]]
        sorting.append(new_entry)

    return sortedby(sorting, sorts)
