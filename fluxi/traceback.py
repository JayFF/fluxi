# -*- coding: utf-8 -*-
"""
from nose
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import traceback

def _decode(string):
    """Decode a string swallowing errors. Turn Nones into
    "None", which is more helpful than crashing.
    In Python 2, extract_tb() returns simple strings. We arbitrarily guess that
    iso-8859-1 is the encoding and use "replace" mode for undecodable chars. 
    """
    if string is None:
        return 'None'
    return bytes(string).decode('iso-8859-1','replace')
    #return string if isinstance(string, unicode) else string.decode('utf-8', 'replace')

def get_formatted_tb(err):
    extracted_tb=traceback.extract_tb(err[2])
    tbtext=""
    for i, (file, line_number, function, text) in enumerate(extracted_tb):
        tbtext+="\n   File %s, line %s, in %s\n       %s" % (_decode(file[-20:]), _decode(line_number), _decode(function), _decode(text))
    return tbtext
def get_error(err):
    return "%s:%s"%(_decode(err[0]),_decode(err[1]))