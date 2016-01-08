"""
Utilities for working with the Django Storage API.

A lot of these methods assume the use of a storage backend that does not
require leading directories to exist. The default Django file system storage
*will* sometimes require leading directories to exist.
"""

import errno
import os
import shutil

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import smart_str, smart_unicode
from django.utils.functional import SimpleLazyObject

from storages.backends.s3boto import S3BotoStorage
from storages.utils import setting


DEFAULT_CHUNK_SIZE = 64 * 2 ** 10  # 64kB


class LocalFileStorage(FileSystemStorage):
    """Local storage to an unregulated absolute file path.

    Unregulated means that, unlike the default file storage, you can write to
    any path on the system if you have access.

    Unlike Django's default FileSystemStorage, this class behaves more like a
    "cloud" storage system. Specifically, you never have to write defensive
    code that prepares for leading directory paths to exist.
    """

    def __init__(self, base_url=None):
        super(LocalFileStorage, self).__init__(location='/', base_url=base_url)

    def delete(self, name):
        """Delete a file or empty directory path.

        Unlike the default file system storage this will also delete an empty
        directory path. This behavior is more in line with other storage
        systems like S3.
        """
        full_path = self.path(name)
        if os.path.isdir(full_path):
            os.rmdir(full_path)
        else:
            return super(LocalFileStorage, self).delete(name)

    def _open(self, name, mode='rb'):
        # Create directories if the file is opened for writing.
        if any([flag in mode for flag in ['+', 'a', 'w', 'x']]):
            parent = os.path.dirname(self.path(name))
            try:
                # Try/except to prevent race condition raising "File exists".
                os.makedirs(parent)
            except OSError as e:
                if e.errno == errno.EEXIST and os.path.isdir(parent):
                    pass
                else:
                    raise
        return super(LocalFileStorage, self)._open(name, mode=mode)

    def path(self, name):
        """Actual file system path to name without any safety checks."""
        return os.path.normpath(os.path.join(self.location,
                                             self._smart_path(name)))

    def _smart_path(self, string):
        if os.path.supports_unicode_filenames:
            return smart_unicode(string)
        return smart_str(string)


class S3BotoPublicStorage(S3BotoStorage):

    bucket_name = setting('AWS_STORAGE_PUBLIC_BUCKET_NAME')
    default_acl = bucket_acl = 'public-read'
    querystring_auth = False
    querystring_expire = 0
    # Cache all public files for a very long time, we'll change their path or
    # add a query string when we want to bust the cache.
    headers = {
        'Cache-Control': 'max-age=31536000',
    }


class S3BotoPrivateStorage(S3BotoStorage):

    bucket_name = setting('AWS_STORAGE_PRIVATE_BUCKET_NAME')
    default_acl = bucket_acl = 'private'
    querystring_auth = True
    querystring_expire = 300  # Default: 5 minutes.


def get_public_storage():
    if storage_is_remote():
        return S3BotoPublicStorage()
    else:
        return LocalFileStorage()


def get_private_storage():
    if storage_is_remote():
        return S3BotoPrivateStorage()
    else:
        return LocalFileStorage()


local_storage = LocalFileStorage()
public_storage = SimpleLazyObject(get_public_storage)
private_storage = SimpleLazyObject(get_private_storage)


def storage_is_remote():
    return (settings.DEFAULT_FILE_STORAGE !=
            'mkt.site.storage_utils.LocalFileStorage')


def walk_storage(path, topdown=True, onerror=None, followlinks=False,
                 storage=private_storage):
    """
    Generate the file names in a stored directory tree by walking the tree
    top-down.

    For each directory in the tree rooted at the directory top (including top
    itself), it yields a 3-tuple (dirpath, dirnames, filenames).

    This is intended for use with an implementation of the Django storage API.
    You can specify something other than the private storage instance with
    the storage keyword argument.

    """
    if not topdown:
        raise NotImplementedError
    if onerror:
        raise NotImplementedError
    roots = [path]
    while len(roots):
        new_roots = []
        for root in roots:
            dirs, files = storage.listdir(root)
            files = [smart_str(f) for f in files]
            dirs = [smart_str(d) for d in dirs]
            yield root, dirs, files
            for dn in dirs:
                new_roots.append('%s/%s' % (root, dn))
        roots[:] = new_roots


def copy_stored_file(src_path, dst_path, src_storage=private_storage,
                     dst_storage=private_storage):
    """
    Copy a path (src_path) from a storage (src_storage) to a path (dst_path)
    on a different storage (dst_storage).

    Defaults to copying from and to private storage.
    """
    if src_path == dst_path and src_storage.__class__ == dst_storage.__class__:
        return
    with src_storage.open(src_path, 'rb') as src, \
            dst_storage.open(dst_path, 'wb') as dest:
        shutil.copyfileobj(src, dest)


def move_stored_file(src_path, dst_path, src_storage=private_storage,
                     dst_storage=private_storage):
    """
    Move a path (src_path) from a storage (src_storage) to a path (dst_path)
    on a different storage (dst_storage), by copying and then deleting the
    source.

    Defaults to moving from and to private storage.
    """
    copy_stored_file(src_path, dst_path,
                     src_storage=src_storage, dst_storage=dst_storage)
    src_storage.delete(src_path)
