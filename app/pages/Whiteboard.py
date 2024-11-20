# Dashboard for high level business metrics.
# TODO want to figure out a better way to build db
# perhaps a loop, but difficult to include metrics

import calendar
import datetime
import gspread
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

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

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def get_cognito_data():
    # Define scope
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_info(
        st.secrets["general"],
        scopes=scope
    )
    
    gc = gspread.authorize(credentials)
    
    # Open using the direct spreadsheet ID
    sheet = gc.open_by_key('1HcE08poobjoIpJEvSD9t1SLrFsRGGnJDCk-ANAky6q4')
    
    # Get the CognitoExport worksheet
    worksheet = sheet.worksheet('CognitoExport')
    
    # Get all data
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

st.title('Cognito Export Data')

try:
    # Load the data
    df = get_cognito_data()
    
    # Display basic info
    st.write(f"Total rows: {len(df)}")
    st.write("Columns:", list(df.columns))
    
    # Show first few rows
    st.write("First 5 rows:")
    st.dataframe(df.head())
    
    # Add some basic filtering options
    if len(df.columns) > 0:
        selected_column = st.selectbox("Select column to filter", df.columns)
        unique_values = df[selected_column].unique()
        selected_value = st.selectbox(f"Select {selected_column}", unique_values)
        
        filtered_df = df[df[selected_column] == selected_value]
        st.write(f"Filtered data for {selected_column} = {selected_value}")
        st.dataframe(filtered_df)

except Exception as e:
    st.error(f"Error: {str(e)}")
    st.write("Debug info:")
    st.write("Spreadsheet ID: 1HcE08poobjoIpJEvSD9t1SLrFsRGGnJDCk-ANAky6q4")
    st.write("Service Account:", st.secrets["general"]["client_email"])