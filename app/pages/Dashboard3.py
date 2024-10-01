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
top_row = st.columns((0.8,0.6,0.6,0.6,0.6,0.6))
row0 = st.columns((5,2.4))
# row1 = st.columns(3)
# row2 = st.columns(3)


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
# st.write(airbnb_not_done)
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




def bookings_enq_rate():
        
    fig_rates,  (ax0, ax1) = plt.subplots(2, 2,
                                        width_ratios=[10, 1],
                                        sharex = True,
                                        figsize = (10, 3))



    plt.subplot(2, 2, 1)

    epoch = time.time()
    # today_date
    dt = datetime.datetime.utcfromtimestamp(epoch)

    idx = (dt.weekday() + 1) % 7
    sun = dt - datetime.timedelta(days=idx)
    sun = sun + pd.offsets.DateOffset(days=1)
    sun = sun.strftime("%Y-%m-%d")


    weekly_df = all_books_accom_2425.query(f"(`Booking Month` > 3 and \
                                           `Booking Month` < 12) \
                                            and `Booking Year` == 2024 and \
                                            Created < '{sun}' """) \
                        .groupby(["Season", pd.Grouper(key = "Created", freq="W-SUN")])\
                            ["Booking ID"] \
                                .nunique() \
                                .reset_index() \
                                .sort_values("Created")

    weekly_df_2324 = all_books_accom_2324.query("""(`Booking Month` > 3 and \
                                                 `Booking Month` < 12) \
                                    and `Booking Year` == 2023""") \
                        .groupby(["Season", pd.Grouper(key = "Created", freq="W-SUN")])["Booking ID"] \
                        .nunique() \
                        .reset_index() \
                        .sort_values("Created")



    # USe this to change to same year so can plot on same graph
    weekly_df_2324["Created_delta"] = weekly_df_2324["Created"] + pd.offsets.DateOffset(years=1)

    month_day_fmt = mdates.DateFormatter('%b') # "Locale's abbreviated month name. + day of the month"
    month_ticks = mdates.MonthLocator()
    fig_rates.get_axes()[0].get_xaxis().set_major_formatter(month_day_fmt)    
    fig_rates.get_axes()[0].get_xaxis().set_major_locator(month_ticks)    

    plt.axhline(y = 20, 
                xmin= 0.1,
                xmax= 0.6,
                linestyle = "--",
                color = "#D4D4D4",
                linewidth = 1)

    plt.plot(weekly_df_2324["Created_delta"],
            weekly_df_2324["Booking ID"],
            color = '#DEDEDE', 
            )


    plt.plot(weekly_df["Created"],
            weekly_df["Booking ID"],
            color = '#4571c4', 
            alpha = 0.8
            )



    fig_rates.get_axes()[0].get_xaxis().set_tick_params(labelsize = 8, 
                                                        which = 'both',
                                                        color = '#D4D4D4')


    plt.text(x = pd.to_datetime("2024-01-05"), y = 18, s = "20/ week", fontsize = 7, color = "grey")
    plt.text(x = weekly_df.Created.values[-1], 
            y = weekly_df["Booking ID"].values[-1] - 10,
            s = weekly_df["Booking ID"].values[-1],
            fontsize = 7,
            color = "#4571c4" )  

    fig_rates.get_axes()[0].spines[[ "left", "right", ]].set_visible(False)
    fig_rates.get_axes()[0].spines[['top', 'bottom']].set_color('#D4D4D4')

    fig_rates.get_axes()[1].spines[[ "left", "right", "top" ]].set_visible(False)
    fig_rates.get_axes()[1].spines['bottom'].set_color('#D4D4D4')
    # fig_rates.get_axes()[2].spines['top'].set_color('#D4D4D4')


    fig_rates.get_axes()[0].set_ylabel("Bookings", 
                                    rotation = 0,
                                    fontdict = {"fontsize": 8} ,
                                    loc = "center",
                                    labelpad = 25)


    fig_rates.get_axes()[0].set_yticklabels([])
    fig_rates.get_axes()[0].set_yticks([])
    fig_rates.get_axes()[1].set_yticklabels([])
    fig_rates.get_axes()[1].set_yticks([])

    fig_rates.get_axes()[0].set_title("2024 Weekly Rates vs 2023",
                                    fontdict = {"fontsize": 10},
                                    loc = 'left',
                                    pad = 10)
    
    plt.subplot(2, 2, 3)
    plt.ylim([10,50])



    weekly_enq_2324 = enq_df.query(f"""`Enquiry Date` > '2023-02-28' and Season == "'23/24'" \
                                and `Enquiry Date` < '2023-12-31' """) \
                    .groupby(["Season", pd.Grouper(key = "Enquiry Date", freq = "W-SUN")])["Email"] \
                    .nunique() \
                    .reset_index() \
                    .sort_values("Enquiry Date")

    weekly_enq_2425 = enq_df.query(f"""(`Enquiry Date` > '2024-02-29' and `Enquiry Date` < '{sun}') \
                                and Season == "'24/25'" \
                                and `Enquiry Date` > '2023-12-31' """) \
                    .groupby(["Season", pd.Grouper(key = "Enquiry Date", freq = "W-SUN")])["Email"] \
                    .nunique() \
                    .reset_index() \
                    .sort_values("Enquiry Date")

    weekly_enq_2324["Enquiry_delta"] = weekly_enq_2324["Enquiry Date"] + pd.offsets.DateOffset(years=1)



    plt.axhline(y = 20, 
                xmin= 0.1,
                xmax = 0.6,
                linestyle = "--",
                color = "#D4D4D4",
                linewidth = 1)

    plt.plot(weekly_enq_2324["Enquiry_delta"],
            weekly_enq_2324.Email,
            color = '#DEDEDE',
            )

    plt.plot(weekly_enq_2425["Enquiry Date"],
            weekly_enq_2425.Email,
            color = '#4571c4',
            alpha = 0.8
            )

    plt.text(x = weekly_enq_2425["Enquiry Date"].values[-1],
            y = weekly_enq_2425["Email"].values[-1] + 3,
            s = weekly_enq_2425["Email"].values[-1],
            fontsize = 7,
            color = '#4571c4')
    plt.text(x = pd.to_datetime("2024-01-05"), y = 19, s = "20/ week", fontsize = 7, color = "grey")



    fig_rates.get_axes()[2].get_xaxis().set_major_formatter(month_day_fmt)    


    fig_rates.get_axes()[2].get_xaxis().set_tick_params(labelsize = 8, 
                                                        which = 'both',
                                                        color = '#D4D4D4')
    fig_rates.get_axes()[2].tick_params(bottom = True)
    fig_rates.get_axes()[2].spines[[ "left", "right"]].set_visible(False)
    fig_rates.get_axes()[2].spines['bottom'].set_color('#D4D4D4')
    fig_rates.get_axes()[3].spines[["top", "left", "right"]].set_visible(False)
    fig_rates.get_axes()[2].spines[['top', 'bottom']].set_color('#D4D4D4')

    fig_rates.get_axes()[2].set_ylabel("Web Enquiries", 
                                    rotation = 0,
                                    fontdict = {"fontsize": 8} ,
                                    loc = "center",
                                    labelpad = 35)
    fig_rates.get_axes()[2].set_yticklabels([])
    fig_rates.get_axes()[2].set_yticks([])
    fig_rates.get_axes()[3].set_yticklabels([])
    fig_rates.get_axes()[3].set_yticks([])



    return fig_rates


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
    with top_row[0]:
        with st.container(border = False):
            st.markdown("### Winter 2024/25 Sales")        

    with top_row[1]:
        with st.container(border = True):
            st.metric(
            "Gross Sales",
            format_millions(gross_2425),
            f"{int(((gross_2425 - gross_otd_2324)/gross_otd_2324)*100)}% - OTD {format_millions(gross_otd_2324)}",
            help = "Green represents total on this day in 2023"
        )

    with top_row[2]:
        with st.container(border=True):
            st.metric(
            "Nights",
            f"{nights_2425:,}",
            f"{int(((nights_2425 - nights_otd_2324)/nights_otd_2324)*100)}% - {nights_otd_2324:,}"
            )
    
    with top_row[3]:
            with st.container(border=True):
                st.metric(
                    "Bookings",
                    f"{bk_count_2425:,}",
                    f"{int(((bk_count_2425 - bk_count_otd_2324)/bk_count_otd_2324)*100)}% - {bk_count_otd_2324:,}"
                    )

    with top_row[4]:
        with st.container(border=True):
            st.metric(
                "Guest Services",
                f"{format_millions(gs_sell_2425)}",
                f"{int(((gs_sell_2425 -gs_sell_otd)/gs_sell_otd)*100)}% - {format_millions(gs_sell_otd)}"
            )

    
    pass


