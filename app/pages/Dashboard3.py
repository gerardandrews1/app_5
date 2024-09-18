# Season Dashboard for high level business metrics.
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
st.set_page_config(page_title = "Sales Dashboard",
                   layout="wide",
                   )
# Set up columns
row0 = st.columns(3)
row1 = st.columns(3)
row2 = st.columns(3)


# Get current month
# current_month = datetime.datetime.today().month
today_str = datetime.datetime.today().strftime('%b %d')


# Store queries for use later on
query_2324 = f""" Season == "'23/24'" """

query_2425 = f""" Season == "'24/25'" """


# TODO add more data sources and connect to analytics API

raw_df = load_csv_data("../../Downloads/Bookings Clean.csv")
accom_df = clean_accom_df(raw_df, "Start date")

otd_df = create_otd_df(accom_df, "Gross")

gs_df = load_csv_data("../../Downloads/GS Bookings Clean.csv")
gs_df.Created = pd.to_datetime(gs_df.Created)
otd_gs_df = create_otd_df(gs_df, "Gross")

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

all_books_df = load_csv_data("../../Downloads/All Bookings Clean.csv")
all_books_df = clean_accom_df(all_books_df, "Check In / Start")
all_books_accom = all_books_df[all_books_df["accom_flag"] == 1]
otd_all_books = create_otd_df(all_books_df, "Gross")

all_books_accom_2425 = all_books_accom.query(query_2425)
all_books_accom_2324 = all_books_accom.query(query_2324)

gs_sell_2425 = gs_df.query(query_2425)["Item Sell Price"].sum()
gssell_2324 = gs_df.query(query_2324)["Item Sell Price"].sum()
gs_sell_otd = otd_gs_df.query(query_2324)["Item Sell Price"].sum()


bookingdot_com = all_books_accom[\
                    (all_books_accom["Buyer Company"] == "RoomBoss Channel Manager") \
                    & (all_books_accom["ChannelAS2"] == "Booking.com")]\
                        .query(query_2425)

airbnb = all_books_accom[\
                    (all_books_accom["Buyer Company"] == "RoomBoss Channel Manager") \
                    & (all_books_accom["ChannelAS2"] == "Airbnb")]\
                        .query(query_2425)

airbnb_not_done = airbnb[airbnb["Lead Guest Email"].isna()].shape[0]

airbnb_percent_without_email = f"\
        {(airbnb_not_done/airbnb.shape[0])*100:,.0f}"
                                    

bookingdotcom_not_done = bookingdot_com[bookingdot_com["Lead Guest Email"]\
                                                    .astype(str).str\
                                                    .contains("booking.com")]\
                                                    .shape[0]
bookdotcom_percent_without_email = f"\
            {(bookingdotcom_not_done/bookingdot_com.shape[0])*100:,.0f}"


# Calculate number of unique bks with gs
accom_unique_ids = all_books_accom.query(query_2425)["Package ID"].unique().tolist()
    


gs_unique_ids = gs_df.query(query_2425)["Package ID"].unique().tolist()

bks_with_gs = len(set(gs_unique_ids) & set(accom_unique_ids))

percent_with_gs = int(round((bks_with_gs/len(accom_unique_ids)) * 100, 0))


count = all_books_accom.query(query_2425)["Package ID"]

with row0[0]:
        st.markdown(\
        f"""
        - ###### {bookdotcom_percent_without_email}% of booking.com have not emailed res
        - ###### {airbnb_percent_without_email}% of Airbnb have not emailed res
        - ###### {percent_with_gs}% of bookings have guest services worth {format_millions(gs_sell_2425)}""")



def season_hbars(fig, ax, rows, cols):

    """Make the season hbars """

    # Set a nice title
    ax[0][0].set_title(f"23/24 and 24/25 Totals", 
                        fontsize = 9,
                        loc = "left",
                        )
    
    ax[0][1].set_title(f"Increase", 
                    fontsize = 6,
                    loc = "left",
                    color = "#4C4646")
    
    # Get all the figures
    # gross_2324 = all_books_accom.query(query_2324).Gross.sum()
    # gross_otd_2324 = otd_df.query(query_2324).Gross.sum()

    gs_sell_2425 = gs_df.query(query_2425)["Item Sell Price"].sum()
    gs_sell_2324 = gs_df.query(query_2324)["Item Sell Price"].sum()
    gs_sell_otd = otd_gs_df.query(query_2324)["Item Sell Price"].sum()




    gross_2425 = all_books_accom.query(query_2425)["Item Sell Price"].sum()
    gross_2324 = all_books_accom.query(query_2324)["Item Sell Price"].sum()
    gross_otd_2324 = otd_all_books.query(query_2324)["Item Sell Price"].sum()

    
    bk_count_2324 = accom_df.query(query_2324).ID.nunique()
    bk_count_otd_2324 = otd_all_books.query(query_2324)["Package ID"].nunique()
    bk_count_2425 = all_books_accom.query(query_2425)["Package ID"].nunique()


    nights_2324 = accom_df.query(query_2324).Nights.sum()
    nights_otd_2324 = otd_df.query(query_2324).Nights.sum()
    nights_2425 = accom_df.query(query_2425).Nights.sum()


    

    # Add figures to dict for easy graphing
    season_dict = {
        "Gross" : [gross_2425, gross_otd_2324, gross_2324],
        "Nights" : [nights_2425, nights_otd_2324, nights_2324],
        "Bookings" : [bk_count_2425, bk_count_otd_2324, bk_count_2324],
        "GS": [gs_sell_2425, gs_sell_otd, gs_sell_2324]
        }
    
    # Make the plots
    count = 1
    ax_count = 0
    for x, y in season_dict.items():
        
        plt.subplot(4,2,count)
        
        # Helper function to plot hbars
        build_hbars(ax[ax_count][0],
                    y,
                    x)
        
        add_bar_labels(ax[ax_count][0], y[2])
        count += 1
        ax_count += 1


    # Plot the x factors
    plot_xfactors(season_dict, rows, cols)

    # Add bar labels
    



    pass


