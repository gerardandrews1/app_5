# Dashboard for high level business metrics.
# TODO want to figure out a better way to build db
# perhaps a loop, but difficult to include metrics

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

from src.utils import load_csv_data
from src.utils import create_otd_df
from src.utils import month_splits_2324
from src.utils import clean_accom_df
from src.utils import build_bullet

# Page and variable setup
st.set_page_config(page_title = "Whiteboard",
                   layout="wide")

# Set up columns
row0 = st.columns(2)
row1 = st.columns(2)
row2 = st.columns(2)

current_month = datetime.datetime.today().month

# TODO add more data sources and connect to analytics API

raw_df = load_csv_data("../../Downloads/All Bookings Clean.csv")
accom_df = clean_accom_df(raw_df, "Check In / Start", remove_zero = False)
accom_df["Check In / Start"] = pd.to_datetime(accom_df["Check In / Start"])
accom_df["Check Out / End"] = pd.to_datetime(accom_df["Check Out / End"])
accom_df = accom_df[accom_df["accom_flag"] == 1]



otd_df = create_otd_df(accom_df, "Gross")

gs_df = load_csv_data("../../Downloads/GS Bookings Clean.csv")
gs_df.Created = pd.to_datetime(gs_df.Created)

# Enquiries
enq_df = load_csv_data("../../Downloads/Enquiries Clean.csv")
enq_df["Enquiry Date"] = pd.to_datetime(enq_df["Enquiry Date"])
enq_df["Count"] = 1

enq_df = enq_df[["Enquiry Date", "Email", "Property",
                "Check In", "Check Out", "Nights", "Adults",
                "Bedrooms", "Country", "Season", "Count"]]

enq_df["Stay Period"] = 0
enq_df = month_splits_2324(enq_df, "Check In", "2324")
enq_df = month_splits_2324(enq_df, "Check In", "2425")

# Mailchimp
mc_df = load_csv_data("../../Downloads/Mailchimp.csv")
mc_df["Send Time"] = pd.to_datetime(mc_df["Send Time"])

# Google Analytics
ga_2023 = load_csv_data("../../Backups/GA2023.csv")
ga_2024 = load_csv_data("../../Backups/GA2024.csv")

ga_2024.Date = pd.to_datetime(ga_2024.Date)
ga_2023.Date = pd.to_datetime(ga_2023.Date)


##############  #################

def calc_peak_nights():

    dec_start = pd.to_datetime("2024-12-15")
    mar_finish = pd.to_datetime("2025-03-20")

    total_nights = (mar_finish - dec_start).days

    accom_df_2425 = accom_df.query(f""" Season =="'24/25'" & \
                                    HN_Prop == 1 """)

    accom_df_2425["Zero Nights"] = np.where(accom_df_2425["Zero Stay"] == 1,
                                            accom_df_2425["Nights/Days"],
                                            0)

    accom_df_2425["Zero Nights"] = np.where(
        (accom_df_2425["Check In / Start"].between(dec_start, mar_finish)) & \
        (accom_df_2425["Check Out / End"].between(dec_start, mar_finish)),
        accom_df_2425["Zero Nights"],
        0)

    # 1 if Check In / Start greater than 15 dec and less than 20 Mar
    #       Nights.sum()

    # 2 if Check In / Start < 15 dec & Check Out / End > 15 dec 
        # Check Out / End - dec 15

    # 3 if Check Out / End > mar 20 & Check In / Start < mar 20 
        # mar 20 - Check In / Start

    accom_df_2425["first_period"] = 0
    accom_df_2425["first_period"] = \
        np.where((accom_df_2425["Check In / Start"].between(dec_start, mar_finish)) & \
                (accom_df_2425["Check Out / End"].between(dec_start, mar_finish)), \
                (accom_df_2425["Check Out / End"] - accom_df_2425["Check In / Start"]).dt.days, \
                accom_df_2425["first_period"])

    # Before 15 dec and past dec 15
    accom_df_2425["second_period"] = 0
    accom_df_2425["second_period"] = \
        np.where((accom_df_2425["Check In / Start"] < dec_start) & \
                (accom_df_2425["Check Out / End"].between(dec_start, mar_finish)), \
                (accom_df_2425["Check Out / End"] - dec_start).dt.days,
                accom_df_2425["second_period"])


    accom_df_2425["Peak Nights"] = accom_df_2425.first_period + \
                                   accom_df_2425.second_period
    
    
    accom_df_2425["Package ID"] = accom_df_2425["Package ID"].astype(str)


    gb_rooms = accom_df_2425.groupby(
                    ["Vendor", "Room/Resource"])["Item Sell Price",
                                                 "Peak Nights",
                                                 "Zero Nights"] \
                                                    .sum() \
                                                    .reset_index()

    # Some lists used to filter our long stays/season bookings
    kick_vendors = [#"Snowbird Studios",
                    "Holiday Niseko",
                    "Ezo Yuki",
                    "Yuki no Taki 2",
                    ]


    kick_primary_key = [
                        "Asuka 5 - 10 8",
                        "Snowbird Studios 10"
                        ]

    # Create column to kick those out of rental pool
    gb_rooms["primary_key"] = gb_rooms["Vendor"] + " " +\
                                    gb_rooms["Room/Resource"].astype(str)


    # Kick the rooms we don't want in the calculation
    gb_rooms = gb_rooms[~gb_rooms.Vendor.isin(kick_vendors)]

    gb_rooms = gb_rooms[~gb_rooms["primary_key"].isin(kick_primary_key)]


    gb_rooms["Item Sell Price"] = round( \
        gb_rooms["Item Sell Price"].astype(int) * 0.000001, 2)
    
    gb_rooms["Available Nights"] = total_nights - gb_rooms["Peak Nights"]
    
    gb_rooms["Peak Occupancy"] = round((gb_rooms["Peak Nights"] / \
                                        total_nights) * 100, 1)


    gb_rooms = gb_rooms[[
                    "Vendor",
                    "Room/Resource",
                    "Item Sell Price",
                    "Peak Nights",
                    "Available Nights",
                    "Peak Occupancy",
                    "Zero Nights"
                    ]]

    percent_full_peak = (gb_rooms.shape[0]*total_nights) - \
                         gb_rooms["Peak Nights"].sum()
    
    peak_occupancy = (gb_rooms["Peak Nights"].sum()) /( gb_rooms.shape[0]*total_nights)
    st.write(peak_occupancy)
    avail_nights_left = gb_rooms["Available Nights"].sum()


    st.write(avail_nights_left) 

    st.dataframe(gb_rooms, hide_index = True)
    return gb_rooms["Available Nights"].sum(), 


# st.write(gb_rooms["Peak Nights"].sum() / (gb_rooms.shape[0]*total_nights) ) 

calc_peak_nights()