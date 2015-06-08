#coding=utf-8


class APIError(Exception):

    def __init__(self, status, data):
        self.status = status
        self.data = data