import datetime
import glob
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import seaborn as sns
import streamlit as st

from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
from plotly.subplots import make_subplots
# from streamlit_gsheets import GSheetsConnection
# conn = st.connection("gsheets", type=GSheetsConnection)
# df = conn.read()


from src.utils import load_csv_data
from src.utils import create_otd_df
from src.utils import month_splits_2324
from src.utils import clean_accom_df
from src.utils import build_hbars
from src.utils import plot_xfactors
from src.utils import formatter
from src.utils import plot_setup
from src.utils import format_millions
from src.utils import add_bar_labels
from src.utils import single_hbar_setup
from src.utils import single_hbar_labels


st.set_page_config(
                page_title = "Accom Bookings",
                layout="wide"
                )

# load env variables from file
load_dotenv()
hn_id = os.getenv("api_id")
hn_key = os.getenv("api_key")


# Want to add other data sources soon
raw_file = load_csv_data("../../Downloads/All Bookings Clean.csv")
accom_df = clean_accom_df(raw_file, "Check In / Start")

accom_df["Booking ID"] = accom_df["Booking ID"].astype(str)
accom_df = accom_df[accom_df.accom_flag == 1]

################ SIDEBAR ###################
channels = ["All",
            "Book & Pay",
            "HN Staff",
            "Airbnb",
            "Booking.com",
            "Expedia"
            ]

channel = st.sidebar.multiselect(
                "Select the Channel",
                options = channels,
                default= "All"
                )

if "All" in channel:
    channel = channels

seasons = accom_df["Season"].unique().tolist()

season = st.sidebar.multiselect(
                    "Filter by Season",
                    options = seasons,
                    default = "'24/25'")

winter_months = [
                "-All",
                "November",
                "December",
                "January", 
                "February",
                "March",
                "April",
                "May"]

stay_month = st.sidebar.multiselect(
    "Select stay month",
    options = winter_months,
    default = ["-All"]
)

if "-All" in stay_month:
    stay_month = accom_df["Stay Month"].unique().tolist()


property_list = accom_df["Vendor"].unique().tolist()
property_list.insert(0,"-All")

vendor = st.sidebar.multiselect(
    "Filter by Property",
    options = sorted(property_list, key = str.lower),
    default = "-All"     
    )

if "-All" in vendor:
    vendor = accom_df["Vendor"].unique().tolist()


######## OWNER AND ZERO STAYS #############
zero_stays = st.sidebar.multiselect(
        "Exclude owner and zero stays",
        options = ["Yes", "No"],
        default = ["Yes"]
)

if "Yes" in zero_stays:
    zero_stays = [0]

elif "No" in zero_stays:
    zero_stays = [1,0]


########## MANAGED VS NON MANAGED #################
hn_prop = [0, 1]

management_list = sorted(accom_df["Managed by"].unique().tolist())
management_list.insert(0,"Non-managed")

management_list.insert(0,"-All")

managed = st.sidebar.multiselect(
                "Select Management",
                options = management_list,
                default = "-All"
                )

if "Non-managed" in managed:
    hn_prop = 0
    managed = management_list

if "-All" in managed:
    managed = management_list


df_selection = accom_df.query(
   """
   Vendor == @vendor & \
   Season == @season & \
   ChannelAS2 == @channel & \
   `Stay Month` == @stay_month &  \
   `Zero Stay` in  @zero_stays & \
   `Managed by` == @managed & \
   HN_Prop == @hn_prop 
   """
   )


df_selection = df_selection[["Created (Japan Standard Time)", 
                             "Booking ID",
                             "Custom ID",
                             "Lead Guest Name",
                             "ChannelAS2", 
                             "Vendor",
                             "Product", 
                             "Lead Guest Email",
                             "Check In / Start", 
                             "Check Out / End",
                             "Nights/Days", 
                             "Item Sell Price",
                             "Managed by",
                             "Option 1", 
                             "Season",
                             "Lead Guest Residency",
                             "Notes",
                             "HN_Prop",
                             "Message",
                             "Zero Stay",
                             "Booking Month", 
                             "Booking Year", 
                             "Package Invoiced Amount",
                             "Difference",
                             "Package Received Amount",
                             "accom_flag"
                             ]]



st.write(f"Gross: ¥{df_selection['Item Sell Price'].sum():,.0f}")
st.write(f"Bookings: {df_selection['Booking ID'].nunique()}")
st.write(f"Nights Booked: {df_selection['Nights/Days'].sum():,}")

df_selection.sort_values(
                by = "Check In / Start",
                ascending = True,
                inplace = True)

st.dataframe(df_selection, 1400, 700, hide_index = True) 
