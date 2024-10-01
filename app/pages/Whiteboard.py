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

def calc_nights():

    """Calculate how many nights bookable in Dec
       
       broken down by room
    """
# 2002, 1)
    winter_periods = [[2024, 12, "early_dec", "late_dec"],
                     [2025, 1, "early_jan", "late_jan"],
                     [2025, 2, "early_feb", "late_feb"],
                     [2025, 3, "early_mar", "late_mar"]]



    start_end_dates = {
        "early_dec" : [pd.to_datetime("2024-12-01"), pd.to_datetime("2024-12-15")],
        "late_dec" : [pd.to_datetime("2024-12-16"), pd.to_datetime("2024-12-31")],
        "early_jan" : [pd.to_datetime("2025-01-01"), pd.to_datetime("2025-01-15")],
        "late_jan" : [pd.to_datetime("2025-01-16"), pd.to_datetime("2025-01-31")],
        "early_feb" : [pd.to_datetime("2025-02-01"), pd.to_datetime("2025-02-14")],
        "late_feb" : [pd.to_datetime("2025-02-15"), pd.to_datetime("2025-02-28")],
        }
    
    
    
    # for month in winter_periods:

    #     # Get the first last day of month
    #     first_week_day, last_day = calendar.monthrange(month[0],
    #                                                    month[1])
        
    #     middle_day = (last_day // 2) + 1
        
    #     # Make the date strings
    #     month_start = f"{str(month[0])}-{str(month[1])}-01"
    #     month_middle = f"{str(month[0])}-{str(month[1])}-{str(middle_day)}"
    #     month_end = f"{str(month[0])}-{str(month[1])}-{str(last_day)}"
        
    #     # Convert to datetime
    #     month_start = pd.to_datetime(month_start) 
    #     month_middle = pd.to_datetime(month_middle)
    #     month_end = pd.to_datetime(month_end)

    #     st.write(middle_day)
    #     start_end_dates[month[2]] = [month_start, month_middle]
    #     start_end_dates[month[3]] = [month_middle, month_end]

    
    accom_df_2425 = accom_df.query(f""" Season =="'24/25'" & \
                                    HN_Prop == 1 """)

    accom_df_2425["Zero Nights"] = np.where(accom_df_2425["Zero Stay"] == 1,
                                            accom_df_2425["Nights/Days"],
                                            0)
    
    accom_df_2425["Last Night"] = accom_df_2425["Check Out / End"] - pd.Timedelta(days = 1)

    for key, value in start_end_dates.items():

        accom_df_2425[key] = 0

   
        # start and end date both in the period 
        accom_df_2425[key] = \
            np.where((accom_df_2425["Check In / Start"].between(value[0], value[1])) & \
                    (accom_df_2425["Last Night"].between(value[0], value[1])), \
                    (accom_df_2425["Check Out / End"] - accom_df_2425["Check In / Start"]).dt.days , \
                    accom_df_2425[key])

        # start date in month but goes into next month
        accom_df_2425[key] = \
            np.where((accom_df_2425["Check In / Start"].between(value[0], value[1])) & \
                    (accom_df_2425["Last Night"] > value[1]),  \
                    (value[1] - accom_df_2425["Check In / Start"]).dt.days +1,
                    accom_df_2425[key])

        # start date in last month but finishes this month
        accom_df_2425[key] = \
            np.where((accom_df_2425["Check In / Start"] < value[0]) & \
                (accom_df_2425["Last Night"].between(value[0], value[1])), \
                (accom_df_2425["Check Out / End"] - value[0]).dt.days ,
                accom_df_2425[key])
        
        # # start date before month and end date after month
        # # TODO It's this one that's causing the error
        # if "early" in key:

        accom_df_2425[key] = \
                        np.where((accom_df_2425["Check In / Start"] < value[0]) & \
                        (accom_df_2425["Last Night"] > value[1]),  \
                        (value[1] - value[0]).days +1,
                        accom_df_2425[key])

        # else:

        #     accom_df_2425[key] = \
        #             np.where((accom_df_2425["Check In / Start"] < value[0]) & \
        #             (accom_df_2425["Check Out / End"] > value[1]),  \
        #             (value[1] - value[0]).days,
        #             accom_df_2425[key])
            
        # # To fix those starting on the middle day of the month    
        # if "late" in key:
            
    #     accom_df_2425[key] = \
    #     np.where((accom_df_2425["Check In / Start"] == value[0]),  
    #         accom_df_2425[key] - 1,
    #         accom_df_2425[key])

    accom_df_2425["Last Night"] = accom_df_2425["Last Night"].dt.date

    st.write(accom_df_2425[["Vendor",
                            "Check In / Start",
                            "Last Night",
                            "Check Out / End",
                            "early_dec",
                            "late_dec",
                            "early_jan",
                            "late_jan"]])
    #                                              "late_jan"]])
        
    # st.write(accom_df_2425[["Vendor","Check In / Start", "Check Out / End", "early_dec",
    #                                              "late_dec",
    #                                              "early_jan",
    #                                              "late_jan",
    #                                              "early_feb",
    #                                              "late_feb",
    #                                              "early_mar",
    #                                              "late_mar"]])
    
    
    # # Finally a groupby to bring all together    
    gb_rooms = accom_df_2425.groupby(
                    ["Vendor", "Room/Resource"])["Item Sell Price",
                                                 "early_dec",
                                                 "late_dec",
                                                 "early_jan",
                                                 "late_jan",
                                                #  "early_feb",
                                                #  "late_feb",
                                                #  "early_mar",
                                                #  "late_mar"] \
                                                ] \
                                                    .sum() \
                                                    .reset_index()
    
    # # Some lists used to filter our long stays/season bookings
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
    st.write(gb_rooms)


    cols = ["period", "occupancy"]
    occupancy = []

    for k, v  in start_end_dates.items():
        
        occupancy.append([k,
                         gb_rooms[k].sum()/ \
                        (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1))])
        st.write(k)
        st.write(gb_rooms[k].sum()/ \
                 (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1)))
        
        
    final_df = pd.DataFrame(occupancy, columns = cols)
        
    st.write(final_df)

        
calc_nights()
# calc_peak_nights()