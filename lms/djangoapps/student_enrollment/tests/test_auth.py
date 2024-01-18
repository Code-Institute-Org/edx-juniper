import base64

from django.test import TestCase
from django.contrib.auth.models import User
from oauth2_provider.models import Application

import requests


class AuthTestCase(TestCase):
    """
    - make a call to oauth endpoint to get user's JWT token
    - make a call to enrollment endpoint with AUTHHEADER including JWT
    - make a call to enrollment endpoint without AUTHHEADER
    """
    def setUp(self):
        self.login_service_user = User.objects.get(username='login_service_user')
        self.login_service_user.set_password('arglebargle')
        self.login_service_user.save()
        Application.objects.create(
            client_id='enrollment-auth',
            user=self.login_service_user, 
            client_type='confidential',
            authorization_grant_type='client-credentials',
            client_secret='k8xYnSGcXpfeeLhS',
            name='enrollment-auth')
        self.auth_application = Application.objects.get(name='enrollment-auth')
    
    def test_jwt_retrieval(self):
        client_id = self.auth_application.client_id
        client_secret = self.auth_application.client_secret

        credential = "{client_id}:{client_secret}".format(client_id=client_id, client_secret=client_secret)
        encoded_credential = base64.b64encode(credential.encode("utf-8")).decode("utf-8")

        headers = {"Authorization": "Basic {encoded_credential}".format(encoded_credential=encoded_credential), "Cache-Control": "no-cache"}
        data = {"grant_type": "client_credentials", "token_type": "jwt"}
        # data = {"client_id": client_id, "username": self.login_service_user.username, "grant_type": "password", "password": "arglebargle","token_type": "jwt"}

        token_request = requests.post('http://myopenedx.com/oauth2/access_token/', headers=headers, data=data)
        import ipdb; ipdb.set_trace()
        access_token = token_request.json()["access_token"]
        print(access_token)
