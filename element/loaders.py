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

import os, yaml, re
import codecs
import copy

class NodeLoader(object):
    pass

class LoaderChain(NodeLoader):
    def __init__(self, loaders=None):
        self.loaders = {}
        for loader in loaders or []:
            self.add_loader(loader[0], loader[1])

    def add_loader(self, name, loader):
        self.loaders[name] = loader

    def supports(self, id):
        return True

    def save(self, path, data):
        for name, loader in self.loaders.iteritems():
            if not loader.supports(data):
                continue

            return loader.save(path, data)

    def load(self, data):
        for name, loader in self.loaders.iteritems():
            if not loader.supports(data):
                continue

            return loader.load(data)

class YamlNodeLoader(NodeLoader):
    """
    Load a node by using a yaml definition
    """
    def supports(self, path):
        if isinstance(path, dict):
            return 'type' in path and path['type'] != 'element.static'

        return path[-3:] == 'yml' and os.path.isfile(path)

    def load(self, path):
        meta = codecs.open(path, "r", "utf-8").read()

        data = re.split("(\n|\r\n)----(\n|\r\n)", meta, 1)

        if len(data) > 1:
            meta = data[0]

        node = yaml.load(meta)

        if len(data) > 2:
            node['content'] = data[3]

        return node

    def save(self, path, data):
        data = copy.deepcopy(data)

        content = False

        if 'content' in data:
            content = data['content']
            del data['content']

        data = yaml.safe_dump(data, canonical=False, encoding='utf-8', allow_unicode=True)

        if content:
            file(path, 'w').write(u"%s\n\n----\n%s" % (data, content))
        else:
            file(path, 'w').write(data)

        return True

class InlineLoader(NodeLoader):
    """
    Load a node from content provided
    """
    def supports(self, node):
        return isinstance(node, dict) and 'type' in node and 'id' in node

    def load(self, node):
        return node

    def save(self, id, data):
        return False