def channel_breakdown():

    

    # fig, ax = single_hbar_setup(f"Sales Channel")
    fig, ax = plt.subplots(
                        sharex = True,
                        figsize = (6, 2.5)
                        )
    
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
    
    ax.set_title(
            f" Sales Channel",
            size = 9,
            loc = "left"
            )
    
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
    
    channel_gross = all_books_accom.query(query_2425)\
        .groupby("ChannelAS2")\
        ["Item Sell Price", "Count"]\
        .sum() \
        .reset_index()
    
    channel_gross = channel_gross\
                            .sort_values(['Item Sell Price'],
                                        ascending = False)\
                            .reset_index(drop=True)
    
    channel_gross = channel_gross[channel_gross["ChannelAS2"] != "308828553"]
    
    ax.bar(channel_gross["ChannelAS2"], 
            channel_gross["Item Sell Price"],
             color = "#4571c4",
              )
    
    
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


def country_breakdown():
     
    country_counts_2425 = all_books_accom_2425[["Package ID",
                                                "Item Sell Price",
                                                "Lead Guest Residency"]]
    
    country_counts_2425.drop_duplicates(inplace = True)
    country_counts_2425["Count"] = 1
    total = country_counts_2425.shape[0]
    total_sell = country_counts_2425["Item Sell Price"].sum()

    country_gb = country_counts_2425.groupby("Lead Guest Residency", dropna = False)\
                                                [["Item Sell Price", "Count"]]\
                                                    .sum()\
                                                    .reset_index()
    
    country_gb.sort_values("Item Sell Price", 
                           inplace = True,
                           ascending = False)

    country_gb["% Total Bookings"] =  round((country_gb["Count"] / total)*100,1)
    country_gb["% Total Sell"] =  round((country_gb["Item Sell Price"] / total_sell)*100,1)

    result = country_gb.nlargest(8, columns = "Item Sell Price")


    result.loc[len(result)] = \
        ['Others', 
         country_gb.loc[~country_gb["Lead Guest Residency"]\
                                           .isin(result["Lead Guest Residency"]),
                                           "Item Sell Price"].sum(),
        country_gb.loc[~country_gb["Lead Guest Residency"]\
                                           .isin(result["Lead Guest Residency"]),
                                           "Count"].sum(),
        100 - result["% Total Bookings"].sum(),
        100 - result["% Total Sell"].sum()]
    

    result["Avg book"] = round(result["Item Sell Price"] / result.Count, 0) 

    # result["Item Sell Price"] = result["Item Sell Price"].apply(format_millions)
    result = result[["Lead Guest Residency",
                     "Count",
                     "Item Sell Price",
                     "% Total Bookings",
                     "% Total Sell",
                     "Avg book"]]
    
    st.dataframe(result, hide_index = True)

    fig, ax = plt.subplots(
                        sharex = True,
                        figsize = (6, 2.5)
                        )
    
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
    
    ax.set_title(
            f" Sales Channel",
            size = 9,
            loc = "left"
            )
    
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
    
    # ax.bar(
    #     result["Lead Guest Residency"], 
    #     result["Item Sell Price"],
    #     color = "#4571c4",
    #     )
    
    return fig
    
def managed_nonmanaged():
    fig, ax = plt.subplots(
                # width_ratios=[10, 1],
                sharex = True,
                figsize = (6, 2.5))
    
    
    management_df = accom_df.query(f"""Season == "'24/25'" """)\
                                   [["ID", "HN_Prop","Gross", "Count"]]\
                                    .drop_duplicates()

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


def non_managed_breakdown():
     
    fig, ax = single_hbar_setup(f"Non-managed Breakdown")


    non_managed_df = accom_df.query(f"""HN_Prop == 0 &\
                                    Season == "'24/25'" \
                                    """)
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
 
country_fig = country_breakdown()


# with row1[1]: st.dataframe(country_counts_2324.head(7))
# with row1[1]: st.dataframe(country_counts_2425.head(7))

season_fig, season_ax = plot_setup(4,2)

season_hbars(season_fig, season_ax, 4, 2)

channel_graph = channel_breakdown()

managed_nonmanaged_fig = managed_nonmanaged()
non_managed_fig = non_managed_breakdown()

with row1[0]: st.pyplot(season_fig)

with row1[0]: st.pyplot(channel_graph)
with row1[2]: st.pyplot(managed_nonmanaged_fig)
with row1[2]: st.pyplot(non_managed_fig)
