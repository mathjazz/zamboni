# -*- coding: utf-8 -*-
import hashlib
import json
import mock
import os
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import transaction
from django.test.utils import override_settings

from nose.tools import eq_, ok_

from mkt.api.tests.test_oauth import RestOAuth
from mkt.constants import comm
from mkt.constants.apps import MANIFEST_CONTENT_TYPE
from mkt.constants.base import (STATUS_BLOCKED, STATUS_NULL, STATUS_OBSOLETE,
                                STATUS_PENDING, STATUS_PUBLIC, STATUS_REJECTED)
from mkt.extensions.models import Extension, ExtensionVersion
from mkt.extensions.views import ExtensionVersionViewSet
from mkt.files.models import FileUpload
from mkt.files.tests.test_models import UploadTest
from mkt.site.fixtures import fixture
from mkt.site.storage_utils import (local_storage, private_storage,
                                    public_storage)
from mkt.site.tests import ESTestCase, MktPaths, TestCase
from mkt.users.models import UserProfile


class TestExtensionValidationViewSet(MktPaths, RestOAuth):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(TestExtensionValidationViewSet, self).setUp()
        self.list_url = reverse('api-v2:extension-validation-list')
        self.user = UserProfile.objects.get(pk=2519)

    def _test_create_success(self, client):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/zip',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        with open(self.packaged_app_path('extension.zip'), 'rb') as fd:
            contents = fd.read()
            response = client.post(self.list_url, contents,
                                   content_type='application/zip', **headers)
        eq_(response.status_code, 202)
        data = response.json
        eq_(data['valid'], True)
        eq_(data['processed'], True)
        upload = FileUpload.objects.get(pk=data['id'])
        expected_hash = hashlib.sha256(contents).hexdigest()
        eq_(upload.valid, True)  # We directly set uploads as valid atm.
        eq_(upload.name, 'foo.zip')
        eq_(upload.hash, 'sha256:%s' % expected_hash)
        ok_(upload.path)
        ok_(private_storage.exists(upload.path))
        return upload

    def test_create_anonymous(self):
        upload = self._test_create_success(client=self.anon)
        eq_(upload.user, None)

    def test_create_logged_in(self):
        upload = self._test_create_success(client=self.client)
        eq_(upload.user, self.user)

    def test_create_missing_no_data(self):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/zip',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        response = self.anon.post(self.list_url,
                                  content_type='application/zip', **headers)
        eq_(response.status_code, 400)

    def test_cors(self):
        response = self.anon.post(self.list_url)
        self.assertCORS(response, 'get', 'post',
                        headers=['Content-Disposition', 'Content-Type'])

    def test_create_missing_content_disposition(self):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/zip',
        }
        with open(self.packaged_app_path('extension.zip'), 'rb') as fd:
            response = self.client.post(
                self.list_url, fd.read(), content_type='application/zip',
                **headers)
        eq_(response.status_code, 400)

    def test_create_wrong_type(self):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/foobar',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        with open(self.packaged_app_path('extension.zip'), 'rb') as fd:
            response = self.client.post(
                self.list_url, fd.read(), content_type='application/foobar',
                **headers)
        eq_(response.status_code, 400)

    def test_create_invalid_zip(self):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/zip',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        response = self.client.post(
            self.list_url, 'XXXXXX', content_type='application/zip', **headers)
        eq_(response.status_code, 400)

    def test_create_no_manifest_json(self):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/zip',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        # mozball.zip is an app, not an extension, it has no manifest.json.
        with open(self.packaged_app_path('mozball.zip'), 'rb') as fd:
            response = self.client.post(
                self.list_url, fd.read(), content_type='application/zip',
                **headers)
        eq_(response.status_code, 400)

    @mock.patch('mkt.extensions.views.ExtensionValidator.validate')
    def test_validation_called(self, mock_validate):
        headers = {
            'HTTP_CONTENT_TYPE': 'application/foobar',
            'HTTP_CONTENT_DISPOSITION': 'form-data; name="binary_data"; '
                                        'filename="foo.zip"'
        }
        with open(self.packaged_app_path('extension.zip'), 'rb') as fd:
            self.client.post(self.list_url, fd.read(),
                             content_type='application/zip', **headers)
        ok_(mock_validate.called)

    def test_view_result_anonymous(self):
        upload = FileUpload.objects.create(valid=True)
        url = reverse('api-v2:extension-validation-detail',
                      kwargs={'pk': upload.pk})
        response = self.anon.get(url)
        eq_(response.status_code, 200)
        eq_(response.json['valid'], True)


