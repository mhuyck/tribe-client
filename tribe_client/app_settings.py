TRIBE_URL = 'https://tribe.greenelab.com'
CROSSREF = 'Entrez'

try:
    from django.conf import settings

    TRIBE_URL = getattr(settings, 'TRIBE_URL', TRIBE_URL)

    CROSSREF = getattr(settings, 'TRIBE_CROSSREF_DB', CROSSREF)

    TRIBE_ID = getattr(settings, 'TRIBE_ID', '')
    TRIBE_SECRET = getattr(settings, 'TRIBE_SECRET', '')

    TRIBE_REDIRECT_URI = getattr(settings, 'TRIBE_REDIRECT_URI', '')

except ImportError:
    pass

ACCESS_CODE_URL = TRIBE_URL + "/oauth2/authorize/"
ACCESS_TOKEN_URL = TRIBE_URL + "/oauth2/token/"
