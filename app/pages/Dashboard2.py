# Monthly Dashboard for high level business metrics.
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
from src.utils import add_bar_labels
from src.utils import single_hbar_setup
from src.utils import single_hbar_labels

# Page and variable setup
st.set_page_config(page_title = "Monthly Sales Dashboard",
                   layout="wide",
                   )


month_list = [1, 2, 3, 4, 5, 6, 7, 8, 9]
current_month = st.sidebar.multiselect(
    "Filter by month",
    options= month_list,
    default=8     
    )

# Get current month
current_month_name = datetime.date(2024, current_month[0], 1).strftime("%B")
# current_month = datetime.datetime.today().month
today_str = datetime.datetime.today().strftime('%b %d')


# Set up columns
row0 = st.columns(3)
row1 = st.columns(3)
row2 = st.columns(3)

# current_month = datetime.datetime.today().month

# TODO add more data sources and connect to analytics API

raw_df = load_csv_data("../../Downloads/Bookings Clean.csv")
accom_df = clean_accom_df(raw_df, "Start date")

otd_df = create_otd_df(accom_df, "Gross")

gs_df = load_csv_data("../../Downloads/GS Bookings Clean.csv")
gs_df.Created = pd.to_datetime(gs_df.Created)

# Enquiries
enq_df = load_csv_data("../../Downloads/Enquiries Clean.csv")
enq_df["Enquiry Date"] = pd.to_datetime(enq_df["Enquiry Date"])
enq_df["Count"] = 1