class TestExtensionViewSetPost(UploadTest, RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionViewSetPost, self).setUp()
        self.list_url = reverse('api-v2:extension-list')
        self.user = UserProfile.objects.get(pk=2519)

    def tearDown(self):
        super(TestExtensionViewSetPost, self).tearDown()
        # Explicitely delete the Extensions to clean up leftover files.
        Extension.objects.all().delete()

    def test_create_no_validation_id(self):
        response = self.client.post(self.list_url)
        eq_(response.status_code, 400)

    def test_create_logged_out(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=None)
        eq_(upload.valid, True)
        response = self.anon.post(self.list_url, json.dumps({
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 403)

        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.anon.post(self.list_url, json.dumps({
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 403)

    def _test_success(self):
        def expected_icon_path(size):
            return os.path.join(extension.get_icon_dir(),
                                '%s-%s.png' % (extension.pk, size))

        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url, json.dumps({
            'message': u'add-on has arrivedÄ',
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 201)
        data = response.json

        expected_size = local_storage.size(
            self.packaged_app_path('extension.zip'))
        eq_(data['author'], u'Mozillâ')
        # The extension.zip package has "default_locale": "en_GB".
        eq_(data['description'], {'en-GB': u'A Dummÿ Extension'})
        eq_(data['device_types'], ['firefoxos'])
        eq_(data['disabled'], False)
        eq_(data['last_updated'], None)  # The extension is not public yet.
        eq_(data['latest_version']['size'], expected_size)
        eq_(data['latest_version']['version'], '0.1')
        eq_(data['name'], {'en-GB': u'My Lîttle Extension'})
        eq_(data['slug'], u'my-lîttle-extension')
        eq_(data['status'], 'pending')
        extension = Extension.objects.without_deleted().get(pk=data['id'])
        eq_(extension.default_language, 'en-GB')
        eq_(extension.description, u'A Dummÿ Extension')
        eq_(extension.description.locale, 'en-gb')
        eq_(extension.name, u'My Lîttle Extension')
        eq_(extension.name.locale, 'en-gb')
        eq_(data['uuid'], extension.uuid)
        eq_(extension.status, STATUS_PENDING)
        eq_(list(extension.authors.all()), [self.user])
        ok_(private_storage.exists(expected_icon_path(128)))
        ok_(private_storage.exists(expected_icon_path(64)))
        ok_(extension.icon_hash)
        note = extension.threads.get().notes.get()
        eq_(note.body, u'add-on has arrivedÄ')
        eq_(note.note_type, comm.SUBMISSION)
        return extension

    def test_create_logged_in(self):
        self._test_success()
        eq_(Extension.objects.without_deleted().count(), 1)
        eq_(ExtensionVersion.objects.without_deleted().count(), 1)

    def test_create_logged_in_with_lang(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url, json.dumps({
            'lang': 'es',  # Ignored. Only the lang inside the package matters.
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 201)
        data = response.json

        eq_(data['author'], u'Mozillâ')
        # The extension.zip package has "default_locale": "en_GB".
        eq_(data['description'], {'en-GB': u'A Dummÿ Extension'})
        eq_(data['name'], {'en-GB': u'My Lîttle Extension'})
        extension = Extension.objects.without_deleted().get(pk=data['id'])
        eq_(extension.default_language, 'en-GB')
        eq_(extension.description.locale, 'en-gb')
        eq_(extension.name.locale, 'en-gb')

    def test_create_logged_in_name_already_exists(self):
        # "My Lîttle Extension" is the name inside the test package. That
        # name is in en-GB language.
        self.user.extension_set.create(
            default_language='en-GB',
            name={'en-GB': u'My Lîttle Extension'}, slug='dummy-addon')
        eq_(Extension.objects.count(), 1)
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url, json.dumps({
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 400)
        eq_(Extension.objects.count(), 1)

    def test_create_upload_has_no_user(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=None)
        response = self.client.post(
            self.list_url, json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 404)

    def test_create_upload_has_wrong_user(self):
        second_user = UserProfile.objects.get(pk=999)
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=second_user)
        response = self.client.post(
            self.list_url, json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 404)

    def test_invalid_pk(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(
            self.list_url, json.dumps({'validation_id': upload.pk + 'lol'}))
        eq_(response.status_code, 404)

    def test_not_validated(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user,
            validation=json.dumps({'errors': 1}))
        response = self.client.post(self.list_url,
                                    json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 400)

    def test_not_an_addon(self):
        upload = self.get_upload(
            abspath=self.packaged_app_path('mozball.zip'), user=self.user)
        response = self.client.post(
            self.list_url, json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 400)
        eq_(u'NO_MANIFEST', response.json['detail']['key'])


class TestExtensionViewSetDelete(RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionViewSetDelete, self).setUp()
        self.extension = Extension.objects.create()
        self.other_extension = Extension.objects.create()
        self.user = UserProfile.objects.get(pk=2519)
        self.other_user = UserProfile.objects.get(pk=999)
        self.detail_url = reverse(
            'api-v2:extension-detail', kwargs={'pk': self.extension.slug})

    def test_delete_logged_in_has_rights(self):
        eq_(Extension.objects.without_deleted().count(), 2)
        self.extension.authors.add(self.user)
        response = self.client.delete(self.detail_url)
        eq_(response.status_code, 204)
        eq_(Extension.objects.without_deleted().count(), 1)
        ok_(not Extension.objects.without_deleted().filter(
            pk=self.extension.pk).exists())
        ok_(Extension.objects.without_deleted().filter(
            pk=self.other_extension.pk).exists())

    def test_delete_logged_in_no_rights(self):
        self.extension.authors.add(self.other_user)
        response = self.client.delete(self.detail_url)
        eq_(response.status_code, 403)
        eq_(Extension.objects.without_deleted().count(), 2)

    def test_delete_anonymous_no_rights(self):
        response = self.anon.delete(self.detail_url)
        eq_(response.status_code, 403)
        eq_(Extension.objects.without_deleted().count(), 2)

    def test_delete__404(self):
        self.detail_url = reverse(
            'api-v2:extension-detail', kwargs={'pk': self.extension.pk + 666})
        response = self.client.delete(self.detail_url)
        eq_(response.status_code, 404)
        eq_(Extension.objects.without_deleted().count(), 2)


class TestExtensionViewSetPostAction(UploadTest, RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionViewSetPostAction, self).setUp()
        self.extension = Extension.objects.create()
        self.user = UserProfile.objects.get(pk=2519)
        self.block_url = reverse(
            'api-v2:extension-block', kwargs={'pk': self.extension.slug})
        self.unblock_url = reverse(
            'api-v2:extension-unblock', kwargs={'pk': self.extension.slug})

    def test_cors(self):
        self.grant_permission(self.user, 'Admin:%')
        self.assertCORS(self.client.post(self.block_url), 'post')
        self.assertCORS(self.client.post(self.unblock_url), 'post')

    def test_block_unblock_reviewer(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.post(self.block_url)
        eq_(response.status_code, 403)

        response = self.client.post(self.unblock_url)
        eq_(response.status_code, 403)

    def test_block_unblock_anonymous(self):
        response = self.anon.post(self.block_url)
        eq_(response.status_code, 403)

        response = self.anon.post(self.unblock_url)
        eq_(response.status_code, 403)

    def test_block_unblock_author(self):
        self.extension.authors.add(self.user)
        response = self.client.post(self.block_url)
        eq_(response.status_code, 403)

        response = self.client.post(self.unblock_url)
        eq_(response.status_code, 403)

    def test_block(self):
        self.grant_permission(self.user, 'Admin:%')
        response = self.client.post(self.block_url)
        eq_(response.status_code, 202)
        self.extension.reload()
        eq_(self.extension.status, STATUS_BLOCKED)

    def test_unblock(self):
        self.grant_permission(self.user, 'Admin:%')
        response = self.client.post(self.unblock_url)
        eq_(response.status_code, 202)
        self.extension.reload()
        eq_(self.extension.status, STATUS_NULL)


class TestExtensionViewSetGet(RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionViewSetGet, self).setUp()
        self.list_url = reverse('api-v2:extension-list')
        self.user = UserProfile.objects.get(pk=2519)
        self.user2 = UserProfile.objects.get(pk=999)
        self.extension = Extension.objects.create(
            author=u'My Favourité Author',
            description=u'Mÿ Extension Description', icon_hash='654321',
            name=u'Mŷ Extension')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, size=4242, status=STATUS_PENDING,
            version='0.42')
        self.extension.authors.add(self.user)
        self.extension2 = Extension.objects.create(name=u'NOT Mŷ Extension')
        ExtensionVersion.objects.create(
            extension=self.extension2, status=STATUS_PENDING, version='0.a1')
        self.extension2.authors.add(self.user2)
        self.deleted_extension = Extension.objects.create(
            deleted=True, name=u'Mŷ Deleted Extension',
            description=u'Mÿ Deleted Extension Description')
        ExtensionVersion.objects.create(
            extension=self.deleted_extension, size=142, status=STATUS_PUBLIC,
            version='1.4.2')
        self.deleted_extension.authors.add(self.user)
        self.url = reverse('api-v2:extension-detail',
                           kwargs={'pk': self.extension.pk})
        self.url2 = reverse('api-v2:extension-detail',
                            kwargs={'pk': self.extension2.pk})
        self.deleted_url = reverse('api-v2:extension-detail',
                                   kwargs={'pk': self.deleted_extension.pk})

    def test_has_cors(self):
        self.assertCORS(
            self.anon.get(self.list_url),
            'get', 'patch', 'put', 'post', 'delete')
        self.assertCORS(
            self.anon.get(self.url),
            'get', 'patch', 'put', 'post', 'delete')

    def test_list_anonymous(self):
        response = self.anon.get(self.list_url)
        eq_(response.status_code, 403)

    def test_list_logged_in(self):
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        meta = response.json['meta']
        # Only one extension is returned, the only non-public extension that
        # belongs to self.user.
        eq_(meta['total_count'], 1)
        eq_(len(response.json['objects']), 1)
        data = response.json['objects'][0]
        eq_(data['id'], self.extension.id)
        eq_(data['author'], self.extension.author)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['device_types'], ['firefoxos'])
        eq_(data['disabled'], False)
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        eq_(data['last_updated'], None)  # The extension is not public yet.
        eq_(data['latest_version']['download_url'],
            self.version.download_url)
        eq_(data['latest_version']['unsigned_download_url'],
            self.version.unsigned_download_url)
        eq_(data['latest_version']['version'], self.version.version)
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        eq_(data['status'], 'pending')
        eq_(data['uuid'], self.extension.uuid)

    def test_detail_anonymous(self):
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

        self.version.update(status=STATUS_PUBLIC)
        self.extension.update(last_updated=datetime.now())
        response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.extension.id)
        eq_(data['author'], self.extension.author)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['disabled'], False)
        eq_(data['device_types'], ['firefoxos'])
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        self.assertCloseToNow(data['last_updated'])
        eq_(data['latest_version']['download_url'],
            self.version.download_url)
        eq_(data['latest_version']['size'], self.version.size)
        eq_(data['latest_version']['unsigned_download_url'],
            self.version.unsigned_download_url)
        eq_(data['latest_version']['version'], self.version.version)
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        eq_(data['status'], 'public')
        eq_(data['uuid'], self.extension.uuid)

    def test_detail_deleted(self):
        response = self.anon.get(self.deleted_url)
        eq_(response.status_code, 404)

        response = self.client.get(self.deleted_url)
        eq_(response.status_code, 404)

    def test_detail_anonymous_disabled(self):
        self.version.update(status=STATUS_PUBLIC)
        self.extension.update(disabled=True)
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

    def test_detail_anonymous_rejected(self):
        self.version.update(status=STATUS_REJECTED)
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

    def test_detail_with_slug(self):
        self.url = reverse('api-v2:extension-detail',
                           kwargs={'pk': self.extension.slug})
        self.test_detail_anonymous()

    def test_detail_logged_in(self):
        response = self.client.get(self.url2)
        eq_(response.status_code, 403)

        # user is the owner, he can access the extension even if it's not
        # public.
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.extension.id)
        eq_(data['author'], self.extension.author)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['device_types'], ['firefoxos'])
        eq_(data['disabled'], False)
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        eq_(data['last_updated'], None)  # The extension is not public yet.
        eq_(data['latest_version']['download_url'],
            self.version.download_url)
        eq_(data['latest_version']['size'], self.version.size)
        eq_(data['latest_version']['unsigned_download_url'],
            self.version.unsigned_download_url)
        eq_(data['latest_version']['version'], self.version.version)
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        eq_(data['status'], 'pending')
        eq_(data['uuid'], self.extension.uuid)

        # Even works if disabled.
        self.extension.update(disabled=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.extension.id)
        eq_(data['disabled'], True)

    def test_detail_anonymous_or_not_owner_blocked(self):
        self.extension.update(status=STATUS_BLOCKED)
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

        self.extension.authors.remove(self.user)
        self.extension.update(status=STATUS_BLOCKED)
        response = self.client.get(self.url)
        eq_(response.status_code, 403)

    def test_detail_owner_blocked(self):
        self.extension.update(status=STATUS_BLOCKED)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.extension.pk)
        eq_(data['status'], 'blocked')

    def test_detail_owner_rejected(self):
        self.version.update(status=STATUS_REJECTED)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.extension.pk)
        eq_(data['status'], 'rejected')


class TestExtensionViewSetPatchPut(RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionViewSetPatchPut, self).setUp()
        self.user = UserProfile.objects.get(pk=2519)
        self.user2 = UserProfile.objects.get(pk=999)
        self.extension = Extension.objects.create(
            author=u'I, Âuthor', description=u'Mÿ Extension Description',
            name=u'Mŷ Extension', slug=u'mŷ-extension')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, size=4343, status=STATUS_PUBLIC,
            version='0.43')
        self.url = reverse('api-v2:extension-detail',
                           kwargs={'pk': self.extension.pk})

    def test_put(self):
        self.extension.authors.add(self.user)
        response = self.client.put(self.url, json.dumps({'slug': 'lol'}))
        eq_(response.status_code, 405)

    def test_patch_deleted(self):
        self.extension.update(deleted=True)
        self.extension.authors.add(self.user)
        response = self.client.patch(self.url, json.dumps({
            'slug': u'lolé', 'disabled': True}))
        eq_(response.status_code, 404)
        self.extension.reload()
        eq_(self.extension.deleted, True)
        eq_(self.extension.disabled, False)
        eq_(self.extension.slug, u'mŷ-extension')

    def test_patch_owner_blocked(self):
        self.extension.authors.add(self.user)
        self.extension.update(status=STATUS_BLOCKED)
        response = self.client.patch(self.url, json.dumps({
            'slug': u'lolé', 'disabled': True}))
        eq_(response.status_code, 403)

    def test_patch_without_rights(self):
        response = self.anon.patch(self.url, json.dumps({'slug': 'lol'}))
        eq_(response.status_code, 403)
        response = self.client.patch(self.url, json.dumps({'slug': 'lol'}))
        eq_(response.status_code, 403)
        eq_(self.extension.reload().slug, u'mŷ-extension')

    def test_patch_with_rights(self):
        self.extension.authors.add(self.user)
        response = self.client.patch(self.url, json.dumps({
            'slug': u'lolé', 'disabled': True}))
        eq_(response.status_code, 200)
        eq_(response.json['slug'], u'lolé')
        eq_(response.json['disabled'], True)
        self.extension.reload()
        eq_(self.extension.disabled, True)
        eq_(self.extension.slug, u'lolé')

    def test_patch_with_rights_with_slug(self):
        # Changes to the slug are made even if you used the slug in the URL.
        self.url = reverse('api-v2:extension-detail',
                           kwargs={'pk': self.extension.slug})
        self.extension.authors.add(self.user)
        response = self.client.patch(self.url, json.dumps({'slug': u'làlé'}))
        eq_(response.status_code, 200)
        eq_(response.json['slug'], u'làlé')
        eq_(response.json['disabled'], False)
        self.extension.reload()
        eq_(self.extension.disabled, False)
        eq_(self.extension.slug, u'làlé')

    def test_patch_slug_not_available(self):
        Extension.objects.create(slug=u'sorrŷ-already-taken')
        self.extension.authors.add(self.user)
        response = self.client.patch(self.url, json.dumps({
            'slug': u'sorrŷ-already-taken', 'disabled': True}))
        eq_(response.status_code, 400)
        self.extension.reload()
        eq_(self.extension.disabled, False)
        eq_(self.extension.slug, u'mŷ-extension')

    def test_patch_non_editable_fields(self):
        self.extension.authors.add(self.user)
        self.extension.update(status=STATUS_PENDING)
        response = self.client.patch(self.url, json.dumps({
            'author': u'Aaaarr', 'description': u'Désccc', 'name': u'Nàmeee',
            'status': 'public'}))
        # We don't reject PATCH when it tries to modify read-only or
        # non-existent properties atm, we just ignore them, so it's a 200.
        eq_(response.status_code, 200)
        self.extension.reload()
        # The fields should not have changed:
        eq_(self.extension.author, u'I, Âuthor')
        eq_(self.extension.description, u'Mÿ Extension Description')
        eq_(self.extension.name, u'Mŷ Extension')
        eq_(self.extension.status, STATUS_PENDING)
        eq_(response.json['author'], self.extension.author)
        eq_(response.json['description'],
            {'en-US': self.extension.description})
        eq_(response.json['name'],
            {'en-US': self.extension.name})
        eq_(response.json['status'], 'pending')


