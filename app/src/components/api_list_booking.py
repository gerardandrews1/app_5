# module to call the API list booking functionality
import os
import json
import requests
import streamlit as st

from ratelimit import limits



# api call function
@limits(calls = 15, period = 120)
def call_api(ebook_id, api_id, api_key):
    
    """
    Call API with wrapper only 15 calls
    per 2 min limit imposed
    Using API credentials
    """
    url = f"https://api.roomboss.com/extws/hotel/v1/listBooking?bookingEid={ebook_id}"
    
    auth = (api_id, api_key)
    
    response = requests.get(url, auth = auth)

    if response.status_code != 200:
        st.write(f"Error {response.status_code}")
        # raise Exception('API response: {}'.format(response.status_code))

    return response

