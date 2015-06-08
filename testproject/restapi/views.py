#coding=utf-8

from django.shortcuts import render

from decorators import api_lookup_table


def document(request):
    return render(request, 'restapi/doc.html', {
        'apis': api_lookup_table
    })