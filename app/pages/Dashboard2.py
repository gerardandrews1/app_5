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
from src.utils import build_hbars
from src.utils import plot_xfactors
from src.utils import formatter
from src.utils import plot_setup
from src.utils import format_millions

# Page and variable setup
st.set_page_config(page_title = "Sales Dashboard",
                   layout="wide")



# Set up columns
row0 = st.columns(3)
row1 = st.columns(3)
row2 = st.columns(3)

current_month = datetime.datetime.today().month

# TODO add more data sources and connect to analytics API

raw_df = load_csv_data("../../Downloads/Bookings Clean.csv")
accom_df = clean_accom_df(raw_df)

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


# Get current month
current_month_name = datetime.datetime.now().strftime("%b")
current_month = datetime.datetime.today().month
today_str = datetime.datetime.today().strftime('%b %d')


# Store queries for use later on
monthly_query_2425 = f""" Season == "'24/25'" and \
                `Booking Month` == {current_month}"""

monthly_query_2324 = f""" Season == "'23/24'" and \
                `Booking Month` == {current_month}"""

query_2324 = f""" Season == "'23/24'" """

query_2425 = f""" Season == "'24/25'" """


# Activates first plot



############## Monthly Totals

def season_bullets(fig, ax):

    """Make the season hbars not bullets"""

    # Set a nice title
    ax[0][0].set_title(f"23/24 & 24/25 Totals", 
                        fontsize = 7,
                        loc = "left",
                        )
    
    ax[0][1].set_title(f"Increase", 
                    fontsize = 5,
                    loc = "left",
                    color = "#4C4646")
    
    # Get all the figures
    gross_2324 = accom_df.query(query_2324).Gross.sum()
    gross_otd_2324 = otd_df.query(query_2324).Gross.sum()
    gross_2425 = accom_df.query(query_2425).Gross.sum()

    bk_count_2324 = accom_df.query(query_2324).ID.nunique()
    bk_count_otd_2324 = otd_df.query(query_2324).ID.nunique()
    bk_count_2425 = accom_df.query(query_2425).ID.nunique()

    nights_2324 = accom_df.query(query_2324).Nights.sum()
    nights_otd_2324 = otd_df.query(query_2324).Nights.sum()
    nights_2425 = accom_df.query(query_2425).Nights.sum()

    # Add figures to dict for easy graphing
    season_dict = {
        "Gross" : [gross_2425, gross_otd_2324, gross_2324],
        "Bookings" : [bk_count_2425, bk_count_otd_2324, bk_count_2324],
        "Nights" : [nights_2425, nights_otd_2324, nights_2324]}
    
    # Make the plots
    count = 1
    ax_count = 0
    for x, y in season_dict.items():
        
        plt.subplot(3,2,count)
        
        # Helper function to plot hbars
        build_hbars(ax[ax_count][0],
                    y,
                    x)

        count += 1
        ax_count += 1


    # Plot the x factors
    plot_xfactors(season_dict)

    pass

def monthly_bullets(fig, ax):
    
    """Create the top left square of DB"""

    # Make a nice title
    ax[0][0].set_title(f"{current_month_name} Totals", 
                        fontsize = 7,
                        loc = "left")
    ax[0][1].set_title(f"Increase", 
                        fontsize = 5,
                        loc = "left",
                        color = "#4C4646")

    #####

    # Get figures for graphing
    monthly_gross = accom_df.query(monthly_query_2425).Gross.sum()
    monthly_count = accom_df.query(monthly_query_2425).ID.nunique()
    monthly_nights = accom_df.query(monthly_query_2425).Nights.sum()

    # OTD
    otd_gross = otd_df.query(monthly_query_2324).Gross.sum()
    otd_monthly_count = otd_df.query(monthly_query_2324).ID.nunique()
    otd_monthly_nights = otd_df.query(monthly_query_2324).Nights.sum()

    # Get last year month totals
    month_gross_2023 = accom_df.query(monthly_query_2324).Gross.sum()

    month_count_2023 = accom_df.query(monthly_query_2324).ID.nunique()

    month_nights_2023 = accom_df.query(monthly_query_2324).Nights.sum()

    month_dict = {
        "Gross" : [monthly_gross, otd_gross, month_gross_2023],
        "Bookings" : [monthly_count, otd_monthly_count, month_count_2023],
        "Nights" : [monthly_nights, otd_monthly_nights, month_nights_2023]}

    count = 1
    ax_count = 0
    for x, y in month_dict.items():
        
        plt.subplot(3,2,count)
        
        # Helper function to plot hbars
        build_hbars(ax[ax_count][0],
                    y,
                    x)

        count += 1
        ax_count += 1


    # Plot the x factors
    plot_xfactors(month_dict)


    pass


def monthly_channel():

    fig = plt.figure(figsize = (10,4))




    channel_gross = accom_df.query(monthly_query_2425)\
        .groupby("ChannelAS2")\
        ["Gross", "Count"]\
        .sum() \
        .reset_index()
    
    channel_gross = channel_gross.sort_values(['Gross'], ascending = False).reset_index(drop=True)

    ax = sns.barplot(
            data = channel_gross, 
            x = 'ChannelAS2',
            y = 'Gross',
            palette = ["#D4D4D4"])

    for i in ax.containers:
        ax.bar_label(i,
                     fmt = format_millions,
                     color = "#4C4646")
        
    fig.axes[0].set_xlabel("")
    fig.axes[0].set_ylabel("")

    fig.axes[0].spines[["top", "left", "right", "bottom"]].set_visible(False)
    fig.axes[0].yaxis.set_major_formatter(formatter)
    fig.axes[0].tick_params(
                                top=False,
                                bottom=True,
                                left=False,
                                right=False,
                                labelleft=False,
                                labelbottom=True,
                                labelsize = 10,
                                color = "#D4D4D4",
                                labelcolor = "#4C4646",
                                length = 1,
                                pad = 1)

    return fig

monthly_fig, month_ax = plot_setup(3,2)
monthly_bullets(monthly_fig, month_ax)
season_fig,season_ax = plot_setup(3,2)
season_bullets(season_fig,season_ax)
month_channel = monthly_channel()

with row1[0]: st.pyplot(monthly_fig)

with row0[0]: st.pyplot(season_fig)

with row2[0]: st.pyplot(month_channel)
                                   
