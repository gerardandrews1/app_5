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

raw_df = load_csv_data("../../Downloads/Bookings Clean.csv")
accom_df = clean_accom_df(raw_df, remove_zero = False)
accom_df["Start date"] = pd.to_datetime(accom_df["Start date"])
accom_df["End date"] = pd.to_datetime(accom_df["End date"])


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

dec_start = pd.to_datetime("2024-12-15")
mar_finish = pd.to_datetime("2025-03-20")

total_nights = (mar_finish - dec_start).days

accom_df_2425 = accom_df.query(f""" Season =="'24/25'" & \
                                  HN_Prop == 1 """)

accom_df_2425["Zero Nights"] = np.where(accom_df_2425["Zero Stay"] == 1, accom_df_2425.Nights, 0)

accom_df_2425["Zero Nights"] = np.where((accom_df_2425["Start date"].between(dec_start, mar_finish)) & \
                                        (accom_df_2425["End date"].between(dec_start, mar_finish)),
                                        accom_df_2425["Zero Nights"],
                                        0)

# 1 if start date greater than 15 dec and less than 20 Mar
#       Nights.sum()

# 2 if start date < 15 dec & end date > 15 dec 
    # end date - dec 15

# 3 if end date > mar 20 & start date < mar 20 
    # mar 20 - start date

accom_df_2425["first_period"] = 0
accom_df_2425["first_period"] = \
    np.where((accom_df_2425["Start date"].between(dec_start, mar_finish)) & \
             (accom_df_2425["End date"].between(dec_start, mar_finish)), \
             (accom_df_2425["End date"] - accom_df_2425["Start date"]).dt.days, \
             accom_df_2425["first_period"])

# Before 15 dec and past dec 15
accom_df_2425["second_period"] = 0
accom_df_2425["second_period"] = \
    np.where((accom_df_2425["Start date"] < dec_start) & \
             (accom_df_2425["End date"].between(dec_start, mar_finish)), \
             (accom_df_2425["End date"] - dec_start).dt.days,
             accom_df_2425["second_period"])


accom_df_2425["Peak Nights"] = accom_df_2425.first_period + accom_df_2425.second_period
accom_df_2425.ID = accom_df_2425["ID"].astype(str)


# accom_df_2425.first_period = accom_df_2425["first_period"].astype(str)
# accom_df_2425.second_period = accom_df_2425["second_period"].astype(str)
# accom_df_2425.second_period = accom_df_2425["third_period"].astype(str)

# st.write(accom_df_2425.columns)

# st.write(accom_df_2425[["ID", "Lead Guest", "Start date", "End date", "first_period",
#                         "second_period", ]])
                        # "second_period", "third_period"]])

gb_rooms = accom_df_2425.groupby(["Vendor", "Product"])["Gross","Peak Nights", "Zero Nights"] \
                            .sum() \
                            .reset_index()

kick_vendors = ["Snowbird Studios",
                "Holiday Niseko",
                "Ezo Yuki"
                ]


kick_products = ["Koyuki 3 - 3 Bed 2 Bath"]

gb_rooms = gb_rooms[~gb_rooms.Vendor.isin(kick_vendors)]
gb_rooms = gb_rooms[~gb_rooms.Product.isin(kick_products)]


gb_rooms.Gross = round(gb_rooms.Gross.astype(int) * 0.000001, 2)
gb_rooms["Available Nights"] = total_nights - gb_rooms["Peak Nights"]
gb_rooms["Peak Occupancy"] = round((gb_rooms["Peak Nights"] / total_nights) * 100, 1)


gb_rooms = gb_rooms[["Vendor",
                     "Product",
                     "Gross",
                     "Available Nights",
                     "Peak Occupancy",
                     "Zero Nights"]]
st.write(gb_rooms)