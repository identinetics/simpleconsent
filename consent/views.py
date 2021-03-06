import base64
import hashlib
import hmac
import json
import os
import pathlib

from basicauth.decorators import basic_auth_required
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from jinja2 import Template
from consent.models import Consent
from consent.constants import InvalidHmacSignatureException


@basic_auth_required
def has_consent(request: HttpRequest, entityid_b64: str, consentid: str) -> HttpResponse:
    """ Test if a consent exists for a given active entityID/consentid pair """
    entityid_bytes = base64.urlsafe_b64decode(entityid_b64.encode('ascii'))
    try:
        _ = Consent.objects.get(entityID=entityid_bytes.decode('ascii'), consentid=consentid, revoked_at=None)
        return HttpResponse('true', status=200)
    except ObjectDoesNotExist:
        return HttpResponse('false', status=200)


def display_consent_request(request: HttpRequest, consent_requ_json_b64: str, hmac_remote: str) -> HttpResponse:
    consent_request_json = base64.urlsafe_b64decode(consent_requ_json_b64.encode('ascii'))
    consent_request = json.loads(consent_request_json)
    template_args = {}
    template_args['attr_list'] = consent_request['attr_list']
    template_args['entityid'] = consent_request['entityid']
    template_args['sp'] = consent_request['sp']
    template_args['consent_requ_json_b64'] = consent_requ_json_b64  # required for submit link
    template_args['hmac_remote'] = hmac_remote  # required for submit link
    template_args['purpose'] = settings.CONSENT_BOILERPLATE_TEXT['purpose']
    template_args['revocation'] = settings.CONSENT_BOILERPLATE_TEXT['revocation']
    template_args['title'] = settings.CONSENT_BOILERPLATE_TEXT['title']
    template_path = pathlib.Path(os.getenv('CONSENT_TEMPLATE', 'consent/templates/index.html'))
    template = Template(template_path.read_text())
    contents = template.render(template_args)
    return HttpResponse(contents)


def accept_consent(request: HttpRequest, consent_requ_json_b64: str, hmac_remote: str) -> HttpResponse:
    # authenticate the proxy initiating this operation with an hmac
    consent_request_json = base64.urlsafe_b64decode(consent_requ_json_b64.encode('ascii'))
    hmac_local = hmac.new(settings.PROXY_HMAC_KEY, consent_request_json, hashlib.sha256).hexdigest()
    if hmac_local != hmac_remote:
        raise InvalidHmacSignatureException('consent_request_json does not have valid (HMAC) signature')
    consent_request = json.loads(consent_request_json)

    if len(Consent.objects.filter(entityID=consent_request['entityid'],
                                  consentid=consent_request['consentid'], revoked_at=None)) == 0:
        consent = Consent()
        # skip input sanitization - we trust the signer
        consent.displayname = consent_request['displayname']
        consent.entityID = consent_request['entityid']
        consent.consentid = consent_request['consentid']
        consent.sp_displayname = consent_request['sp']
        consent.uid = consent_request['mail']
        consent.consent_text = ', '.join(consent_request['attr_list'])

        consent.save()

    return HttpResponseRedirect(settings.PROXY_HANDLE_CONSENT_RESPONSE_URL)


def decline_consent(request: HttpRequest) -> HttpResponse:
    return HttpResponseRedirect(settings.PROXY_HANDLE_CONSENT_RESPONSE_URL)
