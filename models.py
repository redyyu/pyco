# coding=utf8

import os
import re
import yaml
import json
import urllib

from utils.misc import process_slug, gen_excerpt


class DBConnection:
    models = dict()

    def register(self, models):
        for model in models:
            self.models[model.__name__] = model

    def __getattr__(self, name):
        try:
            attr = self.models[name]
        except Exception:
            raise Exception('Model `{}` not registerd.'.format(name))
        return attr


# base
class FlatFile:
    _id = None
    path = str()
    data = dict()
    raw = None

    def __init__(self, path):
        self._id = path
        if isinstance(path, str):
            self.path = path
        self._load_raw()

    def __getitem__(self, key):
        if key == '_id':
            return self._id
        else:
            return self.data[key]

    def __setitem__(self, key, value):
        if key == '_id':
            self._id = value
        else:
            self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def save(self):
        with open(self.path, 'w') as f:
            f.write(self.raw or '')
        return self._id

    def delete(self):
        if os.path.isfile(self.path):
            os.remove(self.path)
        return self._id

    def _load_raw(self):
        if os.path.isfile(self.path):
            with open(self.path, 'r') as fh:
                self.raw = fh.read()
        else:
            self.raw = None

    def _prepare_field(self, x):
        if isinstance(x, dict):
            return {k.capitalize(): self._prepare_field(v)
                    for k, v in x.items()}
        elif isinstance(x, list):
            return list([self._prepare_field(i) for i in x])
        elif isinstance(x, str):
            return urllib.parse.unquote(x)
        elif isinstance(x, (int, float, bool)) or x is None:
            return x
        else:
            try:
                x = urllib.parse.unquote(str(x))
            except Exception as e:
                x = str(e)
        return x

    def _parse_field(self, x):
        if isinstance(x, dict):
            return dict((k.lower(), self._parse_field(v))
                        for k, v in x.items())
        elif isinstance(x, list):
            return list([self._parse_field(i) for i in x])
        elif isinstance(x, (str, int, float, bool)) or x is None:
            return x
        else:
            try:
                x = str(x)
            except Exception as e:
                x = str(e)
        return x


class Configure(FlatFile):

    path = 'configure.yaml'
    data = {}

    def __init__(self):
        super(Configure, self).__init__(self.path)
        if self.raw:
            fields = yaml.safe_load(self.raw)
            self.data = self._parse_field(fields)

    def save(self):
        self.raw = yaml.safe_dump(self._prepare_field(self.data),
                                  stream=None,
                                  default_flow_style=False,
                                  indent=2,
                                  encoding=None)
        return super(Configure, self).save()

    def exists(self):
        return self.raw and self.data


class Theme(FlatFile):
    config_file_path = 'config.json'
    data = {}

    def __init__(self, theme_path):
        self.path = os.path.join(theme_path, self.config_file_path)
        super(Theme, self).__init__(self.path)
        self.data = json.loads(self.raw)

    def save(self):
        raise Exception('Save is not allowed.')

    def delete(self):
        raise Exception('Delete is not allowed.')


class Site(FlatFile):
    CONTENT_DIR = 'content'

    DEFUALT_SITE = {
        "app_id": "pyco_app",
        "slug": "pyco",
        "locale": "en_US",
        "content_types": {
            "page": "Pages",
        },
        "menus": {
            "primary": []
        },
        "meta": {
            "title": "Pyco",
        }
    }

    path = os.path.join(CONTENT_DIR, 'site.json')
    data = {}

    def __init__(self):
        super(Site, self).__init__(self.path)
        self._ensure()

    def _ensure(self):
        if self.raw is None:
            self.data = self.DEFUALT_SITE
            self.save()
        self.parse()

    def save(self):
        self.raw = json.dumps(self.data)
        return super(Site, self).save()

    def parse(self):
        site = json.loads(self.raw)
        site_meta = site.pop('meta')
        languages = site_meta.pop('languages')
        self._id = site.get('app_id', self._id)
        self.data = {
            '_id': self._id,
            'slug': site.get('slug'),
            'locale': site.get('locale'),
            'content_types': site.get('content_types'),
            'categories': site.get('categories'),
            'menus': site.get('menus'),
            'slots': site.get('slots'),
            'meta': site_meta,
            'languages': languages
        }


