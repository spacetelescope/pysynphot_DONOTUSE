# Licensed under a 3-clause BSD style license - see LICENSE.rst

# STDLIB
import io
import os
from setuptools import Extension

# ASTROPY
from extension_helpers import import_file, write_if_different

LOCALROOT = os.path.relpath(os.path.dirname(__file__))


def string_escape(s):
    s = s.decode('ascii').encode('ascii', 'backslashreplace')
    s = s.replace(b'\n', b'\\n')
    s = s.replace(b'\0', b'\\0')
    return s.decode('ascii')


def generate_c_docstrings():
    docstrings = import_file(os.path.join(LOCALROOT, 'docstrings.py'))
    docstrings = docstrings.__dict__
    keys = [
        key for key, val in docstrings.items()
        if not key.startswith('__') and isinstance(val, str)]
    keys.sort()
    docs = {}
    for key in keys:
        docs[key] = docstrings[key].encode('utf8').lstrip() + b'\0'

    h_file = io.StringIO()
    h_file.write("""/*
DO NOT EDIT!

This file is autogenerated by synphot/setup_package.py.  To edit
its contents, edit synphot/docstrings.py
*/

#ifndef __DOCSTRINGS_H__
#define __DOCSTRINGS_H__

#if defined(_MSC_VER)
void fill_docstrings(void);
#endif

""")
    for key in keys:
        val = docs[key]
        h_file.write('extern char doc_{0}[{1}];\n'.format(key, len(val)))
    h_file.write("\n#endif\n\n")

    write_if_different(
        os.path.join(LOCALROOT, 'include', 'docstrings.h'),
        h_file.getvalue().encode('utf-8'))

    c_file = io.StringIO()
    c_file.write("""/*
DO NOT EDIT!

This file is autogenerated by synphot/setup_package.py.  To edit
its contents, edit synphot/docstrings.py

The weirdness here with strncpy is because some C compilers, notably
MSVC, do not support string literals greater than 256 characters.
*/

#include <string.h>
#include "docstrings.h"

#if defined(_MSC_VER)
""")
    for key in keys:
        val = docs[key]
        c_file.write('char doc_{0}[{1}];\n'.format(key, len(val)))

    c_file.write("\nvoid fill_docstrings(void)\n{\n")
    for key in keys:
        val = docs[key]
        # For portability across various compilers, we need to fill the
        # docstrings in 256-character chunks
        for i in range(0, len(val), 256):
            chunk = string_escape(val[i:i + 256]).replace('"', '\\"')
            c_file.write('   strncpy(doc_{0} + {1}, "{2}", {3});\n'.format(
                key, i, chunk, min(len(val) - i, 256)))
        c_file.write("\n")
    c_file.write("\n}\n\n")

    c_file.write("#else /* UNIX */\n")

    for key in keys:
        val = docs[key]
        c_file.write('char doc_{0}[{1}] = "{2}";\n\n'.format(
            key, len(val), string_escape(val).replace('"', '\\"')))

    c_file.write("#endif\n")

    write_if_different(
        os.path.join(LOCALROOT, 'src', 'docstrings.c'),
        c_file.getvalue().encode('utf-8'))


def get_extensions():
    from collections import defaultdict
    import numpy
    generate_c_docstrings()

    cfg = defaultdict(list)
    cfg['include_dirs'].extend([
        numpy.get_include(),
        os.path.join(LOCALROOT, "include")])
    cfg['sources'] = [
        str(os.path.join(LOCALROOT, 'src', 'synphot_utils.c')),
        str(os.path.join(LOCALROOT, 'src', 'docstrings.c'))]
    cfg = dict((str(key), val) for key, val in cfg.items())

    return [Extension(str('synphot.synphot_utils'), **cfg)]
