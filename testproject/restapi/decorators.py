#coding=utf-8

from django.http import HttpResponse
from django.conf.urls import url as make_url

from exceptions import APIError

import urls
import json
import inspect


def json_response(result):
    """JSON"""
    return HttpResponse(json.dumps(result), status=200, content_type='application/json')


def json_error(error):
    """JSON"""
    return HttpResponse(json.dumps(error.data), status=error.status, content_type='application/json')


def get_param(key):
    def wrapper(request, *args, **kwargs):
        """GET"""
        return request.GET.get(key, None)

    return wrapper


def post_param(key):

    def wrapper(request, *args, **kwargs):
        return request.POST.get(key, None)

    return wrapper


def url_param(key):
    if type(key) is int:
        def wrapper(request, *args, **kwargs):
            """URL"""
            return args[key]

        return wrapper

    if type(key) is str:
        def wrapper(request, *args, **kwargs):
            """URL"""
            return kwargs[key]

        return wrapper


def inspect_func(func):
    if hasattr(func, 'rest_spec'):
        return func.rest_spec

    result = {
        'module_name': inspect.getmodule(func).__name__,
        'func_name': func.func_name,
        'description': func.__doc__,
        'params': {},
        'result': json_response,
        'result_description': json_response.__doc__,
        'error': json_error,
        'error_description': json_error.__doc__,
        'examples': {},
    }

    arg_spec = inspect.getargspec(func)

    arg_count = 0
    default_count = len(arg_spec.defaults) if arg_spec.defaults else 0
    default_start = len(arg_spec.args) - default_count

    for arg in arg_spec.args:
        default_value = arg_spec.defaults[arg_count-default_start] if arg_count >= default_start else None

        parser_func = get_param(arg)
        type_value = type(default_value) if default_value else unicode
        result['params'][arg] = {
            'description': '',
            'parser': parser_func,
            'parser_description': parser_func.__doc__,
            'type': type_value,
            'type_description': type_value.__name__,
            'required': default_value == None,
            'default':  default_value,
        }
        arg_count += 1

    func.rest_spec = result
    return result


def param(name, description='', parser=None, type=None, required=True, default=None):

    def wrapper(func):
        rest_spec = inspect_func(func)
        if name not in rest_spec['params']:
            raise Exception('%s is not a param of function %s' % (name, rest_spec['func_name']))

        param_spec = rest_spec['params'][name]

        if description: param_spec['description'] = description
        if parser:
            param_spec['parser'] = parser
            param_spec['parser_description'] = parser.__doc__
        if type:
            param_spec['type'] = type
            param_spec['type_description'] = type.__name__
        if required: param_spec['required'] = required
        if default: param_spec['default'] = default

        return func

    return wrapper


def result(handler):

    def wrapper(func):
        rest_spec = inspect_func(func)
        rest_spec['result'] = handler
        rest_spec['result_description'] = handler.__doc__
        return func

    return wrapper


def error(handler):

    def wrapper(func):
        rest_spec = inspect_func(func)
        rest_spec['error'] = handler
        rest_spec['error_description'] = handler.__doc__
        return func

    return wrapper


def example(status, data):

    def wrapper(func):
        rest_spec = inspect_func(func)
        rest_spec['examples'][status] = data
        return func

    return wrapper


api_lookup_table = {}


def api(api_func=None, name=None, group=None, url=None, method='GET'):

    def wrapper(func):
        rest_spec = inspect_func(func)

        api_group = group if group != None else rest_spec['module_name']

        if api_group not in api_lookup_table:
            api_lookup_table[api_group] = {}

        api_name = name if name else rest_spec['func_name']

        if api_name in api_lookup_table[api_group]:
            raise Exception('duplicate api name %s with function %s' % (api_name, rest_spec['func_name']))

        api_prefix = '^%s/'%api_group if api_group else '^'
        api_postfix = '/$'

        if not url:
            api_url = api_prefix + api_name + api_postfix
        else:
            api_url = api_prefix + url + api_postfix

        api_lookup_table[api_group][api_name] = {
            'method': method,
            'spec': rest_spec,
            'url': api_url
        }

        def django_view(request, *args, **kwargs):
            params = {}

            for param_name, param_spec in rest_spec['params'].iteritems():
                val = param_spec['parser'](request, *args, **kwargs)
                if val:
                    try:
                        params[param_name] = param_spec['type'](val) if param_spec['type'] else val
                    except ValueError:
                        return HttpResponse('invalid type of %s' % param_name, status=400)    
                elif param_spec['required']:
                    return HttpResponse('%s is required' % param_name, status=400)
                else:
                    params[param_name] = param_spec['default']

            try:
                result = func(**params)
                return rest_spec['result'](result)
            except APIError as err:
                return rest_spec['error'](err)

        urlpattern = make_url(api_url, django_view)
        urls.urlpatterns.append(urlpattern)
        return func


    if api_func:
        return wrapper(api_func)
    else:
        return wrapper