def channel_breakdown():

    

    # fig, ax = single_hbar_setup(f"Sales Channel")
    fig, ax = plt.subplots(
                        sharex = True,
                        figsize = (6, 3)
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
            labelleft=True,
            labelbottom=False,
            labelsize = 6,
            color = "#D4D4D4",
            labelcolor = "#4C4646",
            length = 1,
            pad = 1
            )
    
    channel_gross = all_books_accom.query(query_2425)\
        .groupby("ChannelAS2")\
        ["Item Sell Price", "Count", "Nights/Days"]\
        .sum() \
        .reset_index()
    
    channel_gross = channel_gross\
                            .sort_values(['Item Sell Price'],
                                        ascending = False)\
                            .reset_index(drop=True)
    
    channel_gross = channel_gross[channel_gross["ChannelAS2"] != "308828553"]

    channel_gross["Avg booking"] = round(channel_gross["Item Sell Price"] / \
                                    channel_gross["Count"], -4) 

    channel_gross["Gross"] = round(channel_gross["Item Sell Price"] * 0.000001,1)


    st.write(channel_gross)
    
    ax.barh(
        channel_gross["ChannelAS2"], 
        channel_gross["Item Sell Price"],
        color = "#4571c4",
        # width = 0.5
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
        

    fig.tight_layout()

    return channel_gross


def country_breakdown():
     
    country_counts_2425 = all_books_accom_2425[["Package ID",
                                                "Item Sell Price",
                                                "Lead Guest Residency",
                                                "Nights/Days"]]
    
    country_counts_2425.drop_duplicates(inplace = True)
    country_counts_2425["Count"] = 1
    total = country_counts_2425.shape[0]
    total_sell = country_counts_2425["Item Sell Price"].sum()

    country_gb = country_counts_2425.groupby("Lead Guest Residency", dropna = False)\
                                                [["Item Sell Price", "Count","Nights/Days"]]\
                                                    .sum()\
                                                    .reset_index()
    
    country_gb.sort_values("Item Sell Price", 
                           inplace = True,
                           ascending = False)

    # st.write(country_gb)
    country_gb["% of Bookings"] =  round((country_gb["Count"] / total)*100,1)
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
        country_gb.loc[~country_gb["Lead Guest Residency"]\
                                            .isin(result["Lead Guest Residency"]),
                                            "Nights/Days"].sum(),
        100 - result["% of Bookings"].sum(),
        100 - result["% Total Sell"].sum(),
        ]
    
    result["Avg booking"] = round(result["Item Sell Price"] / result.Count, 0)


    result = result[["Lead Guest Residency",
                     "Count",
                     "Item Sell Price",
                     "% of Bookings",
                     "% Total Sell",
                     "Avg booking",
                     "Nights/Days"]]
    
    result["Gross"] = round(result["Item Sell Price"] * 0.000001, 1)

    result.sort_values("Item Sell Price", ascending = False, inplace = True)
    fig, ax = plt.subplots(
                        sharex = True,
                        figsize = (6, 2.5)
                        )
    
    ax.spines[["top", "left", "right", "bottom"]].set_visible(False)
    
    ax.set_title(
            f" Sales by Country",
            size = 9,
            loc = "left"
            )
    
    ax.tick_params(
            top=False,
            bottom=False,
            left=False,
            right=False,
            labelleft=True,
            labelbottom=False,
            labelsize = 6,
            color = "#D4D4D4",
            labelcolor = "#4C4646",
            length = 1,
            pad = 1
            )
    
    result["Lead Guest Residency"] = result["Lead Guest Residency"]\
                                            .fillna(value = "Unknown")

        #  result[["Lead Guest Residency", "% Total Bookings", "Item Sell Price"]],
         
    ax.barh(
        result["Lead Guest Residency"],
        result["Item Sell Price"],
        
        color = "#4571c4",
        )
    for i in ax.containers:
    
        ax.bar_label(

            i,
            fmt = format_millions,
            color = "#242124",
            size = 6
            )

    fig.tight_layout()
    return result
    
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
     
    fig, ax = plot_setup(1, 2)

    ax[0].set_title(f"Non Managed", 
                        fontsize = 9,
                        loc = "left",
                        )
    
    ax[1].set_title(f"% of Sales", 
                        fontsize = 8,
                        loc = "left",
                        )
    
    ax[0].tick_params(
                    top=False,
                    bottom=False,
                    left=False,
                    right=False,
                    labelleft=True,
                    labeltop = False,
                    labelbottom=False,
                    labelsize = 6,
                    color = "#4C4646",
                    labelcolor = "#4C4646",
                    length = 1,
                    pad = 1)
    
    ax[1].tick_params(
                    top=False,
                    bottom=False,
                    left=False,
                    right=False,
                    labelleft=False,
                    labelright = True,
                    labeltop = False,
                    labelbottom=False,
                    labelsize = 6,
                    color = "#4C4646",
                    labelcolor = "#4C4646",
                    length = 1,
                    pad = 1)
    
    non_managed_total_23 = all_books_accom_2324.query("HN_Prop == 0")\
                                                    ["Item Sell Price"].sum()
    
    non_managed_total_23_otd = otd_all_books.query(f"""HN_Prop == 0 & \
                                                   {query_2324}""")\
                                                   ["Item Sell Price"].sum()
    
    non_managed_total_24 = all_books_accom_2425.query("HN_Prop == 0")\
                                                    ["Item Sell Price"].sum()

    non_managed_df = all_books_accom_2425.query(f"""HN_Prop == 0 &\
                                    Season == "'24/25'" \
                                    """)

    non_managed_gb = non_managed_df.groupby(["Managed by"])\
                                                    [["Item Sell Price",
                                                     "Count",
                                                     "Item Buy Price",
                                                     "Nights/Days"]]\
                                .sum()\
                                .reset_index()


    
    non_managed_gb["Avg booking"] = non_managed_gb["Item Sell Price"] / non_managed_gb["Count"]
    non_managed_gb["Avg booking"] = round(non_managed_gb["Avg booking"],-4)

    non_managed_gb["Commission"] = round(non_managed_gb["Item Sell Price"] - \
                                         non_managed_gb["Item Buy Price"],
                                         -4)
    
    

    # Plot    
    ax[0].barh(non_managed_gb["Managed by"], 
            non_managed_gb["Item Sell Price"],
            color = "#4571c4",
            )
    
    single_hbar_labels(ax[0])


    non_managed_perc_24 = (non_managed_gb["Item Sell Price"].sum() / \
                        all_books_accom_2425["Item Sell Price"].sum())

    non_managed_perc_23 = (non_managed_total_23 / \
                        all_books_accom_2324["Item Sell Price"].sum())
    

    
    ax[1].bar(0, 
              non_managed_perc_24,
              width = 0.3,
              label = [""],
              color = "#4571c4")
    ax[1].bar(0.5, 
              non_managed_perc_23,
              width = 0.3,
              label = [""],
              color = "#4571c4")

    ax[1].hlines(non_managed_perc_23, 
                 xmin = -0.1,
                 xmax = 0.1,
                 color = "#DEDEDE",
                 linewidth = 1)

    # Set the tick for 2023 % 
    ax[1].set_yticks([non_managed_perc_23],
                      labels = [f"{round(non_managed_perc_23 *100,1)}%"])

    label = [f"{round(non_managed_perc_24 * 100, 1)}%"]


    for i in ax[1].containers:
        
        ax[1].bar_label(

                i,
                label,
                color = "#242124",
                size = 6
                )


    with top_row[5]:
        with st.container(border=True):
            st.metric(
                "Non-managed Sales",
                format_millions(non_managed_total_24),
                f"{int(((non_managed_total_24 - non_managed_total_23_otd)/ non_managed_total_23_otd)*100)}%  -\
                    {format_millions(non_managed_total_23_otd)}",
                   )

    
    st.write(non_managed_gb)
    non_managed_gb["Item Sell Price"] = round(non_managed_gb["Item Sell Price"] * 0.000001,2)
    non_managed_gb = non_managed_gb.sort_values(['Item Sell Price'],
                                                 ascending = False)

    return non_managed_gb
 
