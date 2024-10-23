# Dashboard for high level business metrics.
# TODO want to figure out a better way to build db
# perhaps a loop, but difficult to include metrics

import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st
import time

from dotenv import load_dotenv
from plotly.subplots import make_subplots

from src.utils import load_csv_data
from src.utils import create_otd_df
from src.utils import month_splits_2324
from src.utils import clean_accom_df
from src.utils import clean_payments_df
from src.utils import highlight_unpaid
from src.utils import highlight_unpaid_inv


# Page and variable setup
st.set_page_config(page_title = "Bookings & Payments",
                   layout="wide")

# Set up columns
row0 = st.columns(1)
row1 = st.columns(2)
row2 = st.columns(2)

current_month = datetime.datetime.today().month
today = datetime.datetime.today()


# Import data sources
# Accom bookings
raw_accom = load_csv_data("../../Downloads/All Bookings Clean.csv")
accom_df = clean_accom_df(raw_accom, "Check In / Start")

# Payments
payments_raw = load_csv_data("../../Downloads/Invoices and Payments Clean.csv")
payments_df = clean_payments_df(payments_raw)



payments_df.sort_values(by = "Due Date", 
                        ascending = True,
                        inplace = True)


payments_df = payments_df[(payments_df["Due Date"] < today) | \
                          (payments_df["Due Date"] < (today + pd.Timedelta(days = 14)))]

payments_df = payments_df[payments_df["Due Date"] > pd.to_datetime("2024-09-01")]
payments_df = payments_df[payments_df["Payment Amount"] == 0]


# payments_df = payments_df[payments_df["Payment Amount"] == 0]
payments_df = payments_df[payments_df["Booking Status"] == "Active"]


payments_df = payments_df[[
                "Booking ID",
                "Invoice ID",
                "Lead Guest",
                 "Due Date",
                "Invoice Amount",
                "Vendor",
                "Package Start Date",
                "HN_Prop",
                "Invoice Date",
                "Created By",
            ]]

payments_html =  payments_df.style.format({
                "Due Date": lambda x: "{}".format(x.strftime("%d %b %Y")),
                
                "Invoice Amount": "¥{:,.0f}",
                }).apply(highlight_unpaid_inv, axis = 1)


def make_accom_report(accom_df):
      
    """Create the humna readable df for the streamlit report page"""

    accom_df["ID"] = accom_df["Booking ID"].astype(str)
    accom_df = accom_df[accom_df.accom_flag == 1]

    # Cast to datetime and keep it to only last x days
    accom_df["Check In"] = pd.to_datetime(accom_df["Check In / Start"]).dt.date
    accom_df["Created"] = pd.to_datetime(accom_df["Created (Japan Standard Time)"])
    accom_df = accom_df[accom_df["Created"] > (today - pd.Timedelta(days=45))]

    # Cut columns down to size
    accom_df = accom_df[[
                    "Created", 
                    "ID",
                    "Custom ID",
                    "Lead Guest Name",
                    "ChannelAS2", 
                    "Vendor",
                    "Check In", 
                    "Nights/Days", 
                    "Item Sell Price",
                    "Managed by",
                    "Option 1", 
                    "Lead Guest Residency",
                    "Package Invoiced Amount",
                    "Package Received Amount",
                    "Difference"
                    ]]


    # Rename columns for humans

    accom_df.rename(
        columns={
            "Lead Guest Name":"Guest",
            "ChannelAS2":"Sales Channel",
            "Vendor": "Property",
            "Nights/Days": "Nights",
            "Item Sell Price": "Gross",
            "Option 1": "Guests",
            "Lead Guest Residency": "Country",
            "Package Invoiced Amount": "Invoiced",
            "Package Received Amount": "Received"},
        inplace=True)

    accom_df.sort_values(
                    by = "Created", 
                    ascending = False,
                    inplace = True)

    # Use styler to format nicely
    accom_html =  accom_df.style.format({"Created": lambda x: "{}".format(x.strftime("%d %b -- %H:%M")),
                                                "Gross": "¥{:,.0f}",
                                                "Invoiced": "¥{:,.0f}",
                                                "Received": "¥{:,.0f}",
                                                "Difference": "¥{:,.0f}"

                                                }).apply(highlight_unpaid, axis = 1)

    return accom_html

accom_df_24 = accom_df.query("""Season == "'24/25'" """)
not_balanced = accom_df_24[(accom_df.Difference > 0 ) | (accom_df.Difference < 0 )]

not_balanced = not_balanced[not_balanced.Vendor != "Neyuki"]


accom_html = make_accom_report(accom_df)


with row0[0]:
        tab1, tab2, tab3 = st.tabs(["Recent Bookings",
                                     "Payments",
                                     "Not Balanced"  ])


with tab1:
    st.dataframe(accom_html, hide_index = True, use_container_width = True, height = 380)

    
with st.sidebar:
      st.text_input("Enter booking ID")
#
with tab2:
    st.dataframe(payments_html, hide_index = True, use_container_width = True, height = 500)

with tab3:
     st.dataframe(not_balanced[[   
                    "Created", 
                    "Booking ID",
                    "Package Invoiced Amount",
                    "Package Received Amount",
                    "Difference",
                    "Custom ID",
                    "Lead Guest Name",
                    "ChannelAS2", 
                    "Vendor",
                    
                    "Nights/Days", 
                    "Item Sell Price",
                    "Managed by",
                    "Option 1", 
                    "Lead Guest Residency",
                    
                    ]])

# st.dataframe(accom_html, hide_index = True, use_container_width = False, height = 380)