enq_df = enq_df[["Enquiry Date", "Email", "Property", "Enquiry Month",
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


# # Get current month
# current_month_name = datetime.datetime.now().strftime("%b")
# # current_month = datetime.datetime.today().month
# today_str = datetime.datetime.today().strftime('%b %d')


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
    ax[0][0].set_title(f"23/24 and 24/25 Totals", 
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
        
        add_bar_labels(ax[ax_count][0], y[2])
        count += 1
        ax_count += 1


    # Plot the x factors
    plot_xfactors(season_dict, 3, 2)

    # Add bar labels
    



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
        
        add_bar_labels(ax[ax_count][0], y[2])

        count += 1
        ax_count += 1

    # Add bar labels
    # add_bar_labels(ax)
    plt.margins(x=0)
    # Plot the x factors
    plot_xfactors(month_dict, 3, 2)


    pass


def monthly_channel():

    

    fig, ax = single_hbar_setup(f"{current_month_name} Sales Channel")



    channel_gross = accom_df.query(monthly_query_2425)\
        .groupby("ChannelAS2")\
        ["Gross", "Count"]\
        .sum() \
        .reset_index()
    
    channel_gross = channel_gross.sort_values(['Gross'], ascending = True).reset_index(drop=True)
    channel_gross = channel_gross[channel_gross["ChannelAS2"] != "308828553"]
    
    ax.barh(channel_gross["ChannelAS2"], 
            channel_gross["Gross"],
             color = "#4571c4",
              height = 0.75 )
    # ax = sns.barplot(
    #         data = channel_gross, 
    #         y = 'ChannelAS2',
    #         x = 'Gross',
    #         width = 0.70,
    #         palette = ["#4571c4"],
    #         orient = "h")

    for i in ax.containers:
        ax.bar_label(i,
                     fmt = format_millions,
                     color = "#4C4646",
                     size = 6.5)
        

    

    return fig


def monthly_bk_rate():


    fig_bkrates, ax =  plt.subplots(
                                    # width_ratios=[10, 1],
                                    sharex = True,
                                    figsize = (6, 2.5))

    weekly_df = accom_df.query(f"""Season =="'24/25'" and \
                               (`Booking Month` == {current_month} \
                               and `Booking Month` < 12) \
                               and `Booking Year` == 2024 """) \
                        .groupby(["Season", 
                                  pd.Grouper(key = "Created",
                                             freq="D")])["ID"] \
                        .nunique() \
                        .reset_index() \
                        .sort_values("Created")
    plt.bar(weekly_df["Created"],
         weekly_df.ID,
         color = '#DEDEDE', 
         )
    month_day_fmt = mdates.DateFormatter('%d') # 
    month_ticks = mdates.MonthLocator()
    ax.get_xaxis().set_major_formatter(month_day_fmt)    
    # ax.get_xaxis().set_major_locator(month_ticks) 

    # st.write(weekly_df)
    ax.tick_params(
                top=False,
                bottom=True,
                left=False,
                right=False,
                labelleft=False,
                labelbottom=True,
                labelsize = 6,
                color = "#D4D4D4",
                labelcolor = "#4C4646",
                length = 1,
                pad = 1)
    
    ax.spines[["top", "left", "right", "bottom"]].set_visible(False)
    ax.set_title(f" {current_month_name} Bookings per day",
                 size = 9,
                 loc = "left")

    for i in ax.containers:
        ax.bar_label(i,
                     fmt = int,
                     color = "#4C4646",
                     size = 5)


    return fig_bkrates

def monthly_enq_rate():

    fig_enqrates, ax =  plt.subplots(
                                    # width_ratios=[10, 1],
                                    sharex = True,
                                    figsize = (6, 2.5))
    st.write(enq_df.columns)
    weekly_enq_2425 = enq_df.query(f"""`Enquiry Date` > '2023-12-01' and \
                               Season == "'24/25'" and \
                               `Enquiry Month` == {current_month}""") \
                .groupby(["Season", pd.Grouper(key = "Enquiry Date", freq = "D")])["Email"] \
                .nunique() \
                .reset_index() \
                .sort_values("Enquiry Date")
    
    plt.bar(weekly_enq_2425["Enquiry Date"],
         weekly_enq_2425.Email,
         color = '#DEDEDE', 
         )
    
    month_day_fmt = mdates.DateFormatter('%d') # 
    month_ticks = mdates.MonthLocator()
    ax.get_xaxis().set_major_formatter(month_day_fmt)    
    # ax.get_xaxis().set_major_locator(month_ticks) 

    # st.write(weekly_df)
    ax.tick_params(
                top=False,
                bottom=True,
                left=False,
                right=False,
                labelleft=False,
                labelbottom=True,
                labelsize = 6,
                color = "#D4D4D4",
                labelcolor = "#4C4646",
                length = 1,
                pad = 1
                )
    
    ax.spines[["top", "left", "right", "bottom"]].set_visible(False)
    ax.set_title(f" {current_month_name} Enquiries per day",
                 size = 9,
                 loc = "left")

    for i in ax.containers:
        ax.bar_label(i,
                     fmt = int,
                     color = "#4C4646",
                     size = 5)


    return fig_enqrates

def man_nonman():
    
    fig, ax = plt.subplots(
                # width_ratios=[10, 1],
                sharex = True,
                figsize = (6, 2.5))
    
    
    management_df = accom_df.query(f"""Season == "'24/25'" and \
                                   `Booking Month` == {current_month} """)\
                                   [["ID", "HN_Prop","Gross", "Count"]].drop_duplicates()

    management_gb = management_df\
                    .groupby("HN_Prop")["Gross","Count"]\
                    .sum()\
                    .reset_index()
    
    management_gb["HN_Prop"] = management_gb["HN_Prop"].replace(0, "Non-managed")  
    management_gb["HN_Prop"] = management_gb["HN_Prop"].replace(1, "Managed")  

    plt.bar(management_gb["HN_Prop"],
            management_gb["Gross"],
            width = 0.2,
            align = "center")
    
    # st.write(weekly_df)
    ax.tick_params(
                top=False,
                bottom=True,
                left=False,
                right=False,
                labelleft=False,
                labelbottom=True,
                labelsize = 6,
                color = "#D4D4D4",
                labelcolor = "#4C4646",
                length = 1,
                pad = 1)
    
    ax.spines[["top", "left", "right", "bottom"]].set_visible(False)
    ax.set_title(f"Managed and Non-managed",
                 size = 8,
                 loc = "left")
    
    plt.xlim(-0.9,1.9)

    single_hbar_labels(ax)

    return fig




    plt.subplots()


def non_managed_channel():

    fig, ax = single_hbar_setup(f"{current_month_name} Non-managed Gross")


    non_managed_df = accom_df.query(f"""HN_Prop == 0 &\
                                    Season == "'24/25'" &\
                                    `Booking Month` == {current_month}""")
    non_managed = non_managed_df.groupby(["Managed by"])["Gross"]\
                                .sum()\
                                .reset_index()

    non_managed = non_managed.sort_values(['Gross'], ascending = True)
        
    ax.barh(non_managed["Managed by"], 
            non_managed["Gross"],
            color = "#4571c4",
            )

    
    single_hbar_labels(ax)
    
    return fig
    

nm_fig = non_managed_channel()

monthly_fig, month_ax = plot_setup(3,2)
monthly_bullets(monthly_fig, month_ax)
season_fig,season_ax = plot_setup(3,2)
season_bullets(season_fig,season_ax)
month_channel = monthly_channel()

with row1[0]: st.pyplot(monthly_fig)

with row0[0]: st.pyplot(season_fig)

with row2[0]: st.pyplot(month_channel)
                                   
bk_rate = monthly_bk_rate()
enq_rate = monthly_enq_rate()
man_fig = man_nonman()
with row0[1]: st.pyplot(bk_rate)
with row1[1]: st.pyplot(enq_rate)
with row1[2]: st.pyplot(man_fig)
with row2[2]: st.pyplot(nm_fig)