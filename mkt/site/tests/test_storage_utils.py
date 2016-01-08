from functools import partial
import os
import tempfile
import unittest

from django.core.files.base import ContentFile
from django.test.utils import override_settings

import mock
from nose.tools import eq_

from mkt.site.storage_utils import (copy_stored_file, get_private_storage,
                                    get_public_storage, local_storage,
                                    move_stored_file, private_storage,
                                    storage_is_remote, walk_storage)
from mkt.site.tests import TestCase
from mkt.site.utils import rm_local_tmp_dir


def test_storage_walk():
    tmp = tempfile.mkdtemp()
    jn = partial(os.path.join, tmp)
    try:
        private_storage.save(jn('file1.txt'), ContentFile(''))
        private_storage.save(jn('one/file1.txt'), ContentFile(''))
        private_storage.save(jn('one/file2.txt'), ContentFile(''))
        private_storage.save(jn('one/two/file1.txt'), ContentFile(''))
        private_storage.save(jn('one/three/file1.txt'), ContentFile(''))
        private_storage.save(jn('four/five/file1.txt'), ContentFile(''))
        private_storage.save(jn(u'four/kristi\u2603/kristi\u2603.txt'),
                             ContentFile(''))

        results = [(dir, set(subdirs), set(files))
                   for dir, subdirs, files in
                   sorted(walk_storage(tmp, storage=private_storage))]

        yield (eq_, results.pop(0),
               (tmp, set(['four', 'one']), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('four'), set(['five', 'kristi\xe2\x98\x83']), set([])))
        yield (eq_, results.pop(0),
               (jn('four/five'), set([]), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('four/kristi\xe2\x98\x83'), set([]),
                set(['kristi\xe2\x98\x83.txt'])))
        yield (eq_, results.pop(0),
               (jn('one'), set(['three', 'two']),
                set(['file1.txt', 'file2.txt'])))
        yield (eq_, results.pop(0),
               (jn('one/three'), set([]), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('one/two'), set([]), set(['file1.txt'])))
        yield (eq_, len(results), 0)
    finally:
        rm_local_tmp_dir(tmp)


class TestFileOps(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        rm_local_tmp_dir(self.tmp)

    def path(self, path):
        return os.path.join(self.tmp, path)

    def contents(self, path):
        with private_storage.open(path, 'rb') as fp:
            return fp.read()

    def newfile(self, name, contents):
        src = self.path(name)
        private_storage.save(src, ContentFile(contents))
        return src

    def test_copy(self):
        src = self.newfile('src.txt', '<contents>')
        dst = self.path('somedir/dst.txt')
        copy_stored_file(
            src, dst,
            src_storage=private_storage, dst_storage=private_storage)
        eq_(self.contents(dst), '<contents>')

    def test_self_copy(self):
        src = self.newfile('src.txt', '<contents>')
        dst = self.path('src.txt')
        copy_stored_file(
            src, dst,
            src_storage=private_storage, dst_storage=private_storage)
        eq_(self.contents(dst), '<contents>')

    def test_move(self):
        src = self.newfile('src.txt', '<contents>')
        dst = self.path('somedir/dst.txt')
        move_stored_file(
            src, dst,
            src_storage=private_storage, dst_storage=private_storage)
        eq_(self.contents(dst), '<contents>')
        eq_(private_storage.exists(src), False)

    def test_non_ascii(self):
        src = self.newfile(u'kristi\u0107.txt',
                           u'ivan kristi\u0107'.encode('utf8'))
        dst = self.path(u'somedir/kristi\u0107.txt')
        copy_stored_file(
            src, dst,
            src_storage=private_storage, dst_storage=private_storage)
        eq_(self.contents(dst), 'ivan kristi\xc4\x87')


class TestStorageClasses(TestCase):

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.S3BotoPrivateStorage')
    def test_get_storage_remote(self):
        assert storage_is_remote()
        eq_(get_private_storage().__class__.__name__, 'S3BotoPrivateStorage')
        eq_(get_public_storage().__class__.__name__, 'S3BotoPublicStorage')

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    def test_get_storage_local(self):
        assert not storage_is_remote()
        eq_(get_private_storage().__class__.__name__, 'LocalFileStorage')
        eq_(get_public_storage().__class__.__name__, 'LocalFileStorage')

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    @mock.patch('mkt.site.storage_utils.shutil.copyfileobj')
    def test_copy_stored_file_when_local(self, mock):
        tmp = tempfile.mkstemp()[1]
        copy_stored_file(tmp, tmp, src_storage=local_storage,
                         dst_storage=private_storage)
        assert not mock.called
        local_storage.delete(tmp)
