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
from src.utils import percent_change



# Page and variable setup
st.set_page_config(page_title = "Sales Dashboard",
                   layout="wide",
                   )
# Set up columns
top_row = st.columns((0.6,0.8,0.8,0.8,0.8,0.8))
row0 = st.columns((5,2.4))

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html = True)
# Get current month
# current_month = datetime.datetime.today().month
today_str = datetime.datetime.today().strftime('%b %d')


# Store queries for use later on
query_2324 = f""" Season == "'23/24'" """

query_2425 = f""" Season == "'24/25'" """


# TODO add more data sources and connect to analytics API


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
all_books_df = clean_accom_df(all_books_df, "Check In / Start", 
                              remove_zero = True)

all_books_accom = all_books_df[all_books_df["accom_flag"] == 1]
otd_all_books = create_otd_df(all_books_df, "Gross")
otd_all_books = otd_all_books.query("accom_flag == 1")

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


def season_metrics():

    """Make the season hbars """


    # Get all the figures
    gs_sell_2425 = gs_df.query(query_2425)["Item Sell Price"].sum()
    gs_sell_2324 = gs_df.query(query_2324)["Item Sell Price"].sum()
    gs_sell_otd = otd_gs_df.query(query_2324)["Item Sell Price"].sum()




    gross_2425 = all_books_accom.query(query_2425)["Item Sell Price"].sum()
    gross_2324 = all_books_accom.query(query_2324)["Item Sell Price"].sum()
    gross_otd_2324 = otd_all_books.query(query_2324)["Item Sell Price"].sum()

    
    bk_count_2324 = all_books_accom.query(query_2324)["Package ID"].nunique()
    bk_count_otd_2324 = otd_all_books.query(query_2324)["Package ID"].nunique()
    bk_count_2425 = all_books_accom.query(query_2425)["Package ID"].nunique()


    nights_2324 = all_books_accom.query(query_2324)["Nights/Days"].sum()
    nights_otd_2324 = otd_all_books.query(query_2324)["Nights/Days"].sum()
    nights_2425 = all_books_accom.query(query_2425)["Nights/Days"].sum()


    gross_percent_change = int(((gross_2425 - gross_otd_2324)/gross_otd_2324)*100)
    nights_percent_change = int(((nights_2425 - nights_otd_2324)/nights_otd_2324)*100)
    bk_percent_change = int(((bk_count_2425 - bk_count_otd_2324)/bk_count_otd_2324)*100)
    gs_percent_change = int(((gs_sell_2425 -gs_sell_otd)/gs_sell_otd)*100)

    # Add figures to dict for easy graphing
    season_dict = {
        "Gross" : [gross_2425, gross_otd_2324, gross_2324],
        "Nights" : [nights_2425, nights_otd_2324, nights_2324],
        "Bookings" : [bk_count_2425, bk_count_otd_2324, bk_count_2324],
        "GS": [gs_sell_2425, gs_sell_otd, gs_sell_2324]
        }
    
    # Add bar labels
    with top_row[0]:
        with st.container(border = False):
            st.markdown("### Winter 24/25 Sales")        

    with top_row[1]:
        with st.container(border = True):
            st.markdown(
                f'<p class="title_text">Gross Sales</p> \
                <p class="price_details">{format_millions(gross_2425)}</p>',
                unsafe_allow_html = True)
            
            css_class, arrow = percent_change(gross_percent_change)

            st.markdown(f'<p class="{css_class}">{gross_percent_change}% {arrow}   \
                        OTD - {format_millions(gross_otd_2324)}</p>',
                        unsafe_allow_html = True)
                # 
                
            st.markdown(f'<p class="title_text"> 2023 Total - ¥785M</p>',
                        unsafe_allow_html = True)

    with top_row[2]:
        with st.container(border=True):
            st.markdown(
                f'<p class="title_text">Nights Booked</p> \
                <p class="price_details">{format_millions(nights_2425)}</p>',
                unsafe_allow_html = True)
            
            css_class, arrow = percent_change(nights_percent_change)

            st.markdown(
                f'<p class="{css_class}">{nights_percent_change}% {arrow}   \
                OTD - {format_millions(nights_otd_2324)}</p>',
                unsafe_allow_html = True)
            

            st.markdown(
                f'<p class="title_text"> 2023 Total - {nights_2324:,}</p>',
                unsafe_allow_html = True)
    
    with top_row[3]:
            with st.container(border=True):
                st.markdown(
                    f'<p class="title_text">Number of Bookings</p> \
                    <p class="price_details">{format_millions(bk_count_2425)}</p>',
                    unsafe_allow_html = True)
            
                css_class, arrow = percent_change(bk_percent_change)

                st.markdown(
                    f'<p class="{css_class}">{bk_percent_change}% {arrow}   \
                    OTD - {bk_count_otd_2324}</p>',
                    unsafe_allow_html = True)
            

                st.markdown(
                    f'<p class="title_text"> 2023 Total - {bk_count_2324:,}</p>',
                    unsafe_allow_html = True)      

    with top_row[4]:
        with st.container(border=True):
            st.markdown(
                    f'<p class="title_text">Guest Service Gross</p> \
                    <p class="price_details">{format_millions(gs_sell_2425)}</p>',
                    unsafe_allow_html = True)
            
            css_class, arrow = percent_change(gs_percent_change)

            st.markdown(
                f'<p class="{css_class}">{gs_percent_change}% {arrow}   \
                OTD - {format_millions(gs_sell_otd)}</p>',
                unsafe_allow_html = True)
        

            st.markdown(
                f'<p class="title_text"> 2023 Total - {format_millions(gs_sell_2324)}</p>',
                unsafe_allow_html = True)

    
    pass


