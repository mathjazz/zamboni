# -*- coding: utf8 -*-
import datetime
import requests
from urlparse import urljoin
from uuid import UUID

from django.conf import settings
from django.db import transaction

import commonware.log

from lib.iarc_v2.serializers import IARCV2RatingListSerializer
from mkt.site.helpers import absolutify
from mkt.translations.utils import no_translation
from mkt.users.models import UserProfile
from mkt.webapps.models import IARCCert, Webapp

log = commonware.log.getLogger('z.iarc_v2')


class IARCException(Exception):
    pass


def app_data(app):
    """App data that IARC needs in PushCert response / AttachToCert request."""
    author = app.listed_authors[0] if app.listed_authors else UserProfile()
    with no_translation(app.default_locale):
        app_name = unicode(Webapp.with_deleted.get(pk=app.pk).name)
    data = {
        'Publish': app.is_public(),
        'ProductName': app_name,
        'StoreProductID': app.guid,
        'StoreProductURL': absolutify(app.get_url_path()),
        # We want an identifier that does not change when users attached to
        # an app are shuffled around, so just use the app PK as developer id.
        'StoreDeveloperID': app.pk,
        # PushCert and AttachToCert docs use a different property for the
        # developer email address, use both just in case.
        'DeveloperEmail': author.email,
        'EmailAddress': author.email,
        'CompanyName': app.developer_name,
    }
    return data


def get_rating_changes():
    """
    Call GetRatingChange to get all changes from IARC within the last day, and
    apply them to the corresponding Webapps.

    FIXME: Could add support for pagination, but very low priority since we
    will never ever get anywhere close to 500 rating changes in a single day.
    """
    start_date = datetime.datetime.utcnow()
    end_date = start_date - datetime.timedelta(days=1)
    url = urljoin(settings.IARC_V2_SERVICE_ENDPOINT, 'GetRatingChanges')
    data = requests.post(url, json={
        'StartDate': start_date.strftime('%Y-%m-%d'),
        'EndDate': end_date.strftime('%Y-%m-%d'),
        'MaxRows': 500,  # Limit.
        'StartRowIndex': 0  # Offset.
    }).json()
    for row in data.get('CertList', []):
        # Find app through Cert ID, ignoring unknown certs.
        try:
            cert = IARCCert.objects.get(cert_id=UUID(row['CertID']).get_hex())
        except IARCCert.DoesNotExist:
            continue
        serializer = IARCV2RatingListSerializer(instance=cert.app, data=row)
        if serializer.is_valid():
            serializer.save()
    return data


@transaction.atomic
def search_and_attach_cert(app, cert_id):
    """Call SearchCerts to get all info about an existing cert from IARC and
    apply that info to the Webapp instance passed. Then, call AttachToCert
    to notify IARC that we're attaching the cert to that Webapp."""
    serializer = _search_cert(app, cert_id)
    if serializer.is_valid():
        serializer.save()
    else:
        raise IARCException('SearchCerts failed!')
    data = _attach_to_cert(app, cert_id)
    if data.get('ResultCode') != 'Success':
        # If AttachToCert failed, we need to rollback the save we did earlier,
        # we raise an exception to do that since we are in an @atomic block.
        raise IARCException(data.get('ErrorMessage', 'AttachToCert failed!'))
    return data


def _search_cert(app, cert_id):
    """Ask IARC for information about a cert."""
    url = urljoin(settings.IARC_V2_SERVICE_ENDPOINT, 'SearchCerts')
    data = requests.post(url, json={'CertID': unicode(UUID(cert_id))}).json()
    # We don't care about MatchFound, serializer won't find the right fields
    # if no match is found.
    serializer = IARCV2RatingListSerializer(instance=app, data=data)
    return serializer


def _attach_to_cert(app, cert_id):
    """Tell IARC to attach a cert to an app."""
    url = urljoin(settings.IARC_V2_SERVICE_ENDPOINT, 'AttachToCert')
    data = app_data(app)
    data['CertID'] = unicode(UUID(cert_id))
    return requests.post(url, json=data).json()


def publish(app):
    """Tell IARC we published an app."""
    try:
        cert_id = app.iarc_cert.cert_id
        data = _update_certs(cert_id, 'Publish')
    except IARCCert.DoesNotExist:
        data = None
    return data


def unpublish(app):
    """Tell IARC we unpublished an app."""
    try:
        cert_id = app.iarc_cert.cert_id
        data = _update_certs(cert_id, 'RemoveProduct')
    except IARCCert.DoesNotExist:
        data = None
    return data


# FIXME: implement UpdateStoreAttributes for when the app developer email
# changes.


def _update_certs(cert_id, action):
    """
    UpdateCerts to tell IARC when we publish or unpublish a product.
    Endpoint can handle batch updates, but we only need one at a time.

    Arguments:
    cert_id -- Globally unique ID for certificate.
    action -- One of [InvalidateCert, RemoveProduct, UpdateStoreAttributes,
                      Publish].

    Return:
    Update object.
        ResultCode (string) -- Success or Failure
        ErrorId (string) -- Can pass on to IARC for debugging.
        ErrorMessage (string) -- Human-readable error message
    """
    url = urljoin(settings.IARC_V2_SERVICE_ENDPOINT, 'UpdateCerts')
    data = {
        'UpdateList': [{
            'CertID': unicode(UUID(cert_id)),
            'Action': action,
        }]
    }
    return requests.post(url, json=data).json()
