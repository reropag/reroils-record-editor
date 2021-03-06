# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 RERO.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, RERO does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Utilities for reroils-record-editor."""

import copy
import uuid

from flask import current_app, url_for
from invenio_db import db
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record

from .babel_extractors import translate


def get_schema(schema):
    """Return jsonschemas dictionary."""
    ext = current_app.extensions.get('invenio-jsonschemas')
    keys = current_app.config['REROILS_RECORD_EDITOR_TRANSLATE_JSON_KEYS']
    ext.get_schema.cache_clear()
    return translate(ext.get_schema(schema), keys=keys)


def get_schema_url(schema):
    """Return jsonschemas url path."""
    ext = current_app.extensions.get('invenio-jsonschemas')
    return ext.path_to_url(schema)


def resolve(record_type, pid_value):
    """Resolve a pid value for a given record type."""
    config = current_app.config['RECORDS_REST_ENDPOINTS']
    config = config.get(record_type, {})
    pid_type = config.get('pid_type')
    cfg = current_app.config['REROILS_RECORD_EDITOR_OPTIONS'].get(record_type)
    record_class = cfg.get('record_class', Record)
    resolver = Resolver(pid_type=pid_type,
                        object_type='rec',
                        getter=record_class.get_record)
    return resolver.resolve(pid_value)


def delete_record(record_type, pid, record_indexer, parent_pid=None):
    """Remove a record from the db and the index and his corresponding pid."""
    pid, record = resolve(record_type, pid)
    record_indexer().delete(record)
    record_indexer().client.indices.flush()
    record.delete()
    pid.delete()
    db.session.commit()
    _next = url_for('reroils_record_editor.search_%s' % record_type)
    return _next, pid


def save_record(data, record_type, fetcher, minter,
                record_indexer, record_class, parent_pid=None):
    """Save a record into the db and index it."""
    def get_pid(record_type, record, fetcher):
        try:
            pid_value = fetcher(None, record).pid_value
        except KeyError:
            return None
        return pid_value

    # load and clean dirty data provided by angular-schema-form
    record = clean_dict_keys(data)
    pid_value = get_pid(record_type, record, fetcher)
    # update an existing record
    if pid_value:
        pid, rec = resolve(record_type, pid_value)
        rec.update(record)
        rec.commit()
    # create a new record
    else:
        # generate bibid
        uid = uuid.uuid4()
        pid = minter(uid, record)
        # create a new record
        rec = record_class.create(record, id_=uid)

    db.session.commit()

    record_indexer().index(rec)
    record_indexer().client.indices.flush()
    _next = url_for('invenio_records_ui.%s' % record_type,
                    pid_value=pid.pid_value)

    return _next, pid


def clean_dict_keys(data):
    """Remove key having useless values."""
    # retrun a new list with defined value only
    if isinstance(data, list):
        to_return = []
        for item in data:
            tmp = clean_dict_keys(item)
            if tmp:
                to_return.append(tmp)
        return to_return

    # retrun a new dict with defined value only
    if isinstance(data, dict):
        to_return = {}
        for k, v in data.items():
            tmp = clean_dict_keys(v)
            if tmp:
                to_return[k] = tmp
        return to_return

    return data


def remove_pid(editor_options, pid_value):
    """Remove PID in the editor option for new record."""
    for option in reversed(editor_options):
        if isinstance(option, str):
            if option == pid_value:
                editor_options.remove(option)
        if isinstance(option, dict):
            items = option.get('items')
            if option.get('key') == pid_value:
                editor_options.remove(option)
            elif isinstance(items, list):
                new_items = remove_pid(items, pid_value)
                if new_items:
                    option['items'] = new_items
                else:
                    editor_options.remove(option)
        if isinstance(option, list):
            editor_options = remove_pid(option, pid_value)
    return editor_options
