from django.conf import settings
from django import http


class BlockIPMiddleware(object):
    def process_request(self, request):
        if request.META['REMOTE_ADDR'] in settings.BLOCKED_IPS:
            return http.HttpResponseForbidden("<h1>Forbidden</h1>")
        return None
