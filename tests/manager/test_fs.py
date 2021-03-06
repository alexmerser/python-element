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

import unittest
import element.manager.fs
from element.manager import get_uuid
import element.loaders
import element.plugins.static.loader
import os
import shutil
import element.exceptions

class FsManagerTest(unittest.TestCase):     
    def setUp(self):
        self.fixture = "%s/../fixtures/data/" % os.path.dirname(os.path.abspath(__file__))

        if os.path.isdir('%s/tmp' % self.fixture):
            shutil.rmtree('%s/tmp' % self.fixture)

        self.fs = element.manager.fs.FsManager(
            self.fixture, 
            element.loaders.LoaderChain([
                ('yaml', element.loaders.YamlNodeLoader()),
                ('static', element.plugins.static.loader.StaticNodeLoader({
                    'jpg': 'image/jpeg',
                    'png': 'image/png',
                })),
            ])
        )

    def tearDown(self):
        if os.path.isdir('%s/tmp' % self.fixture):
            shutil.rmtree('%s/tmp' % self.fixture)


    def test_build_references(self):
        self.assertEquals(5, len(self.fs.files))

        expected = {
            'eacacfab-74cf-6c8d-5e393165': 'feeds',
            '50093cac-fdc1-5ba6-6f12d44e': 'feeds/all.rss',
            'fca0ea55-c21b-186e-fe6924a5': 'sonata_small.png',
            'c3e6be59-3448-0daa-be2dd043': '2013/my-post-content',
            'fa3b5e88-acfb-fc73-90125d9e': '2013/inline-content',
        }

        self.assertEquals(expected, self.fs.files)

    def test_contains_uuid(self):
        node = self.fs.retrieve("fca0ea55-c21b-186e-fe6924a5")

        self.assertEquals(node['id'], "sonata_small.png")
        self.assertEquals(node['uuid'], "fca0ea55-c21b-186e-fe6924a5")

    def test_retrieve(self):
        node = self.fs.retrieve('fca0ea55-c21b-186e-fe6924a5')

        self.assertEquals(node['id'], "sonata_small.png")
        self.assertEquals(node['uuid'], "fca0ea55-c21b-186e-fe6924a5")

    def test_index(self):
        data = self.fs.find_one(alias="/feeds")
        self.assertIsNotNone(data)
        self.assertEquals(data['path'], 'feeds')

        data = self.fs.find_one(alias="/feeds/_index")
        self.assertIsNotNone(data)
        self.assertEquals(data['path'], 'feeds')


    def test_exists(self):
        self.assertTrue(self.fs.exists('fca0ea55-c21b-186e-fe6924a5'))

    def test_find(self):
        cases = [
            ({}, 5),
            ({'type': 'blog.post'}, 2),
            ({'type': 'fake'}, 0),
            ({'type': 'fake', 'types': ['blog.post']}, 2),
            ({'types': ['blog.post', 'fake']}, 2),
            ({'types': [], 'tags': ['red', 'yellow']}, 2),
            ({'types': [], 'tags': ['red', 'yellow', 'brown']}, 0),
            ({'types': [], 'tags': []}, 5)
        ]

        for kwarg, expected in cases:
            nodes = self.fs.find(**kwarg)
            self.assertEquals(expected, len(nodes))

    def test_private(self):
        cases = [
            ({'path': "/../private"}, 0),
        ]

        for kwarg, expected in cases:
            with self.assertRaises(element.exceptions.SecurityAccessException):
                self.fs.find(**kwarg)

    def test_save_and_delete(self):
        uuid = get_uuid('tmp/simple_save')

        self.assertFalse(self.fs.delete(uuid))
        self.assertTrue(self.fs.save(uuid, {'hello': 'world', 'type': 'mytype', 'path': 'tmp/simple_save'}))
        self.assertTrue(self.fs.delete(uuid))

    def test_save_nested_folder(self):
        self.assertTrue(self.fs.save(None, {'hello': 'world', 'type': 'mytype', 'path': 'tmp/nested/fake'}))

    def test_save_binary_file(self):
        self.assertTrue(self.fs.save(None, {
            'path': 'tmp/foo/image.png',
            'type': 'element.static',
            'content': file("%s/sonata_small.png" % self.fixture, 'r').read()
        }))

        self.assertTrue(os.path.isfile("%s/tmp/foo/image.png" % self.fixture))