class TestExtensionSearchView(RestOAuth, ESTestCase):
    fixtures = fixture('user_2519')

    def setUp(self):
        self.last_updated_date = datetime.now()
        self.extension = Extension.objects.create(
            author=u'MäÄägnificent Author',
            description=u'Mâgnificent Extension Description',
            icon_hash='abcdef',
            name=u'Mâgnificent Extension',
            last_updated=self.last_updated_date)
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, reviewed=self.days_ago(7),
            size=333, status=STATUS_PUBLIC, version='1.0.0')
        self.url = reverse('api-v2:extension-search')
        super(TestExtensionSearchView, self).setUp()
        self.refresh('extension')

    def tearDown(self):
        Extension.get_indexer().unindexer(_all=True)
        super(TestExtensionSearchView, self).tearDown()

    def test_verbs(self):
        self._allowed_verbs(self.url, ['get'])

    def test_has_cors(self):
        self.assertCORS(self.anon.get(self.url), 'get')

    def test_basic(self):
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)
        data = response.json['objects'][0]
        eq_(data['id'], self.extension.id)
        eq_(data['author'], self.extension.author)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['disabled'], False)
        eq_(data['device_types'], ['firefoxos'])
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        self.assertCloseToNow(data['last_updated'], now=self.last_updated_date)
        eq_(data['latest_public_version']['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['latest_public_version']['download_url'],
            self.version.download_url)
        eq_(data['latest_public_version']['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['latest_public_version']['size'], self.version.size)
        eq_(data['latest_public_version']['unsigned_download_url'],
            self.version.unsigned_download_url)
        eq_(data['latest_public_version']['version'], self.version.version)
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        eq_(data['status'], 'public')
        eq_(data['uuid'], self.extension.uuid)

    def test_list(self):
        self.extension2 = Extension.objects.create(name=u'Mŷ Second Extension')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, status=STATUS_PUBLIC, version='1.2.3')
        self.refresh('extension')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 2)

    def test_query(self):
        self.extension2 = Extension.objects.create(name=u'Superb Extensiôn')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        with self.assertNumQueries(0):
            res = self.anon.get(self.url, data={'q': 'superb'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 1)
        eq_(objs[0]['id'], self.extension2.pk)

    def test_q_num_requests(self):
        es = Extension.get_indexer().get_es()
        orig_search = es.search
        es.counter = 0

        def monkey_search(*args, **kwargs):
            es.counter += 1
            return orig_search(*args, **kwargs)

        es.search = monkey_search

        with self.assertNumQueries(0):
            res = self.anon.get(self.url, data={'q': 'extension'})
        eq_(res.status_code, 200)
        eq_(res.json['meta']['total_count'], 1)
        eq_(len(res.json['objects']), 1)

        # Verify only one search call was made.
        eq_(es.counter, 1)

        es.search = orig_search

    def test_query_sort_reviewed(self):
        self.extension2 = Extension.objects.create(name=u'Superb Extensiôn')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, reviewed=self.days_ago(0),
            status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        with self.assertNumQueries(0):
            res = self.anon.get(
                self.url, data={'q': 'extension', 'sort': 'reviewed'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 2)
        eq_(objs[0]['id'], self.extension2.pk)
        eq_(objs[1]['id'], self.extension.pk)

    def test_query_sort_relevance(self):
        self.extension2 = Extension.objects.create(
            name=u'Superb Extensiôn', slug='superb-lol')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, reviewed=self.days_ago(0),
            status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        with self.assertNumQueries(0):
            res = self.anon.get(self.url, data={'q': 'extension'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 2)
        eq_(objs[0]['id'], self.extension.pk)
        eq_(objs[1]['id'], self.extension2.pk)

    def test_query_no_results(self):
        with self.assertNumQueries(0):
            res = self.anon.get(self.url, data={'q': 'something'})
        eq_(res.status_code, 200)
        eq_(res.json['objects'], [])

    def test_not_public(self):
        self.extension.update(status=STATUS_PENDING)
        self.refresh('extension')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_disabled(self):
        self.extension.update(disabled=True)
        self.refresh('extension')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_blocked(self):
        self.extension.update(status=STATUS_BLOCKED)
        self.refresh('extension')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_deleted(self):
        self.extension.update(deleted=True)
        self.refresh('extension')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_search_author(self):
        self.extension2 = Extension.objects.create(
            author=u"Another Author", description="Another Description",
            name=u'Another Extensiôn', slug='another-extension')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, reviewed=self.days_ago(0),
            status=STATUS_PUBLIC, version='7.8.9')
        self.refresh('extension')
        # Test client wants utf-8 encoded strings for params, not unicode
        # objects.
        author = self.extension.author.encode('utf-8')
        with self.assertNumQueries(0):
            response = self.anon.get(self.url, data={'author': author})
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)
        eq_(response.json['objects'][0]['id'], self.extension.pk)


class TestReviewerExtensionSearchView(RestOAuth, ESTestCase):
    fixtures = fixture('user_2519')

    def setUp(self):
        self.user = UserProfile.objects.get()
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.last_updated_date = datetime.now()
        self.extension = Extension.objects.create(
            author=u'MäÄägnificent Author',
            description=u'Mâgnificent Extension Description',
            name=u'Mâgnificent Extension',
            last_updated=self.last_updated_date)
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, reviewed=self.days_ago(7),
            size=333, status=STATUS_PUBLIC, version='1.0.0')
        self.url = reverse('api-v2:extension-search-reviewers')
        super(TestReviewerExtensionSearchView, self).setUp()
        self.refresh('extension')

    def tearDown(self):
        Extension.get_indexer().unindexer(_all=True)
        super(TestReviewerExtensionSearchView, self).tearDown()

    def test_verbs(self):
        self._allowed_verbs(self.url, ['get'])

    def test_has_cors(self):
        with transaction.atomic():
            self.assertCORS(self.anon.get(self.url), 'get')

    def test_basic(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_anon(self):
        with transaction.atomic():
            response = self.anon.get(self.url)
            eq_(response.status_code, 403)

    def test_user_no_perm(self):
        with transaction.atomic():
            self.user.groups.all().delete()
            response = self.client.get(self.url)
            eq_(response.status_code, 403)

    def test_list(self):
        self.extension2 = Extension.objects.create(name=u'Mŷ Second Extension')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, status=STATUS_PUBLIC, version='1.2.3')
        self.refresh('extension')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 2)

    def test_query(self):
        self.extension2 = Extension.objects.create(name=u'Superb Extensiôn')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        res = self.client.get(self.url, data={'q': 'superb'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 1)
        eq_(objs[0]['id'], self.extension2.pk)

    def test_query_sort_reviewed(self):
        self.extension2 = Extension.objects.create(name=u'Superb Extensiôn')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, reviewed=self.days_ago(0),
            status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        res = self.client.get(
            self.url, data={'q': 'extension', 'sort': 'reviewed'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 2)
        eq_(objs[0]['id'], self.extension2.pk)
        eq_(objs[1]['id'], self.extension.pk)

    def test_query_sort_relevance(self):
        self.extension2 = Extension.objects.create(
            name=u'Superb Extensiôn', slug='superb-lol')
        self.version2 = ExtensionVersion.objects.create(
            extension=self.extension2, reviewed=self.days_ago(0),
            status=STATUS_PUBLIC, version='4.5.6')
        self.refresh('extension')
        res = self.client.get(self.url, data={'q': 'extension'})
        eq_(res.status_code, 200)
        objs = res.json['objects']
        eq_(len(objs), 2)
        eq_(objs[0]['id'], self.extension.pk)
        eq_(objs[1]['id'], self.extension2.pk)

    def test_query_no_results(self):
        res = self.client.get(self.url, data={'q': 'something'})
        eq_(res.status_code, 200)
        eq_(res.json['objects'], [])

    def test_not_public(self):
        self.extension.update(status=STATUS_PENDING)
        self.refresh('extension')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_blocked(self):
        self.extension.update(status=STATUS_BLOCKED)
        self.refresh('extension')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_disabled(self):
        self.extension.update(disabled=True)
        self.refresh('extension')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_deleted(self):
        self.extension.update(deleted=True)
        self.refresh('extension')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        # We want to show deleted add-ons in reviewer search.
        eq_(len(response.json['objects']), 1)


class ReviewQueueTestMixin(object):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(ReviewQueueTestMixin, self).setUp()
        self.user = UserProfile.objects.get(pk=2519)

        another_extension = Extension.objects.create(
            name=u'Anothër Extension', description=u'Anothër Description',
            icon_hash='fdecba')
        ExtensionVersion.objects.create(
            extension=another_extension, size=888, status=STATUS_PUBLIC,
            version='0.1')

    def test_has_cors(self):
        self.assertCORS(self.anon.get(self.list_url), 'get', 'post')

    def test_list_anonymous(self):
        response = self.anon.get(self.list_url)
        eq_(response.status_code, 403)

    def test_list_logged_in_no_rights(self):
        response = self.client.get(self.list_url)
        eq_(response.status_code, 403)

    def test_list_logged_in_with_rights_status(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_list_logged_in_with_rights_deleted(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        # Deleted extensions do not show up in the review queue.
        self.extension.update(deleted=True)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_list_logged_in_with_rights_disabled(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        # Disabled extensions do not show up in the review queue.
        self.extension.update(disabled=True)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_list_logged_in_with_rights(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        data = response.json['objects'][0]
        eq_(data['id'], self.extension.id)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['disabled'], False)
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        eq_(data['last_updated'], None)  # The extension is not public yet.
        ok_(data['latest_version'])
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        ok_(data['status'])
        eq_(data['uuid'], self.extension.uuid)
        return data


class TestReviewerExtensionViewSet(ReviewQueueTestMixin, RestOAuth):

    def setUp(self):
        super(TestReviewerExtensionViewSet, self).setUp()
        self.list_url = reverse('api-v2:extension-queue-list')
        self.extension = Extension.objects.create(
            name=u'Än Extension', description=u'Än Extension Description',
            icon_hash='123456')
        self.version = ExtensionVersion.objects.create(
            status=STATUS_PENDING, extension=self.extension, size=999,
            version='48.1516.2342')
        self.extension.update(status=STATUS_PENDING)
        self.url = reverse('api-v2:extension-queue-detail',
                           kwargs={'pk': self.extension.pk})

    def test_detail_has_cors(self):
        self.assertCORS(self.anon.get(self.url), 'get', 'post')

    def test_detail_anonymous(self):
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

    def test_detail_logged_in_no_rights(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 403)

    def test_list_logged_in_with_rights(self):
        data = super(TestReviewerExtensionViewSet,
                     self).test_list_logged_in_with_rights()
        eq_(data['status'], 'pending')

    def test_detail_logged_in_with_rights_status_public(self):
        self.version.update(status=STATUS_PUBLIC)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_logged_in_with_rights(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        version = self.version
        expected_data_version = {
            'id': version.pk,
            'created': version.created.replace(microsecond=0).isoformat(),
            'download_url': version.download_url,
            'reviewer_mini_manifest_url': version.reviewer_mini_manifest_url,
            'size': 999,
            'status': 'pending',
            'unsigned_download_url': version.unsigned_download_url,
            'version': version.version
        }
        eq_(data['id'], self.extension.id)
        eq_(data['description'], {'en-US': self.extension.description})
        eq_(data['disabled'], False)
        eq_(data['icons'], {
            '64': self.extension.get_icon_url(64),
            '128': self.extension.get_icon_url(128),
        })
        eq_(data['last_updated'], None)  # The extension is not public yet.
        eq_(data['latest_public_version'], None)
        eq_(data['latest_version'], expected_data_version)
        eq_(data['mini_manifest_url'], self.extension.mini_manifest_url)
        eq_(data['name'], {'en-US': self.extension.name})
        eq_(data['slug'], self.extension.slug)
        eq_(data['status'], 'pending')
        eq_(data['uuid'], self.extension.uuid)

    def test_detail_with_slug(self):
        self.url = reverse('api-v2:extension-queue-detail',
                           kwargs={'pk': self.extension.slug})
        self.test_detail_logged_in_with_rights()

    def test_detail_logged_in_with_rights_deleted(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        # Deleted extensions do not show up in the review queue.
        self.extension.update(deleted=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_logged_in_with_rights_disabled(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        # Disabled extensions do not show up in the review queue.
        self.extension.update(disabled=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)


class TestReviewerExtensionViewSetUpdates(ReviewQueueTestMixin, RestOAuth):

    def setUp(self):
        super(TestReviewerExtensionViewSetUpdates, self).setUp()
        self.list_url = reverse('api-v2:extension-queue-updates')
        self.extension = Extension.objects.create(
            status=STATUS_PUBLIC, name=u'Än Extension',
            description=u'Än Extension Description')
        ExtensionVersion.objects.create(
            extension=self.extension, size=999, status=STATUS_PUBLIC,
            version='48.1516.2342')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, size=999, status=STATUS_PENDING,
            version='48.1516.2352')
        self.extension.update(status=STATUS_PUBLIC)

    def test_list_logged_in_with_rights(self):
        data = super(TestReviewerExtensionViewSetUpdates,
                     self).test_list_logged_in_with_rights()
        # Extension is public, latest_version is pending.
        eq_(data['status'], 'public')


class TestExtensionVersionViewSetGet(RestOAuth):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(TestExtensionVersionViewSetGet, self).setUp()
        self.user = UserProfile.objects.get(pk=2519)
        self.extension = Extension.objects.create(name=u'Än Extension')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, status=STATUS_PENDING,
            version='4815.1623.42')
        self.list_url = reverse('api-v2:extension-version-list', kwargs={
            'extension_pk': self.extension.pk})
        self.url = reverse('api-v2:extension-version-detail', kwargs={
            'extension_pk': self.extension.pk, 'pk': self.version.pk})

    def test_has_cors(self):
        self.assertCORS(self.anon.options(self.list_url),
                        'get', 'patch', 'put', 'post', 'delete')
        self.assertCORS(self.anon.options(self.url),
                        'get', 'patch', 'put', 'post', 'delete')

    def test_get_extension_object(self):
        # This is an internal method we're testing. self.kwargs['extension_id']
        # should never be absent if everything is properly configured, so we
        # have to manually instantiate the view to test it.
        viewset = ExtensionVersionViewSet()
        viewset.kwargs = {}
        with self.assertRaises(ImproperlyConfigured):
            viewset.get_extension_object()

    def test_get_non_existing_extension(self):
        self.extension.authors.add(self.user)
        self.list_url = reverse('api-v2:extension-version-list', kwargs={
            'extension_pk': self.extension.pk + 42})
        self.url = reverse('api-v2:extension-version-detail', kwargs={
            'extension_pk': self.extension.pk + 42, 'pk': self.version.pk})
        self.url2 = reverse('api-v2:extension-version-detail', kwargs={
            'extension_pk': self.extension.pk, 'pk': self.version.pk + 42})
        response = self.client.get(self.list_url)
        eq_(response.status_code, 404)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)
        response = self.client.get(self.url2)
        eq_(response.status_code, 404)

    def test_detail_anonymous(self):
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)
        self.version.update(status=STATUS_PUBLIC)
        response = self.anon.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['status'], 'public')
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_detail_anonymous_disabled(self):
        self.version.update(status=STATUS_PUBLIC)
        self.extension.update(disabled=True)
        response = self.anon.get(self.url)
        eq_(response.status_code, 403)

    def test_detail_anonymous_deleted(self):
        self.version.update(status=STATUS_PUBLIC)
        self.extension.update(deleted=True)
        response = self.anon.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_logged_in_no_rights(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 403)
        self.version.update(status=STATUS_PUBLIC)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['status'], 'public')
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_detail_logged_in_deleted(self):
        self.version.update(status=STATUS_PUBLIC)
        self.extension.update(deleted=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_logged_in_no_rights_version_deleted(self):
        self.version.update(status=STATUS_PUBLIC, deleted=True)
        # Force the extension to be public for this test (since the version is
        # deleted it needs the extra help to be public).
        self.extension.update(status=STATUS_PUBLIC)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_list_anonymous(self):
        response = self.anon.get(self.list_url)
        eq_(response.status_code, 403)
        self.version.update(status=STATUS_PUBLIC)
        response = self.anon.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)
        data = response.json['objects'][0]
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['status'], 'public')
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_list_logged_in_no_rights(self):
        response = self.client.get(self.list_url)
        eq_(response.status_code, 403)
        self.version.update(status=STATUS_PUBLIC)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)
        data = response.json['objects'][0]
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['status'], 'public')
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_list_logged_in_no_rights_deleted(self):
        self.version.update(status=STATUS_PUBLIC, deleted=True)
        # Force the extension to be public for this test (since the version is
        # deleted it needs the extra help to be public).
        self.extension.update(status=STATUS_PUBLIC)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_list_owner(self):
        self.extension.authors.add(self.user)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)
        data = response.json['objects'][0]
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['status'], 'pending')
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_list_owner_disabled(self):
        self.extension.authors.add(self.user)
        self.extension.update(disabled=True)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 1)

    def test_list_owner_deleted(self):
        self.extension.authors.add(self.user)
        self.extension.update(deleted=True)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 404)

    def test_list_owner_version_deleted(self):
        self.extension.authors.add(self.user)
        self.version.update(deleted=True)
        response = self.client.get(self.list_url)
        eq_(response.status_code, 200)
        eq_(len(response.json['objects']), 0)

    def test_detail_owner_disabled(self):
        self.extension.authors.add(self.user)
        self.extension.update(disabled=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.version.pk)

    def test_detail_owner_deleted(self):
        self.extension.authors.add(self.user)
        self.extension.update(deleted=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_owner_version_deleted(self):
        self.extension.authors.add(self.user)
        self.version.update(deleted=True)
        response = self.client.get(self.url)
        eq_(response.status_code, 404)

    def test_detail_owner(self):
        self.extension.authors.add(self.user)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.version.pk)
        eq_(data['created'],
            self.version.created.replace(microsecond=0).isoformat())
        eq_(data['download_url'], self.version.download_url)
        eq_(data['reviewer_mini_manifest_url'],
            self.version.reviewer_mini_manifest_url)
        eq_(data['status'], 'pending')
        eq_(data['unsigned_download_url'], self.version.unsigned_download_url)
        eq_(data['version'], self.version.version)

    def test_detail_owner_obsolete(self):
        self.version.update(status=STATUS_OBSOLETE)
        self.extension.authors.add(self.user)
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        data = response.json
        eq_(data['id'], self.version.pk)
        eq_(data['status'], 'obsolete')


