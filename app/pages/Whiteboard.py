# Dashboard for high level business metrics.
# TODO want to figure out a better way to build db
# perhaps a loop, but difficult to include metrics

import calendar
import datetime
import gspread
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd

import requests
import streamlit as st
import time

from dotenv import load_dotenv
from ratelimit import limits


from src.utils import load_csv_data
from src.utils import create_otd_df
from src.utils import month_splits_2324
from src.utils import clean_accom_df
from src.utils import build_bullet

# Page and variable setup
st.set_page_config(page_title = "Whiteboard",
                   layout="wide")

load_dotenv()

api_id = os.getenv('api_id')
api_key = os.getenv('api_key')



def get_cognito_entry(entry_number):
    
    api_key = st.secrets["cognito_api_key"]

    url = f"https://www.cognitoforms.com/api/forms/14/entries/{entry_number}?access_token={api_key}"

    response = requests.get(url)
    st.write(response.json())
    return response.json()



# decorator to throttle api calls 
@limits(calls = 15, period = 120)
def call_gs_api(ebook_id, api_id, api_key):
    
    """
    Call API with wrapper only 15 calls
    per 2 min limit imposed
    Using API credentials

    """


    url = "https://api.roomboss.com/vendors/list?countryCode=JP&locationCode=NISEKO&lang=en"


    # response = requests.request("GET", url, headers=headers, data=payload)

    
    
    auth = (api_id, api_key)

    # response = requests.get(url, auth = auth, headers = {})

    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)



    if response.status_code != 200:
        st.write(f"{response.reason}\
                 {response.status_code}, check input")
        
    st.write(response.text)

    return response

def get_gsheet_data():
        
    gc = gspread.service_account()

    # Open google sheets
    sh = gc.open("All Bookings")

    # clear today sheet and update data
    cognito_sheet = sh.get_worksheet(2)
    
    data = cognito_sheet.get_all_values()
    headers = data.pop(0)
    df = pd.DataFrame(data, columns=headers)

    return df

def get_cognito_info(ebook_id, df):

    result = df.loc[df["HolidayNisekoReservationNumber"] == ebook_id]
    st.write(result)
# get_cognito_entry()

# call_gs_api(1694617, api_id, api_key)

get_cognito_entry(14)