def calc_nights():

    """Calculate how many nights bookable in Dec
       
       broken down by room
    """

    start_end_dates = {
        "early_dec" : [pd.to_datetime("2024-12-01"), pd.to_datetime("2024-12-15")],
        "late_dec" : [pd.to_datetime("2024-12-16"), pd.to_datetime("2024-12-31")],
        "early_jan" : [pd.to_datetime("2025-01-01"), pd.to_datetime("2025-01-15")],
        "late_jan" : [pd.to_datetime("2025-01-16"), pd.to_datetime("2025-01-31")],
        "early_feb" : [pd.to_datetime("2025-02-01"), pd.to_datetime("2025-02-14")],
        "late_feb" : [pd.to_datetime("2025-02-15"), pd.to_datetime("2025-02-28")],
        "early_mar" : [pd.to_datetime("2025-03-01"), pd.to_datetime("2025-03-15")],
        "late_mar" : [pd.to_datetime("2025-03-16"), pd.to_datetime("2025-03-31")],
        }
    
    accom_df_2425 = all_books_accom_2425.query(f""" Season =="'24/25'" & \
                                    HN_Prop == 1 """)
    
    accom_df_2425["Check In / Start"] = pd.to_datetime(accom_df_2425["Check In / Start"])
    accom_df_2425["Check Out / End"] = pd.to_datetime(accom_df_2425["Check Out / End"])

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

       
    accom_df_2425["Last Night"] = accom_df_2425["Last Night"].dt.date

    st.write(accom_df_2425[["Vendor",
                            "Check In / Start",
                            "Last Night",
                            "Check Out / End",
                            "early_dec",
                            "late_dec",
                            "early_jan",
                            "late_jan"]])
    
    # # Finally a groupby to bring all together    
    gb_rooms = accom_df_2425.groupby(
                    ["Vendor", "Room/Resource"])["Item Sell Price",
                                                 "early_dec",
                                                 "late_dec",
                                                 "early_jan",
                                                 "late_jan",
                                                 "early_feb",
                                                 "late_feb",
                                                 "early_mar",
                                                 "late_mar"] \
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

        st.write(gb_rooms[k].sum()/ \
                 (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1)))
        
        
    final_df = pd.DataFrame(occupancy, columns = cols)
        
    st.write(final_df)

    return final_df