class TestExtensionVersionViewSetPost(UploadTest, RestOAuth):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(TestExtensionVersionViewSetPost, self).setUp()
        self.user = UserProfile.objects.get(pk=2519)
        self.extension = Extension.objects.create(name=u'Än Extension')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, status=STATUS_PENDING,
            version='0.0')
        self.list_url = reverse('api-v2:extension-version-list', kwargs={
            'extension_pk': self.extension.pk})
        self.publish_url = reverse('api-v2:extension-version-publish', kwargs={
            'extension_pk': self.extension.pk, 'pk': self.version.pk})
        self.reject_url = reverse('api-v2:extension-version-reject', kwargs={
            'extension_pk': self.extension.pk, 'pk': self.version.pk})

    def tearDown(self):
        super(TestExtensionVersionViewSetPost, self).tearDown()
        # Explicitely delete the Extensions to clean up leftover files.
        Extension.objects.all().delete()

    def test_has_cors(self):
        self.assertCORS(self.anon.options(self.publish_url), 'post')
        self.assertCORS(self.anon.options(self.reject_url), 'post')

    def test_post_anonymous(self):
        response = self.anon.post(self.publish_url)
        eq_(response.status_code, 403)
        response = self.anon.post(self.reject_url)
        eq_(response.status_code, 403)
        response = self.anon.post(self.list_url)
        eq_(response.status_code, 403)

    def test_post_logged_in_no_rights(self):
        response = self.client.post(self.publish_url)
        eq_(response.status_code, 403)
        response = self.client.post(self.reject_url)
        eq_(response.status_code, 403)
        response = self.client.post(self.list_url)
        eq_(response.status_code, 403)

    def test_post_non_existing_extension(self):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.list_url = reverse('api-v2:extension-version-list', kwargs={
            'extension_pk': self.extension.pk + 42})
        self.publish_url = reverse('api-v2:extension-version-publish', kwargs={
            'extension_pk': self.extension.pk + 42, 'pk': self.version.pk})
        self.reject_url = reverse('api-v2:extension-version-reject', kwargs={
            'extension_pk': self.extension.pk + 42, 'pk': self.version.pk})
        self.publish_url2 = reverse(
            'api-v2:extension-version-publish',
            kwargs={'extension_pk': self.extension.pk,
                    'pk': self.version.pk + 42})
        self.reject_url2 = reverse('api-v2:extension-version-reject', kwargs={
            'extension_pk': self.extension.pk, 'pk': self.version.pk + 42})
        response = self.client.post(self.list_url)
        eq_(response.status_code, 404)
        response = self.client.post(self.publish_url)
        eq_(response.status_code, 404)
        response = self.client.post(self.reject_url)
        eq_(response.status_code, 404)
        response = self.client.post(self.publish_url2)
        eq_(response.status_code, 404)
        response = self.client.post(self.reject_url2)
        eq_(response.status_code, 404)

    def test_post_logged_in_with_rights(self):
        self.extension.authors.add(self.user)
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url, json.dumps({
            'message': u'add-on has arrivedÄ',
            'validation_id': upload.pk
        }))
        eq_(response.status_code, 201)
        data = response.json
        eq_(data['size'],
            local_storage.size(self.packaged_app_path('extension.zip')))
        eq_(data['status'], 'pending')
        eq_(data['version'], '0.1')
        eq_(Extension.objects.count(), 1)
        eq_(ExtensionVersion.objects.count(), 2)
        self.extension.reload()
        new_version = ExtensionVersion.objects.get(pk=data['id'])
        eq_(self.extension.status, STATUS_PENDING)
        eq_(self.extension.latest_version, new_version)

        note = self.extension.threads.get().notes.get()
        eq_(note.body, u'add-on has arrivedÄ')
        eq_(note.note_type, comm.SUBMISSION)

    def test_post_same_version_that_was_deleted(self):
        # Pretend version was already published, include some fake data to have
        # the files that would normally exist on the fileystem.
        self.version.update(version='0.1', status=STATUS_PUBLIC)
        file_path = self.version.file_path
        with private_storage.open(file_path, 'w') as f:
            f.write('sample data\n')
        signed_file_path = self.version.signed_file_path
        with public_storage.open(signed_file_path, 'w') as f:
            f.write('sample signed data\n')
        # Now delete the file...
        self.version.delete()

        # ... And try to upload the same version again.
        self.test_post_logged_in_with_rights()

    def test_post_logged_in_with_rights_disabled(self):
        self.extension.authors.add(self.user)
        self.extension.update(disabled=True)
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url,
                                    json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 403)

    def test_post_logged_in_with_rights_deleted(self):
        self.extension.authors.add(self.user)
        self.extension.update(deleted=True)
        upload = self.get_upload(
            abspath=self.packaged_app_path('extension.zip'), user=self.user)
        eq_(upload.valid, True)
        response = self.client.post(self.list_url,
                                    json.dumps({'validation_id': upload.pk}))
        eq_(response.status_code, 404)

    @mock.patch('mkt.extensions.models.ExtensionVersion.sign_file')
    def test_publish_disabled(self, sign_file_mock):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.extension.update(disabled=True)
        response = self.client.post(self.publish_url)
        eq_(response.status_code, 403)
        ok_(not sign_file_mock.called)

    @mock.patch('mkt.extensions.models.ExtensionVersion.sign_file')
    def test_publish(self, sign_file_mock):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        sign_file_mock.return_value = 665
        response = self.client.post(self.publish_url, data=json.dumps({
            'message': u'Nîce extension'
        }))
        eq_(response.status_code, 202)
        eq_(sign_file_mock.call_count, 1)
        self.extension.reload()
        self.version.reload()
        eq_(self.extension.status, STATUS_PUBLIC)
        eq_(self.version.size, 665)
        eq_(self.version.status, STATUS_PUBLIC)

        note = self.version.threads.get().notes.get()
        eq_(note.note_type, comm.APPROVAL)
        eq_(note.body, u'Nîce extension')

    @mock.patch.object(ExtensionVersion, 'remove_public_signed_file')
    def test_reject_disabled(self, remove_public_signed_file_mock):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.extension.update(disabled=True)
        response = self.client.post(self.reject_url)
        eq_(response.status_code, 403)
        ok_(not remove_public_signed_file_mock.called)

    @mock.patch.object(ExtensionVersion, 'remove_public_signed_file')
    def test_reject(self, remove_public_signed_file_mock):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        remove_public_signed_file_mock.return_value = 666
        response = self.client.post(self.reject_url, data=json.dumps({
            'message': u'Bâd extension'
        }))
        eq_(response.status_code, 202)
        eq_(remove_public_signed_file_mock.call_count, 1)
        self.extension.reload()
        self.version.reload()
        eq_(self.version.size, 666)
        eq_(self.version.status, STATUS_REJECTED)
        eq_(self.extension.status, STATUS_REJECTED)

        note = self.version.threads.get().notes.get()
        eq_(note.note_type, comm.REJECTION)
        eq_(note.body, u'Bâd extension')


