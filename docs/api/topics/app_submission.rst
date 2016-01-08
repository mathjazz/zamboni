.. _app_submission:

==============
App Submission
==============

How to submit an app
====================

Submitting an app involves a few steps. The client must be logged in for all
these steps and the user submitting the app must have accepted the `terms of use`_.

1. :ref:`Validate your app <app_validation-post-label>`. The validation will return
   a validation id.
2. :ref:`Post your app <app-post-label>` using the validation id.
   This will create an app and populate the data with the
   contents of the manifest. It will return the current app data.
3. :ref:`Update your app <app-put-label>`. Not everything that the Firefox
   Marketplace needs will be in the app, as the manifest does not
   contain all the data. Update the required fields.
4. :ref:`Create a screenshot <screenshot-post-label>`. For listing on the
   Firefox Marketplace, at least one screenshot is needed.
5. :ref:`Attach content ratings <content-ratings>`. All apps need content
   ratings before being reviewed.
6. :ref:`Ask for a review <enable-patch-label>`. All apps need to be reviewed,
   this will add it to the review queue.

.. _app_validation:

App Validation
==============

.. note:: The validation does not require you to be authenticated, however you
    cannot create apps from those validations. To validate and then submit an
    app you must be authenticated with the same account for both steps.

.. _app_validation-post-label:

.. http:post:: /api/v2/apps/validation/

    **Request**

    For an `Hosted App <https://developer.mozilla.org/en-US/Marketplace/Options/Hosted_apps>`_:

    :param manifest: URL to the manifest.
    :type manifest: string

    Example:

    .. code-block:: json

        {"manifest": "http://test.app.com/manifest.webapp"}

    Or for a `Packaged App <https://developer.mozilla.org/en-US/Marketplace/Options/Packaged_apps>`_:

    :param upload: an object containing the appropriate file data in the upload field. It has the following properties:
    :type upload: object
    :param upload.type: the content type for the file. In this case, the only valid type is `application/zip`.
    :type upload.type: string
    :param upload.data: the zip file for your app, encoded in base 64.
    :type upload.data: string
    :param upload.name: the file name.
    :type upload.name: string

    Example:

    .. code-block:: json

        {"upload": {"type": "application/zip",
                    "data": "UEsDBAo...gAAAAA=",
                    "name": "mozball.zip"}}

    **Response**

    Returns a :ref:`validation <app_validation-response-label>` result.

    :status 201: successfully created, processed.
    :status 202: successfully created, still processing.

.. _app_validation-response-label:

