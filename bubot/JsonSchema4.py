import json
import urllib.parse
from .Helper import Helper
from os import path
import os.path


class JsonSchemaLoaderMixin:
    def __init__(self, **kwargs):
        self.dir = kwargs.get('dir', ['{}/schemas'.format(path.normpath(path.dirname(__file__)))])
        self.cache = kwargs.get('cache', {})
        self.data = {}
        self.id = None
        self.uri = None
        self.version = None
        self.load_history = []

    def load_from_uri(self, uri, **kwargs):
        uri = urllib.parse.urlparse(uri)  # (scheme, netloc, path, params, query, fragment)
        _id = self.get_id_from_uri(uri, self.id)

        if _id not in self.cache:
            JsonSchema4.load_from_file(_id, dir=self.dir, cache=self.cache)
        if not uri[5]:
            try:
                return self.cache[_id]['data']
            except KeyError:
                raise Exception('bad schema id or definition in {}'.format(_id))

        _fragment = uri[5].split('/')[1:]
        _result = self.cache[_id]
        for elem in _fragment:
            _result = _result[elem]
        return _result

    @classmethod
    def load_from_file(cls, file_name, **kwargs):
        self = cls(**kwargs)
        _path = None
        for _dir in self.dir:
            _path = '{0}/{1}'.format(_dir, file_name)
            if os.path.isfile(_path):
                break
            else:
                _path = None
        if _path is None:
            raise Exception('JsonSchema.load_from_file({0}): file not found'.format(file_name)) from None

        with open(_path, 'r', encoding='utf-8') as file:
            try:
                raw = json.load(file)
            except Exception as e:
                raise Exception('JsonSchema.load_from_file({0}): {1}'.format(file_name, e)) from None
        self.load(raw)
        return self.cache[self.id]['data']

    def load_from_rt(self, rt):
        schema = {}
        for name in rt:
            uri = '{0}-schema.json'.format(name)
            _schema = self.load_from_uri(uri)
            Helper.update_dict(schema, _schema)
        return schema

    @staticmethod
    def get_id_from_uri(uri, default=None):
        if uri[2]:
            return uri[2].split('/')[-1]
        elif default:
            return default
        raise Exception('not define scheme id')

    def load(self, schema):
        self.version = urllib.parse.urlparse(schema['$schema'])[2].split('/')[0]
        self.id = self.get_id_from_uri(urllib.parse.urlparse(schema['id']))
        self.cache[self.id] = dict(data=dict(), definitions=dict())
        if 'definitions' in schema:
            for tmpl in schema['definitions']:
                self.cache[self.id]['definitions'][tmpl] = dict()
                for props in schema['definitions'][tmpl]:
                    _type = schema['definitions'][tmpl][props].__class__.__name__
                    self.load_elem(
                        self.cache[self.id]['definitions'][tmpl],
                        schema['definitions'][tmpl][props],
                        props
                    )
        for elem in schema:
            if elem != 'definitions':
                self.load_elem(self.cache[self.id]['data'], schema[elem], elem)
        pass

    # @staticmethod
    # def add_prop(data, node, name, default=None):
    #     try:
    #         data[name] = node['name']
    #     except KeyError:
    #         if default is not None:
    #             data[name] = default

    def load_elem_ref(self, data, value, name):
        res = self.load_from_uri(value)
        Helper.update_dict(data, res)

    def load_elem(self, data, value, name):
        try:
            value_type = value.__class__.__name__
            getattr(self, 'load_elem_{}'.format(value_type))(
                data, value, name)
        except Exception as e:
            raise Exception('load_elem {0}: {1}'.format(name, value))
        pass

    def load_elem_str(self, data, value, name):
        if name != '$ref':
            data[name] = value
            return
        self.load_elem_ref(data, value, name)

    def load_elem_dict(self, data, value, name):
        if name not in data:
            data[name] = dict()
        for elem in value:
            self.load_elem(data[name], value[elem], elem)

    def load_elem_list(self, data, value, name):
        if name == 'allOf':
            for elem in value:
                for _name in elem:
                    self.load_elem(data, elem[_name], _name)
            return
        else:
            if name not in data:
                data[name] = value
            else:
                raise NotImplemented(name)
        pass

    def load_elem_bool(self, data, value, name):
        data[name] = value

    def load_elem_int(self, data, value, name):
        data[name] = value

    def load_elem_float(self, data, value, name):
        data[name] = value


class JsonSchema4(JsonSchemaLoaderMixin):
    def __init__(self, **kwargs):
        JsonSchemaLoaderMixin.__init__(self, **kwargs)