class TestExtensionVersionViewSetDelete(RestOAuth):
    fixtures = fixture('user_2519', 'user_999')

    def setUp(self):
        super(TestExtensionVersionViewSetDelete, self).setUp()
        self.extension = Extension.objects.create(name=u'Än Extension')
        self.public_version = ExtensionVersion.objects.create(
            extension=self.extension, status=STATUS_PUBLIC,
            version='0.42')
        self.pending_version = ExtensionVersion.objects.create(
            extension=self.extension, status=STATUS_PENDING,
            version='0.43')
        self.other_extension = Extension.objects.create()
        self.other_version = ExtensionVersion.objects.create(
            extension=self.other_extension)
        self.user = UserProfile.objects.get(pk=2519)
        self.other_user = UserProfile.objects.get(pk=999)
        self.detail_url_public = reverse(
            'api-v2:extension-version-detail', kwargs={
                'extension_pk': self.extension.pk,
                'pk': self.public_version.pk})

    def test_delete_latest_public_version_logged_in_has_rights(self):
        eq_(ExtensionVersion.objects.without_deleted().count(), 3)
        self.extension.authors.add(self.user)
        response = self.client.delete(self.detail_url_public)
        eq_(response.status_code, 204)

        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 2)
        ok_(not ExtensionVersion.objects.without_deleted().filter(
            pk=self.public_version.pk).exists())
        ok_(ExtensionVersion.objects.without_deleted().filter(
            pk=self.pending_version.pk).exists())
        ok_(ExtensionVersion.objects.without_deleted().filter(
            pk=self.other_version.pk).exists())
        self.extension.reload()
        eq_(self.extension.status, STATUS_PENDING)

    def test_delete_latest_pending_version_logged_in_has_rights(self):
        self.detail_url_pending = reverse(
            'api-v2:extension-version-detail', kwargs={
                'extension_pk': self.extension.pk,
                'pk': self.pending_version.pk})

        eq_(ExtensionVersion.objects.without_deleted().count(), 3)
        self.extension.authors.add(self.user)
        response = self.client.delete(self.detail_url_pending)
        eq_(response.status_code, 204)

        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 2)
        ok_(ExtensionVersion.objects.without_deleted().filter(
            pk=self.public_version.pk).exists())
        ok_(not ExtensionVersion.objects.without_deleted().filter(
            pk=self.pending_version.pk).exists())
        ok_(ExtensionVersion.objects.without_deleted().filter(
            pk=self.other_version.pk).exists())
        self.extension.reload()
        eq_(self.extension.status, STATUS_PUBLIC)

    def test_delete_both_versions_logged_in_has_rights(self):
        self.detail_url_pending = reverse(
            'api-v2:extension-version-detail', kwargs={
                'extension_pk': self.extension.pk,
                'pk': self.pending_version.pk})

        eq_(ExtensionVersion.objects.without_deleted().count(), 3)
        self.extension.authors.add(self.user)
        response = self.client.delete(self.detail_url_pending)
        eq_(response.status_code, 204)
        response = self.client.delete(self.detail_url_public)
        eq_(response.status_code, 204)

        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 1)
        ok_(not ExtensionVersion.objects.without_deleted().filter(
            pk=self.public_version.pk).exists())
        ok_(not ExtensionVersion.objects.without_deleted().filter(
            pk=self.pending_version.pk).exists())
        ok_(ExtensionVersion.objects.without_deleted().filter(
            pk=self.other_version.pk).exists())
        self.extension.reload()
        eq_(self.extension.status, STATUS_NULL)

    def test_delete_logged_in_no_rights(self):
        self.extension.authors.add(self.other_user)
        response = self.client.delete(self.detail_url_public)
        eq_(response.status_code, 403)
        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 3)

    def test_delete_anonymous_no_rights(self):
        response = self.anon.delete(self.detail_url_public)
        eq_(response.status_code, 403)
        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 3)

    def test_delete__404(self):
        self.extension.authors.add(self.user)
        self.detail_url_public = reverse(
            'api-v2:extension-version-detail', kwargs={
                'extension_pk': self.extension.pk,
                'pk': self.public_version.pk + 555})
        response = self.client.delete(self.detail_url_public)
        eq_(response.status_code, 404)
        eq_(Extension.objects.without_deleted().count(), 2)
        eq_(ExtensionVersion.objects.without_deleted().count(), 3)


