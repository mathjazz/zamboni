import urllib

from django import forms
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory

from mock import patch
from nose.tools import eq_
from rest_framework.decorators import (authentication_classes,
                                       permission_classes)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from mkt.api.base import cors_api_view, SubRouterWithFormat
from mkt.api.tests.test_oauth import RestOAuth
from mkt.site.tests import TestCase
from mkt.webapps.views import AppViewSet


class URLRequestFactory(RequestFactory):

    def _encode_data(self, data, content_type):
        return urllib.urlencode(data)


class TestEncoding(RestOAuth):

    def test_blah_encoded(self):
        """
        Regression test of bug #858403: ensure that a 415 (and not 500) is
        raised when an unsupported Content-Type header is passed to an API
        endpoint.
        """
        r = self.client.post(reverse('app-list'),
                             CONTENT_TYPE='application/blah',
                             data='cvan was here')
        eq_(r.status_code, 415)

    def test_bad_json(self):
        r = self.client.post(reverse('app-list'),
                             CONTENT_TYPE='application/json',
                             data="not ' json ' 5")
        eq_(r.status_code, 400)

    def test_not_json(self):
        r = self.client.get(reverse('app-list'),
                            HTTP_ACCEPT='application/blah')
        # We should return a 406, but for endpoints that only accept JSON, we
        # cheat and return json content without even looking at the Accept
        # header (see mkt.api.renderers and settings).
        eq_(r.status_code, 200)
        eq_(r['content-type'], 'application/json; charset=utf-8')

    @patch.object(AppViewSet, 'create')
    def test_form_encoded(self, create_mock):
        create_mock.return_value = Response()
        self.client.post(reverse('app-list'),
                         data='foo=bar',
                         content_type='application/x-www-form-urlencoded')
        eq_(create_mock.call_args[0][0].data['foo'], 'bar')


class TestCORSWrapper(TestCase):
    urls = 'mkt.api.tests.test_base_urls'

    def test_cors(self):
        @cors_api_view(['GET', 'PATCH'])
        @authentication_classes([])
        @permission_classes([])
        def foo(request):
            return Response()
        request = RequestFactory().options('/')
        foo(request)
        eq_(request.CORS, ['GET', 'PATCH'])

    def test_cors_with_headers(self):
        @cors_api_view(['POST'], headers=('x-barfoo',))
        @authentication_classes([])
        @permission_classes([])
        def foo(request):
            return Response()
        request = RequestFactory().options('/')
        foo(request)
        eq_(request.CORS_HEADERS, ('x-barfoo',))

    def test_cors_options(self):
        res = self.client.options(reverse('test-cors-api-view'))
        eq_(res['Access-Control-Allow-Origin'], '*')
        eq_(res['Access-Control-Allow-Headers'], 'x-barfoo, x-foobar')


class Form(forms.Form):
    app = forms.ChoiceField(choices=(('valid', 'valid'),))


class TestSubRouterWithFormat(TestCase):

    def test_format_is_included(self):
        router = SubRouterWithFormat()
        router.register('foo', ModelViewSet, base_name='bar')
        expected = [
            {'name': 'bar-list', 'pattern': '^(?P<pk>[^/.]+)/foo/$'},
            {'name': 'bar-detail', 'pattern': '^(?P<pk>[^/.]+)/foo/$'},
            {'name': 'bar-list',
             'pattern': '^(?P<pk>[^/.]+)/foo\\.(?P<format>[a-z0-9]+)/?$'},
            {'name': 'bar-detail',
             'pattern': '^(?P<pk>[^/.]+)/foo\\.(?P<format>[a-z0-9]+)/?$'},
        ]
        actual = [{
            'name': url.name, 'pattern': url.regex.pattern
        } for url in router.urls]
        for i, _ in enumerate(expected):
            eq_(actual[i], expected[i])

    def test_format_is_included_no_trailing_slashes(self):
        router = SubRouterWithFormat(trailing_slash=False)
        router.register('foo', ModelViewSet, base_name='bar')
        expected = [
            {'name': 'bar-list', 'pattern': '^(?P<pk>[^/.]+)/foo$'},
            {'name': 'bar-detail', 'pattern': '^(?P<pk>[^/.]+)/foo$'},
            {'name': 'bar-list',
             'pattern': '^(?P<pk>[^/.]+)/foo\\.(?P<format>[a-z0-9]+)/?$'},
            {'name': 'bar-detail',
             'pattern': '^(?P<pk>[^/.]+)/foo\\.(?P<format>[a-z0-9]+)/?$'},
        ]
        actual = [{
            'name': url.name, 'pattern': url.regex.pattern
        } for url in router.urls]
        for i, _ in enumerate(expected):
            eq_(actual[i], expected[i])
