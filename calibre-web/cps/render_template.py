# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2020 OzzieIsaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from flask import render_template, g, abort, request
from flask_babel import gettext as _
from werkzeug.local import LocalProxy
from .cw_login import current_user
from sqlalchemy.sql.expression import or_

from . import config, constants, logger, ub
from .ub import User


log = logger.create()

def get_sidebar_config(kwargs=None):
    kwargs = kwargs or []
    simple = bool([e for e in ['kindle', 'tolino', "kobo", "bookeen"]
                   if (e in request.headers.get('User-Agent', "").lower())])
    if 'content' in kwargs:
        content = kwargs['content']
        content = isinstance(content, (User, LocalProxy)) and not content.role_anonymous()
    else:
        content = 'conf' in kwargs

    sidebar = list()

    sidebar.append({"glyph": "home", "text": _('Home'), "link": 'web.index', "id": "home",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "home",
                    "show_text": _('Show Home'), "config_show": False})
    sidebar.append({"glyph": "book-open", "text": _('All Books'), "link": 'web.books_list', "id": "all_books",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "all_books",
                    "show_text": _('Show All Books'), "config_show": True, "data": "newest"})
    sidebar.append({"glyph": "bookmark", "text": _('Continue Reading'), "link": 'web.books_list', "id": "continue_reading",
                    "visibility": constants.SIDEBAR_READ_AND_UNREAD, 'public': (not current_user.is_anonymous),
                    "page": "continue_reading", "show_text": _('Show Continue Reading'), "config_show": content,
                    "sort_param": "reading", "data": "read"})

    sidebar.append({"section": _("BROWSE")})
    sidebar.append({"glyph": "user", "text": _('Authors'), "link": 'web.author_list', "id": "author",
                    "visibility": constants.SIDEBAR_AUTHOR, 'public': True, "page": "author", "no_param": True,
                    "show_text": _('Show Author Section'), "config_show": True})
    sidebar.append({"glyph": "bookmark", "text": _('Series'), "link": 'web.series_list', "id": "series",
                    "visibility": constants.SIDEBAR_SERIES, 'public': True, "page": "series", "no_param": True,
                    "show_text": _('Show Series Section'), "config_show": True})
    sidebar.append({"glyph": "tag", "text": _('Categories'), "link": 'web.category_list', "id": "category",
                    "visibility": constants.SIDEBAR_CATEGORY, 'public': True, "page": "category", "no_param": True,
                    "show_text": _('Show Category Section'), "config_show": True})

    if current_user.is_authenticated or g.allow_anonymous:
        sidebar.append({"section": _("ACTIVITY")})
        sidebar.append({"glyph": "upload", "text": _('Upload & Tasks'), "link": 'tasks.get_tasks_status', "id": "upload_tasks",
                        "visibility": constants.SIDEBAR_DOWNLOAD, 'public': (not current_user.is_anonymous),
                        "page": "upload_tasks", "show_text": _('Show Upload & Tasks'), "config_show": content, "no_param": True})

    if current_user.role_admin():
        sidebar.append({"section": _("SYSTEM")})
        sidebar.append({"glyph": "settings", "text": _('Settings'), "link": 'admin.admin', "id": "settings",
                        "visibility": constants.SIDEBAR_LIST, 'public': current_user.role_admin(),
                        "page": "settings", "show_text": _('Show Settings'), "config_show": content, "no_param": True})
        sidebar.append({"glyph": "monitor", "text": _('UI Preview'), "link": 'web.ui_preview', "id": "ui_preview",
                        "visibility": constants.SIDEBAR_LIST, 'public': current_user.role_admin(),
                        "page": "ui_preview", "show_text": _('Show UI Preview'), "config_show": content, "no_param": True})

    g.shelves_access = ub.session.query(ub.Shelf).filter(
        or_(ub.Shelf.is_public == 1, ub.Shelf.user_id == current_user.id)).order_by(ub.Shelf.name).all()

    return sidebar, simple


# Returns the template for rendering and includes the instance name
def render_title_template(*args, **kwargs):
    sidebar, simple = get_sidebar_config(kwargs)
    try:
        return render_template(instance=config.config_calibre_web_title, sidebar=sidebar, simple=simple,
                               accept=config.config_upload_formats.split(','),
                               *args, **kwargs)
    except PermissionError:
        log.error("No permission to access {} file.".format(args[0]))
        abort(403)
