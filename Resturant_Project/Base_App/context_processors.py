from django.conf import settings


def live_chat(request):
    return {
        'live_chat_ready': getattr(settings, 'LIVE_CHAT_READY', False),
        'tawk_property_id': getattr(settings, 'TAWK_TO_PROPERTY_ID', ''),
        'tawk_widget_id': getattr(settings, 'TAWK_TO_WIDGET_ID', ''),
    }
