import base64
import json
import os
import requests
from pathlib import Path

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simpleconsent.settings_unittest")
django.setup()
from django.conf import settings
from consent.models import Consent
from consent.tests.setup_db_consent import load_testset1, setup_db_tables_consent

# prepare database fixture (a temporary in-memory database is created for this test)
django.setup()
assert 'consent' in settings.INSTALLED_APPS
setup_db_tables_consent()
load_testset1()
assert len(Consent.objects.all()) > 0, 'No gvOrganisation data found'

origin = 'http://127.0.0.1:8000'


def test_display_consent_request():
    consent_request = {
        'entityid': 'xx',
        'userid': 'test_inv_2',
        'sp': 'TEST SP1',
        'attr_list': ['first_name', 'last_name', 'email'],
    }
    consent_request_json = json.dumps(consent_request)
    consent_request_json_b64 = base64.urlsafe_b64encode(consent_request_json.encode('ascii'))
    url = f"{origin}/request_consent/{consent_request_json_b64.decode('ascii')}/"
    response = requests.request(method='GET', url=url)
    assert response.status_code == 200
    Path('consent/tests/testout/display_consent.html').write_text(response.content.decode('utf-8'))
    assert Path('consent/tests/expected_results/display_consent.html').read_text() == response.content.decode('utf-8')