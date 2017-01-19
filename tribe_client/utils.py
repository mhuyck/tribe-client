import json
import pickle
import requests

from app_settings import (
    TRIBE_URL, TRIBE_ID, TRIBE_SECRET, TRIBE_REDIRECT_URI,
    ACCESS_TOKEN_URL, CROSSREF, PUBLIC_GENESET_DEST)

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_organism_uri(scientific_name, tribe_url=None):
    """
    This function returns the uri for an organism resource in Tribe,
    given the organism's scientific name.

    Arguments:
    scientific_name -- A string. Scientific name of the species for which
    we want the Tribe resource uri (e.g. "Homo sapiens",
    "Pseudomonas aeruginosa")

    tribe_url -- Optional argument, a string. URL for the desired Tribe
    instance. If this is not passed, it will default to the public Tribe
    instance.

    Returns:
    organism_uri -- A string. Resource URI for the desired organism in Tribe.
    """

    if not tribe_url:
        tribe_url = TRIBE_URL

    if not tribe_url:
        logger.error('Both the "tribe_url" argument for this function and '
                     'the TRIBE_URL setting have not been defined, so Tribe '
                     'location is unspecified. Ending function without '
                     'requesting organism.')
        quit()

    # This filters organisms by scientific name in the 'organisms' endpoint
    # of Tribe's API. This returns a dictionary with 'meta' and 'objects' keys.
    parameters = {'scientific_name': scientific_name}
    organism_request = requests.get(tribe_url + '/api/v1/organism',
                                    params=parameters)
    org_response = organism_request.json()

    # The 'objects' key always contains a list (even when there is just one
    # element). Put this organism object's resource_uri in geneset_info.
    organism_obj = org_response['objects'][0]
    organism_uri = organism_obj['resource_uri']

    return organism_uri


def get_access_token(authorization_code):
    """
    Takes the temporary, short-lived authorization_code returned by tribe and
    sends it back (with some other ids and secrets) in exchange for an
    access_token.

    Arguments:
    authorization_code -- a string of characters returned by Tribe when it
    redirects the user from the page where they authorize the client to access
    their resources

    Returns:
    access_token -- another string of characters, with which users can remotely
    access their resources.

    """
    parameters = {
        "client_id": TRIBE_ID, "client_secret": TRIBE_SECRET,
        "grant_type": "authorization_code",  "code": authorization_code,
        "redirect_uri": TRIBE_REDIRECT_URI
    }
    tribe_connection = requests.post(ACCESS_TOKEN_URL, data=parameters)
    result = tribe_connection.json()
    if 'access_token' in result:
        access_token = result['access_token']
        return access_token
    else:
        return None


def retrieve_public_genesets(options={}, retrieve_all=False):
    """
    Returns only public genesets. This will not return any of the
    private ones since no oauth token is sent with this request.

    Arguments:
    options -- An optional dictionary to be sent as request parameters
    (to filter the types of genesets requested, etc.)

    retrieve_all --  A boolean value. If this is True, the function will
    keep requesting the next result page (from meta['next'] in the Tribe
    response), and adding those genesets to the geneset list that is
    returned, until meta['next'] is null/None (meaning that there is no
    next page).

    Returns:
    Either -

    a) A list of genesets (as dictionaries), or
    b) An empty list, if the request failed.
    """

    genesets_url = TRIBE_URL + '/api/v1/geneset/'

    try:
        genesets = []

        tribe_connection = requests.get(genesets_url, params=options)
        result = tribe_connection.json()
        genesets.extend(result['objects'])

        if retrieve_all is True:
            meta = result['meta']

            while meta['next'] is not None:
                genesets_url = TRIBE_URL + meta['next']
                tribe_connection = requests.get(genesets_url)
                result = tribe_connection.json()
                genesets.extend(result['objects'])
                meta = result['meta']

        return genesets

    except:
        return []


def retrieve_public_versions(geneset, options={}):
    """
    Returns only public versions. As with retrieve_public_genesets() above,
    this will not return any private versions since no oauth token is
    sent with this request.

    Arguments:
    options -- An optional dictionary to be sent as request parameters
    geneset -- The resource URI for the desired geneset

    Returns:
    Either -

    a) A list of versions (as dictionaries), or
    b) An empty list, if the request failed.
    """

    versions_url = TRIBE_URL + '/api/v1/version/'
    options['geneset__id'] = geneset
    options['xrdb'] = CROSSREF

    try:
        tribe_connection = requests.get(versions_url, params=options)
        result = tribe_connection.json()
        versions = result['objects']
        return versions

    except:
        return []


