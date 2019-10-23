#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class EnchantException(Exception):
    def __init__(self, msg=''):
        self.msg = msg

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.msg)

    def __repr__(self):
        return self.__str__()

class EConfigNotFound(EnchantException):
    pass

class EFileNotFound(EnchantException):
    pass

class EConfigParseError(EnchantException):
    pass

class EVideoFormatNotSupported(EnchantException):
    pass

class ESubtitleFormatNotSupported(EnchantException):
    pass

class EDuplicatedSubtitleFile(EnchantException):
    pass

class EDuplicatedVideoFile(EnchantException):
    pass

class EObjectNotFound(EnchantException):
    pass

class EMovieNotFound(EnchantException):
    pass