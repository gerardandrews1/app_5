# Dashboard for high level business metrics.
# TODO want to figure out a better way to build db
# perhaps a loop, but difficult to include metrics

import calendar
import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import seaborn as sns
import streamlit as st
import time

from dotenv import load_dotenv
from plotly.subplots import make_subplots
from ratelimit import limits


from src.utils import load_csv_data
from src.utils import create_otd_df
from src.utils import month_splits_2324
from src.utils import clean_accom_df
from src.utils import build_bullet

# Page and variable setup
st.set_page_config(page_title = "Whiteboard",
                   layout="wide")



def get_cognito_entry(entry_number):
    
    api_key = st.secrets["cognito_api_key"]

    url = f"https://www.cognitoforms.com/api/forms/11/entries/{entry_number}?access_token={api_key}"

    response = requests.get(url)

    return response.json()




# decorator to throttle api calls 
@limits(calls = 15, period = 120)
def call_gs_api(ebook_id, api_id, api_key):
    
    """
    Call API with wrapper only 15 calls
    per 2 min limit imposed
    Using API credentials

    
    """

    url = \
    f"https://api.roomboss.com/packages/{ebook_id}"
    
    
    auth = (api_id, api_key)
    
    response = requests.get(url, auth = auth, headers = {})

    if response.status_code != 200:
        st.write(f"{response.reason}\
                 {response.status_code}, check input")
        
    st.write(response.text)

    return response

call_gs_api(1363430,
            st.secrets["api_id"],
            st.secrets["api_key"]
            )

