#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 OzzieIsaacs
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

from markupsafe import escape

from flask import Blueprint, jsonify
from .cw_login import current_user
from flask_babel import gettext as _
from flask_babel import format_datetime
from babel.units import format_unit

from . import logger, config, db
from .render_template import render_title_template
from .services.worker import WorkerThread, STAT_WAITING, STAT_FAIL, STAT_STARTED, STAT_FINISH_SUCCESS, STAT_ENDED, \
    STAT_CANCELLED
from .usermanagement import user_login_required

tasks = Blueprint('tasks', __name__)

log = logger.create()


@tasks.route("/ajax/emailstat")
@user_login_required
def get_email_status_json():
    tasks = WorkerThread.get_instance().tasks
    return jsonify(render_task_status(tasks))


@tasks.route("/tasks")
@user_login_required
def get_tasks_status():
    # if current user admin, show all email, otherwise only own emails
    worker_tasks = WorkerThread.get_instance().tasks
    task_data = render_task_status_for_ui(worker_tasks)
    return render_title_template('tasks.html', title=_("Upload & Tasks"), page="upload_tasks",
                                 tasks=task_data['all_tasks'],
                                 processing_tasks=task_data['processing'],
                                 completed_tasks=task_data['completed'],
                                 failed_tasks=task_data['failed'],
                                 processing_count=len(task_data['processing']),
                                 completed_count=len(task_data['completed']),
                                 failed_count=len(task_data['failed']))


# helper function to apply localize status information in tasklist entries
def render_task_status(tasklist):
    rendered_tasklist = list()
    for __, user, __, task, __ in tasklist:
        if user == current_user.name or current_user.role_admin():
            ret = {}
            if task.start_time:
                ret['starttime'] = format_datetime(task.start_time, format='short')
                ret['runtime'] = format_runtime(task.runtime)

            # localize the task status
            if isinstance(task.stat, int):
                if task.stat == STAT_WAITING:
                    ret['status'] = _('Waiting')
                elif task.stat == STAT_FAIL:
                    ret['status'] = _('Failed')
                elif task.stat == STAT_STARTED:
                    ret['status'] = _('Started')
                elif task.stat == STAT_FINISH_SUCCESS:
                    ret['status'] = _('Finished')
                elif task.stat == STAT_ENDED:
                    ret['status'] = _('Ended')
                elif task.stat == STAT_CANCELLED:
                    ret['status'] = _('Cancelled')
                else:
                    ret['status'] = _('Unknown Status')

            ret['taskMessage'] = "{}: {}".format(task.name, task.message) if task.message else task.name
            ret['progress'] = "{} %".format(int(task.progress * 100))
            ret['user'] = escape(user)  # prevent xss

            # Hidden fields
            ret['task_id'] = task.id
            ret['stat'] = task.stat
            ret['is_cancellable'] = task.is_cancellable
            ret['error'] = task.error

            rendered_tasklist.append(ret)

    return rendered_tasklist


def render_task_status_for_ui(tasklist):
    """Render tasks for the new UI with book cover, title, etc."""
    all_tasks = []
    processing = []
    completed = []
    failed = []

    for __, user, __, task, __ in tasklist:
        if user == current_user.name or current_user.role_admin():
            task_obj = {
                'id': task.id,
                'stat': task.stat,
                'is_cancellable': task.is_cancellable,
                'error': task.error,
                'progress': int(task.progress * 100) if task.progress else 0,
                'name': task.name,
                'message': task.message,
            }

            # Get book info if available
            book_id = getattr(task, 'book_id', None)
            cover_url = None
            title = task.name
            book_url = None
            status_text = ''

            if book_id:
                try:
                    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
                    if book:
                        title = book.title
                        cover_url = config.url_for('web.get_cover', book_id=book.id, resolution='cover')
                        book_url = config.url_for('web.show_book', book_id=book.id)
                except Exception:
                    pass

            # Determine status text and category
            if isinstance(task.stat, int):
                if task.stat == STAT_WAITING:
                    status_text = _('Waiting')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'waiting'
                    processing.append(task_obj)
                elif task.stat == STAT_STARTED:
                    status_text = _('Processing')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'processing'
                    processing.append(task_obj)
                elif task.stat == STAT_FINISH_SUCCESS:
                    status_text = _('Completed')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'completed'
                    task_obj['book_url'] = book_url
                    task_obj['cover_url'] = cover_url
                    task_obj['title'] = title
                    completed.append(task_obj)
                elif task.stat == STAT_FAIL:
                    status_text = _('Failed')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'failed'
                    task_obj['error'] = task.error or _('Unknown error')
                    task_obj['cover_url'] = cover_url
                    task_obj['title'] = title
                    failed.append(task_obj)
                elif task.stat == STAT_CANCELLED:
                    status_text = _('Cancelled')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'cancelled'
                    failed.append(task_obj)
                elif task.stat == STAT_ENDED:
                    status_text = _('Ended')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'ended'
                    completed.append(task_obj)
                else:
                    status_text = _('Unknown')
                    task_obj['status_text'] = status_text
                    task_obj['status_class'] = 'unknown'
                    processing.append(task_obj)

            task_obj['cover_url'] = cover_url
            task_obj['title'] = title
            task_obj['book_url'] = book_url

            all_tasks.append(task_obj)

    return {
        'all_tasks': all_tasks,
        'processing': processing,
        'completed': completed,
        'failed': failed
    }


# helper function for displaying the runtime of tasks
def format_runtime(runtime):
    ret_val = ""
    if runtime.days:
        ret_val = format_unit(runtime.days, 'duration-day', length="long") + ', '
    minutes, seconds = divmod(runtime.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    # ToDo: locale.number_symbols._data['timeSeparator'] -> localize time separator ?
    if hours:
        ret_val += '{:d}:{:02d}:{:02d}s'.format(hours, minutes, seconds)
    elif minutes:
        ret_val += '{:2d}:{:02d}s'.format(minutes, seconds)
    else:
        ret_val += '{:2d}s'.format(seconds)
    return ret_val
