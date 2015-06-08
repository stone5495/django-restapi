from django.db import models


from restapi.decorators import api, param, example, url_param
from restapi.exceptions import APIError


@api(group='abc', url='dddd')
@param('x', type=int)
@param('y', type=int)
def add(x, y):
    """
    add x and y, return the result
    """
    return x+y

