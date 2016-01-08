import base64
import logging
import quopri
import re
import urllib2
from email import message_from_string
from email.utils import parseaddr

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import translation

from email_reply_parser import EmailReplyParser

import mkt

from mkt.access import acl
from mkt.access.models import Group
from mkt.comm.models import CommunicationThreadToken, user_has_perm_thread
from mkt.constants import comm
from mkt.extensions.models import Extension
from mkt.site.helpers import absolutify
from mkt.site.mail import send_mail_jinja
from mkt.translations.utils import to_language
from mkt.users.models import UserProfile
from mkt.webapps.models import Webapp


log = logging.getLogger('z.comm')


def send_mail_comm(note):
    """
    Email utility used globally by the Communication Dashboard to send emails.
    Given a note (its actions and permissions), recipients are determined and
    emails are sent to appropriate people.
    """
    log.info(u'Sending emails for %s' % note.thread.obj)

    if note.note_type in comm.EMAIL_SENIOR_REVIEWERS_AND_DEV:
        # Email senior reviewers (such as for escalations).
        rev_template = comm.EMAIL_SENIOR_REVIEWERS_AND_DEV[note.note_type][
            'reviewer']
        email_recipients(get_senior_reviewers(), note, template=rev_template)

        # Email developers (such as for escalations).
        dev_template = comm.EMAIL_SENIOR_REVIEWERS_AND_DEV[note.note_type][
            'developer']
        email_recipients(get_developers(note), note, template=dev_template)
    else:
        email_recipients(get_recipients(note), note)

        # Also send mail to the fallback emailing list.
        if note.note_type == comm.DEVELOPER_COMMENT:
            subject = '%s: %s' % (unicode(comm.NOTE_TYPES[note.note_type]),
                                  note.thread.obj.name)
            mail_template = comm.COMM_MAIL_MAP.get(note.note_type, 'generic')
            send_mail_jinja(subject, 'comm/emails/%s.html' % mail_template,
                            get_mail_context(note, None),
                            recipient_list=[settings.MKT_REVIEWS_EMAIL],
                            from_email=settings.MKT_REVIEWERS_EMAIL,
                            perm_setting='app_reviewed')


def get_recipients(note):
    """
    Determine email recipients mainly based on CommunicationThreadCC.
    Returns user_id/user_email tuples.
    """
    if note.note_type in comm.EMAIL_SENIOR_REVIEWERS:
        return get_senior_reviewers()

    thread = note.thread
    recipients = thread.thread_cc.values_list('user__id', 'user__email')

    excludes = []
    if not note.read_permission_developer:
        # Exclude developer.
        excludes += get_developers(note)
    if note.author:
        # Exclude note author.
        excludes.append((note.author.id, note.author.email))

    return [r for r in set(recipients) if r not in excludes]


def tokenize_recipients(recipients, thread):
    """[(user_id, user_email)] -> [(user_email, token)]."""
    tokenized_recipients = []
    for user_id, user_email in recipients:
        if not user_id:
            tokenized_recipients.append((user_email, None, None))
        else:
            tok = get_reply_token(thread, user_id)
            tokenized_recipients.append((user_email, user_id, tok.uuid))
    return tokenized_recipients


def email_recipients(recipients, note, template=None, extra_context=None):
    """
    Given a list of tuple of user_id/user_email, email bunch of people.
    note -- commbadge note, the note type determines which email to use.
    template -- override which template we use.
    """
    subject = '%s: %s' % (unicode(comm.NOTE_TYPES[note.note_type]),
                          note.thread.obj.name)

    for email, user_id, tok in tokenize_recipients(recipients, note.thread):
        headers = {}
        if tok:
            headers['Reply-To'] = '{0}{1}@{2}'.format(
                comm.REPLY_TO_PREFIX, tok, settings.POSTFIX_DOMAIN)

        # Get the appropriate mail template.
        mail_template = template or comm.COMM_MAIL_MAP.get(note.note_type,
                                                           'generic')

        # Send mail.
        context = get_mail_context(note, user_id)
        context.update(extra_context or {})
        send_mail_jinja(subject, 'comm/emails/%s.html' % mail_template,
                        context, recipient_list=[email],
                        from_email=settings.MKT_REVIEWERS_EMAIL,
                        perm_setting='app_reviewed', headers=headers)


def get_mail_context(note, user_id):
    """
    Get context data for comm emails, specifically for review action emails.
    """
    obj = note.thread.obj

    # grep: comm-content-type.
    if obj.name and obj.__class__ == Webapp:
        # We need to display the name in some language that is relevant to the
        # recipient(s) instead of using the reviewer's. addon.default_locale
        # should work.
        lang = to_language(obj.default_locale)
        with translation.override(lang):
            obj = Webapp.with_deleted.get(id=obj.id)
    elif not obj.name:
        # For deleted objects.
        obj.name = obj.app_slug if hasattr(obj, 'app_slug') else obj.slug

    if user_id:
        UserProfile.objects.get(id=user_id)

    # grep: comm-content-type.
    manage_url = ''
    obj_type = ''
    thread_url = ''
    if obj.__class__ == Webapp:
        manage_url = absolutify(obj.get_dev_url('versions'))
        obj_type = 'app'
        thread_url = absolutify(reverse('commonplace.commbadge.show_thread',
                                        args=[note.thread.id]))
    elif obj.__class__ == Extension:
        manage_url = absolutify(reverse('commonplace.content.addon_manage',
                                        args=[obj.slug]))
        # Not "Firefox OS add-on" for a/an consistency with "app".
        obj_type = 'add-on'
        if user_id:
            user = UserProfile.objects.get(id=user_id)
            if acl.action_allowed_user(user, 'ContentTools', 'AddonReview'):
                thread_url = absolutify(
                    reverse('commonplace.content.addon_review',
                            args=[obj.slug]))
            else:
                thread_url = manage_url

    return {
        'mkt': mkt,
        'comm': comm,
        'is_app': obj.__class__ == Webapp,
        'is_extension': obj.__class__ == Extension,
        'manage_url': manage_url,
        'note': note,
        'obj': obj,
        'obj_type': obj_type,
        'settings': settings,
        'thread_url': thread_url
    }