.. http:get:: /api/v2/apps/validation/(string:id)/

    **Response**

    Returns a particular validation.

    :param id: the id of the validation.
    :type id: string
    :param processed: if the validation has been processed. Hosted apps are
        done immediately but packaged apps are queued. Clients will have to
        poll the results URL until the validation has been processed.
    :type processed: boolean
    :param valid: if the validation passed.
    :type valid: boolean
    :param validation: the resulting validation messages if it failed.
    :type validation: string
    :status 200: successfully completed.

    Example not processed:

    .. code-block:: json

        {
            "id": "123abcd",
            "processed": false,
            "resource_uri": "/api/v2/apps/validation/123abcd/",
            "valid": false,
            "validation": ""
        }

    Example processed and passed:

    .. code-block:: json

        {
            "id": "123abcd",
            "processed": true,
            "resource_uri": "/api/v2/apps/validation/123abcd/",
            "valid": true,
            "validation": ""
        }

    Example processed and failed:

    .. code-block:: json

        {
            "id": "123abcd",
            "processed": true,
            "resource_uri": "/api/v2/apps/validation/123abcd/",
            "valid": false,
            "validation": {
            "errors": 1, "messages": [{
                "tier": 1,
                "message": "Your manifest must be served with the HTTP header \"Content-Type: application/x-web-app-manifest+json\". We saw \"text/html; charset=utf-8\".",
                "type": "error"
            }],
        }

Creating an App
===============

.. _app-post-label:

.. http:post:: /api/v2/apps/app/

    .. note:: Requires authentication and a successfully validated manifest.

    .. note:: You must accept the `terms of use`_ before submitting apps.

    .. note:: This method is throttled at 10 requests/day.

    **Request**

    :param manifest: the id of the :ref:`validation result <app_validation>` for your hosted app.
    :type manifest: string

    Or for a *packaged app*

    :param upload: the id of the :ref:`validation result <app_validation>` for your packaged app.
    :type upload: string

    **Response**

    :param: An :ref:`apps <app-response-label>`.
    :status: 201 successfully created.

.. _app-put-label:

.. http:put:: /api/v2/apps/app/(int:id)/

    **Request**

    :param required name: the title of the app. Maximum length 127 characters.
    :type name: string
    :param required categories: a list of the categories, at least two of the
        category slugs provided from the :ref:`category API <categories>`.
    :type categories: array
    :param required description: long description. Some HTML supported.
    :type description: string
    :param required privacy_policy: your privacy policy. Some HTML supported.
    :type privacy_policy: string
    :param optional homepage: a URL to your apps homepage.
    :type homepage: string
    :param optional support_url: a URL to your support homepage.
    :type support_url: string
    :param required support_email: the email address for support.
    :type support_email: string
    :param required device_types: a list of the device types at least one of:
        `desktop`, `mobile`, `tablet`, `firefoxos`. `mobile` and `tablet` both
        refer to Android mobile and tablet. As opposed to Firefox OS.
    :type device_types: array
    :param required premium_type: One of `free`, `premium`,
        `free-inapp`, `premium-inapp`, or `other`.
    :type premium_type: string
    :param optional price: The price for your app as a string, for example
        "0.10". Required for `premium` or `premium-inapp` apps.
    :type price: string
    :param optional payment_account: The path for the
        :ref:`payment account <payment-account-label>` resource you want to
        associate with this app.
    :type payment_account: string
    :param optional upsold: The path to the free app resource that
        this premium app is an upsell for.
    :type upsold: string


    **Response**

    :status 202: successfully updated.

Screenshots or videos
=====================

.. note:: Requires authentication and a successfully created app.

.. _screenshot-post-label:

.. http:post:: /api/v2/apps/app/(int:id|string:app_slug)/preview/

    **Request**

    :param position: the position of the preview on the app. We show the
        previews in the order given.
    :type position: int
    :param file: a dictionary containing the appropriate file data in the upload field.
    :type file: object
    :param file.type: the content type.
    :type file.type: string
    :param file.name: the file name.
    :type file.name: string
    :param file.data: the base 64 encoded data.
    :type file.data: string

    .. note:: There is currently a restriction of 5MB on file uploads through
        the API.

    **Response**

    A :ref:`screenshot <screenshot-response-label>` resource.

    :status 201: successfully completed.
    :status 400: error processing the form.

.. _screenshot-response-label:

.. http:get:: /api/v2/apps/preview/(int:preview_id)/

    **Response**

    Example:

    .. code-block:: json

        {
            "addon": "/api/v2/apps/app/1/",
            "id": 1,
            "position": 1,
            "thumbnail_url": "/img/uploads/...",
            "image_url": "/img/uploads/...",
            "filetype": "image/png",
            "resource_uri": "/api/v2/apps/preview/1/"
        }

.. http:delete:: /api/v2/apps/preview/(int:preview_id)/

    **Response**

    :status 204: successfully deleted.

Content ratings
===============

.. note:: Requires authentication and a successfully created app.

.. _content-ratings:

.. http:post:: /api/v2/apps/app/(int:id|string:app_slug)/content_ratings/

    **Request**

    :param submission_id: The submission ID received from IARC.
    :type submission_id: string
    :param security_code: The security code received from IARC.
    :type security_code: string

    **Response**

    :status 201: successfully assigned content ratings.
    :status 400: error processing the form.

Enabling an App
===============

.. note:: Requires authentication and a successfully created app.

.. _enable-patch-label:

.. http:patch:: /api/v2/apps/status/(int:app_id)/

    **Request**

    :param optional status: a status you'd like to move the app to (see below).
    :type status: string
    :param optional disabled_by_user: Whether the app is disabled or not.
    :type disabled_by_user: boolean

    **Response**

    :status 200: successfully completed.
    :status 400: something prevented the transition.


Key statuses are:

  * `incomplete`: incomplete
  * `pending`: pending, awaiting review
  * `public`: public and listed on listing pages and search results
  * `unlisted`: available only to those who know the URL and not listed on
    listing pages nor search results
  * `waiting`: waiting for the developer to publish, currently private and
    only visible to the developer and team members

Valid transitions that users can initiate are:

  * *incomplete* to *pending*: call this once your app has been completed and it
    will be added to the Marketplace review queue. This can only be called if all
    the required data is there. If not, you'll get an error containing the
    reason. For example:

    .. code-block:: json

        {
            "error_message": {
                "status": [
                    "You must provide a support email.",
                    "You must provide at least one device type.",
                    "You must provide at least one category.",
                    "You must upload at least one screenshot or video.",
                    "You must set up content ratings.",
                    "You must set up a payment account."
                ]
            }
        }

  * Once reviewed by the Marketplace review team, the app will be in one of the
    approved statuses ('public', 'waiting', or 'unlisted') and you can
    toggle between any of these statuses, e.g., *waiting* to *unlisted*.
  * *disabled_by_user*: by changing this value from `True` to `False` you can
    enable or disable an app.

.. _`terms of use`: https://marketplace.firefox.com/developers/terms
