#
# Copyright 2014 Thomas Rabaix <thomas.rabaix@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tornado.web import RequestHandler
from tornado.httpserver import HTTPRequest
import jinja2

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

def get_dummy_connection():
    return SubConnection(SubContext('127.0.0.1', 'http'))

class SubRequestHandler(RequestHandler):
    def get_buffer(self):
        return b"".join(self._write_buffer)

class SubConnection(object):
    def __init__(self, context):
        self.context = context

    def set_close_callback(self, callback):
        self.on_connection_close = callback

class SubContext(object):
    def __init__(self, remote_ip, protocol):
        self.remote_ip = remote_ip
        self.protocol = protocol

class Core(object):
    def __init__(self, node_manager, context_creator, dispatcher, application, render_type):
        self.node_manager = node_manager
        self.context_creator = context_creator
        self.dispatcher = dispatcher
        self.application = application
        self.render_type = render_type

    def render_node(self, node, defaults=None):
        defaults = defaults or {}

        # load the node
        node = self.node_manager.get_node(node)

        if not node:
            return jinja2.Markup("<!-- unable to found the node -->")

        # load the related node's handler
        handler = self.node_manager.get_handler(node)

        if not handler:
            return jinja2.Markup("<!-- unable to found the node handler -->")
        
        # build the execution context
        context = self.context_creator.build(node, handler, defaults)

        request_handler = SubRequestHandler(self.application, HTTPRequest('GET', '/_internal', connection=get_dummy_connection()))

        # render the response
        handler.execute(request_handler, context)

        return jinja2.Markup(self.unicode(request_handler.get_buffer()))

    def render_node_event(self, event_name, options=None):
        event = self.dispatcher.dispatch(event_name, options or {})

        if not event.has('node'):
            return jinja2.Markup("<!-- no listener registered for event: %s -->" % event_name)

        return jinja2.Markup(self.unicode(self.render_node(event.get('node'))))

    def render(self, path, type=None):
        if not type:
            type = self.render_type

        if type == 'esi':
            return jinja2.Markup('<esi:include src="%s" />' % path)

        elif type == 'ssi':
            o = urlparse(path)
            return jinja2.Markup('<!--# include virtual="%s?%s&_element=no-debug" -->' % (o.path, o.query))


    def unicode(self, content):
        if isinstance(content, unicode):
            return content

        return content.decode("utf-8")

class ResponseListener(object):
    def __init__(self, templating):
        self.templating = templating

    def handle(self, event):
        result = event.get('result')

        if not isinstance(result, tuple):
            return

        request_handler = event.get('request_handler')

        status_code = 500
        template = None
        params = {}
        headers = {
            'Content-Type': 'text/html; charset=utf-8'
        }

        if len(result) == 3:
            status_code, template, params = result

        if len(result) == 4:
            status_code, template, params, headers = result

        for name, value in headers.iteritems():
            if not request_handler.has_header(name):
                request_handler.set_header(name, value)

        request_handler.set_status(status_code)
        request_handler.write(self.templating.get_template(template).render(params))

        if event.has('node_handler'):
            event.get('node_handler').finalize(request_handler)

        event.set('result', None)