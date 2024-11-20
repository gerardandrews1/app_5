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

def test_gspread_connection():
    st.write("Starting connection test...")
    
    try:
        # Step 1: Check if secrets are accessible
        st.write("1. Checking secrets...")
        try:
            # Print first few characters of key values to verify they exist
            st.write(f"Project ID: {st.secrets['general']['project_id'][:10]}...")
            st.write(f"Client Email: {st.secrets['general']['client_email'][:15]}...")
            st.write("✅ Secrets are accessible")
        except Exception as e:
            st.error(f"❌ Error accessing secrets: {str(e)}")
            return
            
        # Step 2: Set up credentials
        st.write("2. Setting up credentials...")
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive']
                
        credentials_dict = {
            "type": st.secrets["general"]["type"],
            "project_id": st.secrets["general"]["project_id"],
            "private_key_id": st.secrets["general"]["private_key_id"],
            "private_key": st.secrets["general"]["private_key"],
            "client_email": st.secrets["general"]["client_email"],
            "client_id": st.secrets["general"]["client_id"],
            "auth_uri": st.secrets["general"]["auth_uri"],
            "token_uri": st.secrets["general"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["general"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["general"]["client_x509_cert_url"]
        }
        
        try:
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scope
            )
            st.write("✅ Credentials created successfully")
        except Exception as e:
            st.error(f"❌ Error creating credentials: {str(e)}")
            return
            
        # Step 3: Authorize gspread
        st.write("3. Authorizing gspread...")
        try:
            client = gspread.authorize(credentials)
            st.write("✅ Gspread authorized successfully")
        except Exception as e:
            st.error(f"❌ Error authorizing gspread: {str(e)}")
            return
            
        # Step 4: Try to access a spreadsheet
        st.write("4. Attempting to access spreadsheet...")
        try:
            # First, list all spreadsheets the service account has access to
            spreadsheets = client.list_spreadsheet_files()
            st.write("Available spreadsheets:")
            for sheet in spreadsheets:
                st.write(f"- {sheet['name']}")
                
            # Try to open your specific spreadsheet
            if 'gcp_service_account' in st.secrets and 'sheet_name' in st.secrets['gcp_service_account']:
                sheet_name = st.secrets['gcp_service_account']['sheet_name']
                spreadsheet = client.open(sheet_name)
                st.write(f"✅ Successfully opened spreadsheet: {sheet_name}")
            else:
                st.warning("⚠️ No sheet_name specified in secrets")
                
        except Exception as e:
            st.error(f"❌ Error accessing spreadsheet: {str(e)}")
            return
            
        st.success("🎉 All connection tests passed!")
        
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

# Run the test
st.title("Gspread Connection Test")
if st.button("Run Connection Test"):
    test_gspread_connection()

# Display requirements
st.sidebar.write("Requirements:")
st.sidebar.code("""
pip install gspread
pip install google-auth
""")

# Display important notes
st.sidebar.write("Important checks:")
st.sidebar.markdown("""
1. Make sure the Google Sheet is shared with the service account email
2. Enable Google Sheets API in Google Cloud Console
3. Enable Google Drive API in Google Cloud Console
4. Check that your service account has the correct permissions
""")