def retrieve_user_object(access_token):
    """
    Makes a get request to tribe using the access_token to get the user's info
    (the user should only have permissions to see the user object that
    corresponds to them).

    Arguments:
    access_token -- The OAuth token with which the user has access to their
    resources. This is a string of characters.

    Returns:
    Either -

    a) 'OAuth Token expired' if the access_token has expired,
    b) An empty list [] if the access_token is completely invalid, or
    c) The user object this user has access to (in the form of a dictionary)

    """

    parameters = {'oauth_consumer_key': access_token}

    try:
        tribe_connection = requests.get(TRIBE_URL + '/api/v1/user',
                                        params=parameters)
        result = tribe_connection.json()
        user = result['objects']  # This is in the form of a list
        meta = result['meta']

        if 'oauth_token_expired' in meta:
            return ('OAuth Token expired')
        else:
            return user[0]  # Grab the first (and only) element in the list
    except:
        return []


def retrieve_user_genesets(access_token, options={}):
    """
    Returns any genesets created by the user.

    Arguments:
    access_token -- The OAuth token with which the user has access to
    their resources. This is a string of characters.

    options -- An optional dictionary to be sent as request parameters

    Returns:
    Either -

    a) A list of genesets (as dictionaries), or
    b) An empty list, if the request failed.
    """

    try:
        get_user = retrieve_user_object(access_token)

        if (get_user == 'OAuth Token expired' or get_user == []):
            return []

        else:
            options['oauth_consumer_key'] = access_token
            options['creator'] = str(get_user['id'])
            options['show_tip'] = 'true'
            options['full_annotations'] = 'true'

            genesets_url = TRIBE_URL + '/api/v1/geneset/'

            tribe_connection = requests.get(genesets_url, params=options)
            result = tribe_connection.json()

            # The objects we want will be in the 'objects' key of the
            # response. Metadata for this response will be in the 'meta' key
            # of the response.
            genesets = result['objects']
            return genesets

    except:
        return []


def retrieve_user_geneset_versions(access_token, geneset):
    """
    Returns all versions that belong to a specific geneset
    (if user has access to that geneset)

    Arguments:
    access_token -- The OAuth token with which the user has access to
    their resources. This is a string of characters.

    geneset -- The resource URI for the desired geneset

    Returns:
    Either -

    a) A list of versions (as dictionaries), or
    b) An empty list, if the request failed.
    """

    try:
        parameters = {'oauth_consumer_key': access_token,
                      'geneset__id': geneset,
                      'xrdb': CROSSREF}

        versions_url = TRIBE_URL + '/api/v1/version/'
        tribe_connection = requests.get(versions_url, params=parameters)
        result = tribe_connection.json()

        # The objects we want will be in the 'objects' key of the response.
        # Metadata for this response will be in the 'meta' key of the response.
        versions = result['objects']
        return versions

    except:
        return []


def create_remote_geneset(access_token, geneset_info, tribe_url):
    """
    Creates a geneset in Tribe given a 'geneset_info' dictionary.

    Arguments:
    access_token -- The OAuth token with which the user has access to
    their resources. This is a string of characters.

    geneset_info -- The dictionary containing the values for the fields
    in the geneset that is going to be created in Tribe.

    tribe_url -- A string. URL of the Tribe instance where this geneset
    will be saved to.

    Returns:
    Either -

    a) The newly created geneset (as a dictionary), or
    b) An empty list, if the request failed.
    """
    # Get Tribe organism resource uri from the given scientific name
    organism_uri = get_organism_uri(geneset_info['organism'], tribe_url)
    geneset_info['organism'] = organism_uri

    headers = {'Authorization': 'OAuth ' + access_token,
               'Content-Type': 'application/json'}

    payload = json.dumps(geneset_info)
    genesets_url = tribe_url + '/api/v1/geneset'
    geneset_response = requests.post(genesets_url, data=payload,
                                     headers=headers)

    # If something went wrong and the geneset was not created
    # (making the response status something other than 201),
    # return the response as is given by Tribe
    if (geneset_response.status_code != 201):
        return geneset_response

    try:
        geneset_response = geneset_response.json()
        return geneset_response

    except ValueError:
        return geneset_response


