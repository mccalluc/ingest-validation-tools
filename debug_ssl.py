#!/usr/bin/env python3

import requests
import logging
from http.client import HTTPConnection

# Enabling debugging at http.client level (requests->urllib3->http.client)
# you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# the only thing missing will be the response.body which is not logged.
    
HTTPConnection.debuglevel = 1

logging.basicConfig()  # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

requests.get('https://www.uniprot.org/uniprot/G9N9I7')