class CommEmailParser(object):
    """Utility to parse email replies."""
    address_prefix = comm.REPLY_TO_PREFIX

    def __init__(self, email_text):
        """Decode base64 email and turn it into a Django email object."""
        try:
            email_text = base64.standard_b64decode(
                urllib2.unquote(email_text.rstrip()))
        except TypeError:
            # Corrupt or invalid base 64.
            self.decode_error = True
            log.info('Decoding error for CommEmailParser')
            return

        self.email = message_from_string(email_text)

        payload = self.email.get_payload()
        if isinstance(payload, list):
            # If multipart, get the plain text part.
            for part in payload:
                # Nested multipart. Go deeper.
                if part.get_content_type() == 'multipart/alternative':
                    payload = part.get_payload()
                    for part in payload:
                        if part.get_content_type() == 'text/plain':
                            # Found the plain text part.
                            payload = part.get_payload()
                            break

                if part.get_content_type() == 'text/plain':
                    # Found the plain text part.
                    payload = part.get_payload()
                    break

        # Decode quoted-printable data and remove non-breaking spaces.
        payload = (quopri.decodestring(payload)
                         .replace('\xc2\xa0', ' '))
        payload = self.extra_email_reply_parse(payload)
        self.reply_text = EmailReplyParser.read(payload).reply

    def extra_email_reply_parse(self, email):
        """
        Adds an extra case to the email reply parser where the reply is
        followed by headers like "From: appreviews@lists.mozilla.org" and
        strips that part out.
        """
        email_header_re = re.compile('From: [^@]+@[^@]+\.[^@]+')
        split_email = email_header_re.split(email)
        if split_email[0].startswith('From: '):
            # In case, it's a bottom reply, return everything.
            return email
        else:
            # Else just return the email reply portion.
            return split_email[0]

    def _get_address_line(self):
        return parseaddr(self.email['to']) or parseaddr(self.email(['reply']))

    def get_uuid(self):
        name, addr = self._get_address_line()

        if addr.startswith(self.address_prefix):
            # Strip everything between "commreply+" and the "@" sign.
            uuid = addr[len(self.address_prefix):].split('@')[0]
        else:
            log.info('TO: address missing or not related to comm. (%s)'
                     % unicode(self.email).strip())
            return False

        return uuid

    def get_body(self):
        return self.reply_text


def save_from_email_reply(reply_text):
    from mkt.comm.utils import create_comm_note

    log.debug("Saving from email reply")

    parser = CommEmailParser(reply_text)
    if hasattr(parser, 'decode_error'):
        return False

    uuid = parser.get_uuid()

    if not uuid:
        return False
    try:
        tok = CommunicationThreadToken.objects.get(uuid=uuid)
    except CommunicationThreadToken.DoesNotExist:
        log.error('An email was skipped with non-existing uuid %s.' % uuid)
        return False

    thread = tok.thread
    if user_has_perm_thread(thread, tok.user) and tok.is_valid():
        # Deduce an appropriate note type.
        note_type = comm.NO_ACTION

        # grep: comm-content-type.
        if (thread.obj.__class__ == Webapp and
                tok.user.addonuser_set.filter(addon=thread.obj).exists()):
            note_type = comm.DEVELOPER_COMMENT
        elif (thread.obj.__class__ == Extension and
                tok.user.extension_set.filter(id=thread.obj.id).exists()):
            note_type = comm.DEVELOPER_COMMENT
        elif (acl.action_allowed_user(tok.user, 'Apps', 'Review') or
              acl.action_allowed_user(tok.user, 'ContentTools',
                                      'AddonReview')):
            note_type = comm.REVIEWER_PUBLIC_COMMENT

        t, note = create_comm_note(tok.thread.obj, tok.thread.version,
                                   tok.user, parser.get_body(),
                                   note_type=note_type)
        log.info('A new note has been created (from %s using tokenid %s).'
                 % (tok.user.id, uuid))
        return note
    elif tok.is_valid():
        log.error('%s did not have perms to reply to comm email thread %s.'
                  % (tok.user.email, tok.thread.id))
    else:
        log.error('%s tried to use an invalid comm token for thread %s.'
                  % (tok.user.email, tok.thread.id))

    return False


def get_reply_token(thread, user_id):
    tok, created = CommunicationThreadToken.objects.get_or_create(
        thread=thread, user_id=user_id)

    # We expire a token after it has been used for a maximum number of times.
    # This is usually to prevent overusing a single token to spam to threads.
    # Since we're re-using tokens, we need to make sure they are valid for
    # replying to new notes so we reset their `use_count`.
    if not created:
        tok.update(use_count=0)
    else:
        log.info('Created token with UUID %s for user_id: %s.' %
                 (tok.uuid, user_id))
    return tok


def get_developers(note):
    return list(note.thread.obj.authors.values_list('id', 'email'))


def get_senior_reviewers():
    try:
        return list(Group.objects.get(name='Senior App Reviewers')
                                 .users.values_list('id', 'email'))
    except Group.DoesNotExist:
        return []