class Document(FlatFile):

    CONTENT_DIR = 'content'
    CONTENT_FILE_EXT = '.md'

    MAXIMUM_QUERY = 60
    MAXIMUM_STORAGE = 360

    EXCERPT_LENGTH = 600

    DEFAULT_CONTENT_TYPE = 'page'

    DEFAULT_INDEX_SLUG = 'index'
    DEFAULT_SEARCH_SLUG = 'search'
    DEFAULT_CATEGORY_SLUG = 'category'
    DEFAULT_TAG_SLUG = 'tag'
    DEFAULT_404_SLUG = 'error-404'

    RESERVED_SLUGS = [
        DEFAULT_INDEX_SLUG,
        DEFAULT_TAG_SLUG,
        DEFAULT_CATEGORY_SLUG,
        DEFAULT_SEARCH_SLUG,
    ]

    SORTABLE_FIELD_KEYS = ('date', 'updated')
    QUERYABLE_FIELD_KEYS = ('slug', 'parent', 'priority', 'template',
                            'date', 'updated', 'creation')

    path = ''
    data = {}
    _updated = None
    _creation = None

    def __init__(self, path):
        super(Document, self).__init__(path)
        self.parse()

    def save(self):
        _fields = self.data.get('meta', {})
        _fields.update({
            'template': self.data.get('template', ''),
            'priority': self.data.get('priority', 0),
            'parent': self.data.get('parent', ''),
            'date': self.data.get('date', ''),
            'tags': self.data.get('tags', []),
            'terms': self.data.get('terms', []),
            'redirect': self.data.get('redirect', ''),
            'status': self.data.get('status', 1),
        })

        fields = yaml.safe_dump(self._prepare_field(_fields),
                                stream=None,
                                default_flow_style=False,
                                indent=2,
                                encoding=None)
        content = self.data.get('content', '')
        self.raw = '/*\n{}\n*/\n{}'.format(fields, content)
        return super(Document, self).save()

    def parse(self):
        self._refresh_time()
        # raw string
        p = r'(\n)*/\*(\n)*(?P<fields>(.*\n)*)\*/(?P<content>(.*(\n)?)*)'
        re_pattern = re.compile(p)
        m = re_pattern.match(self.raw)
        if m is None:
            fields = {}
            content = ''
        else:
            fields = yaml.safe_load(m.group('fields'))
            content = m.group('content')

        self._parse_structure(self._parse_field(fields), content)

    def _parse_structure(self, fields, content):
        tags = [tag.strip().lower() for tag in fields.pop('tags', [])
                if isinstance(tag, str)]
        template = fields.pop('template', self.content_type)
        priority = fields.pop('priority', 0)
        parent = fields.pop('parent', '')
        date = fields.pop('date', '')
        terms = fields.pop('terms', [])
        redirect = fields.pop('redirect', '')
        status = fields.pop('status', 1)

        self.data = {
            '_id': self._id,
            '_keywords': [self.slug] + tags,
            'slug': self.slug,
            'content_type': self.content_type,
            'priority': priority,
            'parent': parent,
            'date': date,
            'tags': tags,
            'terms': terms,
            'redirect': redirect,
            'template': template,
            'status': status,
            'meta': fields,
            'content': content,
            'excerpt': gen_excerpt(content, self.EXCERPT_LENGTH),
            'updated': self._updated,
            'creation': self._creation,
        }

    def _refresh_time(self):
        try:
            self._updated = int(os.path.getmtime(self.path))
            self._creation = int(os.path.getctime(self.path))
        except Exception:
            self._updated = None
            self._creation = None

    @property
    def slug(self):
        _path = os.path.splitext(self.path)[0]
        return process_slug(_path.split('/')[-1])

    @property
    def content_type(self):
        path_parts = self.path.split('/')
        if len(path_parts) > 2:
            content_type = path_parts[1].lower()
        else:
            content_type = self.DEFAULT_CONTENT_TYPE
        return content_type

    # query methods
    @classmethod
    def find_one(cls, slug, content_type=None):
        if content_type in [None, cls.DEFAULT_CONTENT_TYPE]:
            rel_path = os.path.join(cls.CONTENT_DIR, slug)
        else:
            rel_path = os.path.join(cls.CONTENT_DIR, content_type, slug)
        path = '{}{}'.format(rel_path, cls.CONTENT_FILE_EXT)
        if os.path.isfile(path):
            return cls(path)
        else:
            return None

    @classmethod
    def find(cls, content_type=None):
        if content_type == cls.DEFAULT_CONTENT_TYPE:
            f_dir = os.path.join(cls.CONTENT_DIR)
        else:
            f_dir = os.path.join(cls.CONTENT_DIR, content_type)
        file_paths = [os.path.join(f_dir, f) for f in os.listdir(f_dir)
                      if f.endswith(cls.CONTENT_FILE_EXT) and
                      not f.startswith('_')]
        return [cls(f) for f in file_paths[:cls.MAXIMUM_STORAGE]]