calc_nights()

country_df = country_breakdown()

bk_rates_fig = bookings_enq_rate()

with row0[0]:
    with st.container(border=True):
        st.pyplot(bk_rates_fig)

with row0[0]:
        with st.container(border=True):
            st.markdown(\
            f"""
            - ###### {bookdotcom_percent_without_email}% of booking.com have not emailed res
            - ###### {airbnb_percent_without_email}% of Airbnb have not emailed res
            - ###### {percent_with_gs}% of bookings have guest services worth {format_millions(gs_sell_2425)}""")

# with row1[1]: st.dataframe(country_counts_2324.head(7))
# with row1[1]: st.dataframe(country_counts_2425.head(7))

season_fig, season_ax = plot_setup(4,2)

season_hbars(season_fig, season_ax, 4, 2)

channel_df = channel_breakdown()

# managed_nonmanaged_fig = managed_nonmanaged()
non_managed_df = non_managed_breakdown()

# with row0[0]: 
#     with st.container(border= True): 
#         st.pyplot(season_fig)



# with row0[0]: st.pyplot(channel_graph)
with row0[1]: 
    with st.container(border= True):
        st.dataframe(
            data = channel_df[[
                "ChannelAS2",
                "Gross",
                "Count",
                "Avg booking",
                "Nights/Days"
                ]],
            width = None,
            hide_index = True,
            column_config={
                        "Gross": st.column_config.ProgressColumn(
                            "Gross",
                            format=" ¥%iM",
                            min_value=0,
                            max_value=300,
                        ),
                        "Count" : st.column_config.NumberColumn(
                            "Bookings"
                        ),
                        "Nights/Days": st.column_config.NumberColumn(
                            "Nights"
                        ),
                        "ChannelAS2": st.column_config.TextColumn(
                            "Sales Channel"
                        ),
                        }
                        )



with row0[1]: 
    with st.container(border=True):
        st.dataframe(
                data = non_managed_df[[
                    "Managed by",
                    "Item Sell Price",
                    "Count",
                    "Avg booking",
                    "Commission"
                    ]],
                width = None,
                hide_index = True,
                column_config={
                            "Item Sell Price": st.column_config.ProgressColumn(
                                "Gross",
                                format=" ¥%f M",
                                min_value=0,
                                max_value=18,
                            ),
                            "Count" : st.column_config.NumberColumn(
                                "Bookings"
                            ),
                            })

with row0[1]: 
    with st.container(border=True):
        st.dataframe(
                data = country_df[[
                    "Lead Guest Residency",
                    "Gross",
                    "% of Bookings",
                    "Avg booking",
                    "Nights/Days"
                    ]],
                width = None,
                hide_index = True,
                column_config={
                            "Lead Guest Residency": st.column_config.TextColumn(
                                "Country",
                            ),
                            "Gross": st.column_config.ProgressColumn(
                                "Gross",
                                format=" ¥%fM",
                                min_value=0,
                                max_value=300,
                            ),
                            "Nights/Days": st.column_config.NumberColumn(
                                "Nights"
                            )}
                            )
 