class TestExtensionNonAPIViews(TestCase):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(TestExtensionNonAPIViews, self).setUp()
        self.fake_manifest = {
            'name': u'Fake Extënsion',
            'version': '0.1',
        }
        self.extension = Extension.objects.create(name=u'Fake Extënsion')
        self.version = ExtensionVersion.objects.create(
            extension=self.extension, manifest=self.fake_manifest,
            status=STATUS_PUBLIC, version='0.1')
        self.user = UserProfile.objects.get(pk=2519)
        self.extension.authors.add(self.user)

    def _expected_etag(self):
        expected_etag = hashlib.sha256()
        expected_etag.update(unicode(self.extension.uuid))
        expected_etag.update(unicode(self.version.pk))
        return '"%s"' % expected_etag.hexdigest()

    @override_settings(
        XSENDFILE=True,
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    def test_download_signed(self):
        ok_(self.version.download_url)
        response = self.client.get(self.version.download_url)

        eq_(response.status_code, 200)
        eq_(response[settings.XSENDFILE_HEADER],
            self.version.signed_file_path)
        eq_(response['Content-Type'], 'application/zip')
        eq_(response['ETag'], self._expected_etag())

        self.login(self.user)
        response = self.client.get(self.version.download_url)
        eq_(response.status_code, 200)

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.S3BotoPrivateStorage')
    @mock.patch('mkt.site.utils.public_storage')
    def test_download_signed_using_storage(self, public_storage_mock):
        expected_path = 'https://s3.pub/%s' % self.version.signed_file_path
        public_storage_mock.url = lambda path: 'https://s3.pub/%s' % path
        ok_(self.version.download_url)
        response = self.client.get(self.version.download_url)
        self.assert3xx(response, expected_path)

    def test_download_signed_not_public(self):
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.download_url)
        response = self.client.get(self.version.download_url)
        eq_(response.status_code, 404)

        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        response = self.client.get(self.version.download_url)
        # Even authors and reviewers can't access it: it doesn't exist.
        eq_(response.status_code, 404)

    def test_download_signed_deleted(self):
        self.extension.update(deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        response = self.client.get(self.version.download_url)
        # Even authors and reviewers can't access it: it doesn't exist.
        eq_(response.status_code, 404)

    def test_download_signed_version_deleted(self):
        self.version.update(deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        response = self.client.get(self.version.download_url)
        # Even authors and reviewers can't access it: it doesn't exist.
        eq_(response.status_code, 404)

    def test_download_signed_reviewer_without_permission(self):
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.reviewer_download_url)
        response = self.client.get(self.version.reviewer_download_url)
        eq_(response.status_code, 403)

        self.login(self.user)
        response = self.client.get(self.version.reviewer_download_url)
        eq_(response.status_code, 403)

    def test_download_signed_reviewer_deleted(self):
        self.extension.update(deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)

        ok_(self.version.reviewer_download_url)
        response = self.client.get(self.version.reviewer_download_url)
        eq_(response.status_code, 404)

    def test_download_signed_reviewer_version_deleted(self):
        self.version.update(deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)

        ok_(self.version.reviewer_download_url)
        response = self.client.get(self.version.reviewer_download_url)
        eq_(response.status_code, 404)

    @override_settings(
        XSENDFILE=True,
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    @mock.patch.object(ExtensionVersion, 'reviewer_sign_if_necessary')
    def test_download_signed_reviewer_with_reviewer_permission(
            self, reviewer_sign_if_necessary_mock):
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.reviewer_download_url)
        self.login(self.user)

        response = self.client.get(self.version.reviewer_download_url)
        eq_(reviewer_sign_if_necessary_mock.call_count, 1)
        eq_(response[settings.XSENDFILE_HEADER],
            self.version.reviewer_signed_file_path)
        eq_(response['Content-Type'], 'application/zip')
        eq_(response['ETag'], self._expected_etag())

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.S3BotoPrivateStorage')
    @mock.patch.object(ExtensionVersion, 'reviewer_sign_if_necessary')
    @mock.patch('mkt.site.utils.private_storage')
    def test_download_signed_reviewer_with_reviewer_permission_using_storage(
            self, private_storage_mock, reviewer_sign_if_necessary_mock):
        private_storage_mock.url = lambda path: 'https://s3.priv/%s' % path
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.reviewer_download_url)
        self.login(self.user)
        expected_path = (
            'https://s3.priv/%s' % self.version.reviewer_signed_file_path)

        response = self.client.get(self.version.reviewer_download_url)
        eq_(reviewer_sign_if_necessary_mock.call_count, 1)
        self.assert3xx(response, expected_path)

    @override_settings(
        XSENDFILE=True,
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    def test_download_unsigned(self):
        ok_(self.version.unsigned_download_url)
        response = self.client.get(self.version.unsigned_download_url)
        eq_(response.status_code, 403)

        self.login(self.user)  # Log in as author.
        response = self.client.get(self.version.unsigned_download_url)
        eq_(response.status_code, 200)

        eq_(response[settings.XSENDFILE_HEADER],
            self.version.file_path)
        eq_(response['Content-Type'], 'application/zip')
        eq_(response['ETag'], self._expected_etag())

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.S3BotoPrivateStorage')
    @mock.patch('mkt.site.utils.private_storage')
    def test_download_unsigned_using_storage(self, private_storage_mock):
        expected_path = 'https://s3.private/%s' % self.version.file_path
        private_storage_mock.url = lambda path: 'https://s3.private/%s' % path
        self.login(self.user)  # Log in as author.
        ok_(self.version.unsigned_download_url)
        response = self.client.get(self.version.unsigned_download_url)
        self.assert3xx(response, expected_path)

    @override_settings(
        XSENDFILE=True,
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.LocalFileStorage')
    def test_download_unsigned_with_reviewer_permission(self):
        ok_(self.version.unsigned_download_url)
        self.extension.authors.remove(self.user)
        self.login(self.user)
        response = self.client.get(self.version.unsigned_download_url)
        eq_(response.status_code, 403)

        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.version.unsigned_download_url)
        eq_(response.status_code, 200)

        eq_(response[settings.XSENDFILE_HEADER],
            self.version.file_path)
        eq_(response['Content-Type'], 'application/zip')
        eq_(response['ETag'], self._expected_etag())

    @override_settings(
        DEFAULT_FILE_STORAGE='mkt.site.storage_utils.S3BotoPrivateStorage')
    @mock.patch('mkt.site.utils.private_storage')
    def test_download_unsigned_with_reviewer_permission_using_storage(
            self, private_storage_mock):
        expected_path = 'https://s3.private/%s' % self.version.file_path
        private_storage_mock.url = lambda path: 'https://s3.private/%s' % path

        ok_(self.version.unsigned_download_url)
        self.extension.authors.remove(self.user)
        self.login(self.user)
        response = self.client.get(self.version.unsigned_download_url)
        eq_(response.status_code, 403)

        self.grant_permission(self.user, 'ContentTools:AddonReview')
        response = self.client.get(self.version.unsigned_download_url)
        self.assert3xx(response, expected_path)

    def test_mini_manifest(self):
        ok_(self.extension.mini_manifest_url)
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], MANIFEST_CONTENT_TYPE)
        eq_(json.loads(response.content), self.extension.mini_manifest)

    def test_mini_manifest_etag(self):
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 200)
        original_etag = response['ETag']
        ok_(original_etag)

        # Test that the etag is the same if we just re-save the extension
        # or the version without changing the manifest.
        self.extension.save()
        self.version.save()
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 200)
        eq_(original_etag, response['ETag'])

        # Test that the etag is different if the version manifest changes.
        self.version.manifest['version'] = '9001'
        self.version.save()
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 200)
        ok_(original_etag != response['ETag'])

    def test_mini_manifest_not_public(self):
        self.extension.update(status=STATUS_PENDING)
        # `mini_manifest_url` exists but is a 404 when the extension is not
        # public.
        ok_(self.extension.mini_manifest_url)
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 404)

        self.login(self.user)  # Even logged in you can't access it for now.
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 404)

    def test_mini_manifest_deleted(self):
        self.extension.update(deleted=True)
        # `mini_manifest_url` exists but is a 404 when the extension is
        # deleted.
        ok_(self.extension.mini_manifest_url)
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 404)

        self.login(self.user)  # Even logged in you can't access it for now.
        response = self.client.get(self.extension.mini_manifest_url)
        eq_(response.status_code, 404)

    def test_reviewer_mini_manifest(self):
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.reviewer_mini_manifest_url)
        ok_(self.version.reviewer_mini_manifest)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], MANIFEST_CONTENT_TYPE)
        eq_(json.loads(response.content), self.version.reviewer_mini_manifest)

    def test_reviewer_mini_manifest_etag(self):
        self.version.update(status=STATUS_PENDING)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 200)
        original_etag = response['ETag']
        ok_(original_etag)

        # Test that the etag is the same if we just re-save the extension
        # or the version without changing the manifest.
        self.extension.save()
        self.version.save()
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 200)
        eq_(original_etag, response['ETag'])

        # Test that the etag is different if the version manifest changes.
        self.version.manifest['version'] = '9001'
        self.version.save()
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 200)
        ok_(original_etag != response['ETag'])

    def test_reviewer_mini_manifest_no_permission(self):
        self.version.update(status=STATUS_PENDING)
        ok_(self.version.reviewer_mini_manifest_url)
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 403)

    def test_reviewer_mini_manifest_deleted(self):
        self.version.update(status=STATUS_PENDING)
        self.extension.update(deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        # `reviewer_mini_manifest_url` exists but is a 404 when the extension
        # or the version is deleted.
        ok_(self.version.reviewer_mini_manifest_url)
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 404)

    def test_reviewer_mini_manifest_version_deleted(self):
        self.version.update(status=STATUS_PENDING, deleted=True)
        self.grant_permission(self.user, 'ContentTools:AddonReview')
        self.login(self.user)
        # `reviewer_mini_manifest_url` exists but is a 404 when the extension
        # or the version is deleted.
        ok_(self.version.reviewer_mini_manifest_url)
        response = self.client.get(self.version.reviewer_mini_manifest_url)
        eq_(response.status_code, 404)
