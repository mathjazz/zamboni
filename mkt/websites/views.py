from lxml.etree import XMLSyntaxError

from django.db.transaction import non_atomic_requests

import requests
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from mkt.api.authentication import (RestOAuthAuthentication,
                                    RestSharedSecretAuthentication)
from mkt.api.base import CORSMixin, MarketplaceView
from mkt.api.permissions import GroupPermission
from mkt.reviewers.forms import ReviewersWebsiteSearchForm
from mkt.search.filters import (PublicContentFilter, WebsiteSearchFormFilter,
                                RegionFilter, ReviewerWebsiteSearchFormFilter,
                                SearchQueryFilter, SortingFilter)
from mkt.search.forms import SimpleSearchForm
from mkt.websites.helpers import WebsiteMetadata
from mkt.websites.indexers import WebsiteIndexer
from mkt.websites.models import Website, WebsiteSubmission
from mkt.websites.serializers import (ESWebsiteSerializer,
                                      ReviewerESWebsiteSerializer,
                                      WebsiteSerializer,
                                      PublicWebsiteSubmissionSerializer)


class WebsiteView(CORSMixin, MarketplaceView, RetrieveAPIView):
    cors_allowed_methods = ['get']
    authentication_classes = [RestSharedSecretAuthentication,
                              RestOAuthAuthentication]
    permission_classes = [AllowAny]
    serializer_class = WebsiteSerializer
    queryset = Website.objects.valid()


class WebsiteSearchView(CORSMixin, MarketplaceView, ListAPIView):
    """
    Base website search view based on a single-string query.
    """
    cors_allowed_methods = ['get']
    authentication_classes = [RestSharedSecretAuthentication,
                              RestOAuthAuthentication]
    permission_classes = [AllowAny]
    filter_backends = [PublicContentFilter, WebsiteSearchFormFilter,
                       RegionFilter, SearchQueryFilter, SortingFilter]
    serializer_class = ESWebsiteSerializer
    form_class = SimpleSearchForm

    def get_queryset(self):
        return WebsiteIndexer.search()

    @classmethod
    def as_view(cls, **kwargs):
        # Make all search views non_atomic: they should not need the db, or
        # at least they should not need to make db writes, so they don't need
        # to be wrapped in transactions.
        view = super(WebsiteSearchView, cls).as_view(**kwargs)
        return non_atomic_requests(view)


class ReviewersWebsiteSearchView(WebsiteSearchView):
    permission_classes = [GroupPermission('Apps', 'Review')]
    filter_backends = [SearchQueryFilter, ReviewerWebsiteSearchFormFilter,
                       SortingFilter]
    serializer_class = ReviewerESWebsiteSerializer
    form_class = ReviewersWebsiteSearchForm


class WebsiteMetadataScraperView(CORSMixin, MarketplaceView, APIView):
    """
    Base website search view based on a single-string query.
    """
    cors_allowed_methods = ['get']
    authentication_classes = [RestSharedSecretAuthentication,
                              RestOAuthAuthentication]
    permission_classes = [AllowAny]

    errors = {
        'no_url': '`url` querystring parameter required',
        'network': 'Unable to fetch website metadata',
        'malformed_data': 'Unable to parse website HTML.'
    }

    def get(self, request, format=None):
        url = request.query_params.get('url', None)
        if not url:
            return Response(self.errors['no_url'],
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(WebsiteMetadata(url), status=status.HTTP_200_OK)
        except requests.exceptions.RequestException:
            return Response(self.errors['network'],
                            status=status.HTTP_400_BAD_REQUEST)
        except XMLSyntaxError:
            return Response(self.errors['malformed_data'],
                            status=status.HTTP_400_BAD_REQUEST)


class WebsiteSubmissionViewSet(CORSMixin, MarketplaceView,
                               viewsets.ModelViewSet):
    cors_allowed_methods = ['get', 'post']
    authentication_classes = [RestSharedSecretAuthentication,
                              RestOAuthAuthentication]
    queryset = WebsiteSubmission.objects.all()
    permission_classes = [GroupPermission('Websites', 'Submit')]
    serializer_class = PublicWebsiteSubmissionSerializer

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.update(submitter=self.request.user)