def channel_breakdown():



    
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
    
    
    result["Lead Guest Residency"] = result["Lead Guest Residency"]\
                                            .fillna(value = "Unknown")

        #  result[["Lead Guest Residency", "% Total Bookings", "Item Sell Price"]],
         
    
    return result
    


def non_managed_breakdown():
     
    
    
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
    
    

    non_managed_perc_24 = (non_managed_gb["Item Sell Price"].sum() / \
                        all_books_accom_2425["Item Sell Price"].sum())

    non_managed_perc_23 = (non_managed_total_23 / \
                        all_books_accom_2324["Item Sell Price"].sum())
    
    # Metric card for non managed
    non_managed_percent_change = int(((non_managed_total_24 - non_managed_total_23_otd)/ non_managed_total_23_otd)*100)

    with top_row[5]:
        with st.container(border=True):
            st.markdown(
                    f'<p class="title_text">Non-managed Gross</p> \
                    <p class="price_details">{format_millions(non_managed_total_24)}</p>',
                    unsafe_allow_html = True)
            
            css_class, arrow = percent_change(non_managed_percent_change)

            st.markdown(
                f'<p class="{css_class}">{non_managed_percent_change}% {arrow}   \
                OTD - {format_millions(non_managed_total_23_otd)}</p>',
                unsafe_allow_html = True)
        

            st.markdown(
                f'<p class="title_text"> 23/24  Total - {format_millions(non_managed_total_23)}</p>',
                unsafe_allow_html = True)
            
            

    

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
    

    nights_accom_df = load_csv_data("../../Downloads/All Bookings Clean.csv")
    accom_df_2425 = clean_accom_df(nights_accom_df, "Check In / Start", 
                              remove_zero = False)

    accom_df_2425 = accom_df_2425.query(f""" Season =="'24/25'" & \
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

    # st.write(accom_df_2425[["Vendor",
    #                         "Room/Resource",
    #                         "Check In / Start",
    #                         "Last Night",
    #                         "Check Out / End",
    #                         "early_dec",
    #                         "late_dec",
    #                         "early_jan",
    #                         "late_jan"]])
    
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
    kick_vendors = ["Asuka Value Studios",
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

    cols = ["Period", "Occupancy", "Available Nights"]
    occupancy = []

    for k, v  in start_end_dates.items():
        
        occupancy.append([k,
                         gb_rooms[k].sum()/ \
                        (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1)),
                        (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1)) - gb_rooms[k].sum(),
                        ])

        # st.write(gb_rooms[k].sum()/ \
        #          (gb_rooms.shape[0] * ((v[1] - v[0]).days + 1)))
        
        
    final_df = pd.DataFrame(occupancy, columns = cols)

    final_df["Occupancy"] = round(final_df["Occupancy"] * 100, 1)
        
    st.dataframe(final_df, hide_index = True)

    
    return final_df


occupancy_df = calc_nights()

country_df = country_breakdown()

bk_rates_fig = bookings_enq_rate()

with row0[0]:
    with st.container(border=True):
        innercols = st.columns([3,1])

        with innercols[0]:
            st.pyplot(bk_rates_fig)

        with innercols[1]:
                st.dataframe(occupancy_df, hide_index = True, )


with row0[0]:
        with st.container(border=True):
            st.markdown(\
                f"""
                - ###### {bookdotcom_percent_without_email}% of booking.com have not emailed res
                - ###### {airbnb_percent_without_email}% of Airbnb have not emailed res
                - ###### {percent_with_gs}% of bookings have guest services worth {format_millions(gs_sell_2425)}
                - ###### ~30% of bookings had GS in 2023/24 worth ¥83M""")
            



season_metrics()

channel_df = channel_breakdown()


non_managed_df = non_managed_breakdown()

# Channel breakdown
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

# Non managed breakdown
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

# Country breakdown
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
 