def create_remote_version(access_token, version_info, tribe_url):
    """
    Creates a new version for an already existing geneset in Tribe.

    Arguments:
    access_token -- The OAuth token with which the user has access to
    their resources. This is a string of characters.

    version_info -- The dictionary containing the values for the fields
    in the version that is going to be created in Tribe. One of these
    is the resource_uri of the geneset this version will belong to.

    Returns:
    Either -

    a) The newly created version (as a dictionary), or
    b) An empty list, if the request failed.
    """

    headers = {'Authorization': 'OAuth ' + access_token,
               'Content-Type': 'application/json'}

    payload = json.dumps(version_info)
    versions_url = tribe_url + '/api/v1/version'
    version_response = requests.post(versions_url, data=payload,
                                     headers=headers)

    # If something went wrong and the version was not created
    # (making the response status something other than 201),
    # return the response as is given by Tribe
    if (version_response.status_code != 201):
        return version_response

    try:
        version_response = version_response.json()
        return version_response

    except ValueError:
        return version_response


def return_user_object(access_token):
    parameters = {'oauth_consumer_key': access_token}
    tribe_connection = requests.get(TRIBE_URL + '/api/v1/user',
                                    params=parameters)

    try:
        result = tribe_connection.json()
        return result
    except:
        result = '{"meta": {"previous": null, "total_count": 0, ' + \
                 '"offset": 0, "limit": 20, "next": null}, "objects": []}'
        result = json.loads(result)
        return result


def obtain_token_using_credentials(username, password, client_id,
                                   client_secret, access_token_url):

    payload = {'grant_type': 'password',
               'username': username,
               'password': password,
               'client_id': client_id,
               'client_secret': client_secret}

    r = requests.post(access_token_url, data=payload)
    tribe_response = r.json()
    return tribe_response['access_token']


def pickle_organism_public_genesets(organism, public_geneset_dest=None,
                                    max_gene_num=300):
    """
    Function to download all the public genesets available for an organism,
    and store their pickled form in a file.

    Arguments:
    organism -- A string, of the scientific name for the desired species

    public_geneset_dest --  Optional argument, a string. Location (including
    file name) of the file that will contain the pickled genesets. If
    this argument is not passed, the function will try to get the location
    from the PUBLIC_GENESET_DEST django setting. If this setting is not
    defined either, the function will log an error and quit, as it needs at
    least one of these two locations to be defined to know where to put
    the pickled genesets.

    max_gene_num -- Optional argument, an integer. If a geneset contains more
    this number of genes, it will get filtered out and not included in the
    pickle. The value passed can technically be a string, but only if it
    can be coerced into an integer (e.g. '300' instead of 300), as int() is
    called on this argument. However, if it can't be coerced, a ValueError is
    thrown.

    Returns:
    Nothing, it just writes the pickled genesets to the specified file.

    """

    # Apparently, Tribe does not like requests for more than 1500 genesets
    # at a time.
    go_public_genes = retrieve_public_genesets(
        {'show_tip': 'true', 'limit': '1500',
         'organism__scientific_name': organism, 'title__startswith': 'GO'},
        retrieve_all=True)

    kegg_public_genes = retrieve_public_genesets(
        {'show_tip': 'true', 'limit': '1500',
         'organism__scientific_name': organism, 'title__startswith': 'KEGG'},
        retrieve_all=True)

    omim_public_genes = retrieve_public_genesets(
        {'show_tip': 'true', 'limit': '1500',
         'organism__scientific_name': organism, 'title__startswith': 'DO'},
        retrieve_all=True)

    all_public_genesets = {'Gene Ontology': go_public_genes,
                           'KEGG': kegg_public_genes,
                           'OMIM': omim_public_genes}

    filtered_geneset_dict = {}
    allgenes = set()

    for gs_type, genesets in all_public_genesets.iteritems():

        # This next piece of code will filter out genesets that have more
        # than a certain number of genes (set by the max_gene_num parameter).
        # These large genesets probably would be computationally expensive to
        # handle and also not very biologically informative.
        # Also, the url for the geneset's "detail" page in Tribe is built for
        # each geneset and added to each geneset dictionary.
        filtered_genesets = []
        for geneset in genesets:

            gs_genes = set(geneset['tip']['genes'])

            if len(gs_genes) > int(max_gene_num):
                continue

            allgenes |= gs_genes

            creator = geneset['creator']['username']
            slug = geneset['slug']
            url = TRIBE_URL + '/#/use/detail/' + creator + '/' + slug
            geneset['url'] = url

            filtered_genesets.append(geneset)

        filtered_geneset_dict[gs_type] = filtered_genesets

    if not public_geneset_dest:
        public_geneset_dest = PUBLIC_GENESET_DEST

    if not public_geneset_dest:
        logger.error('Both the "public_geneset_dest" argument for this '
                     'function and the PUBLIC_GENESET_DEST setting have not '
                     'been defined, so no file with the pickled genesets is '
                     'is being written. Ending function.')
        quit()

    pickle.dump((filtered_geneset_dict, len(allgenes)),
                open(public_geneset_dest, 'wb'))
