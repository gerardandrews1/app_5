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
st.set_page_config(page_title = "Sales Dashboard",
                   layout="wide")

# Set up columns
row0 = st.columns(2 )
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


############## FIGURE SETUP #################

fig,  (ax0, ax1, ax2, ax3,
       ax4, ax5, ax6, ax7,
       ax8) = plt.subplots(9, 2,
                           width_ratios=[10, 0.8],
                           figsize = (8,5.2))

for x,y in enumerate(fig.axes):

    fig.axes[x].tick_params(top=False,
               bottom=False,
               left=False,
               right=False,
               labelleft=True,
               labelbottom=False)
    
    fig.axes[x].spines[["top", "left", ]].set_visible(False)
    fig.axes[x].spines[["bottom", "right"]].set_color('#D4D4D4')


    fig.axes[x].get_xaxis().set_visible(False)
# Activates first plot
plt.subplot(9,2,1)


############## Web Enquiries #################

today_str = "2023" + datetime.datetime.today().strftime('%Y-%m-%d')[4:]
today_date = pd.to_datetime(today_str)

# Get metrics for graphs
enq_2324_df = enq_df[enq_df.Season == "'23/24'"]

total_enq_2324 = enq_df[enq_df.Season == "'23/24'"].Email.nunique()
total_enq_2425 = enq_df[enq_df.Season == "'24/25'"].Email.nunique()
total_enq_otd_2324 = enq_2324_df\
    [enq_2324_df["Enquiry Date"] < today_date].Email.nunique()


enq_percent = total_enq_2425/total_enq_otd_2324

build_bullet(total_enq_2425,
             total_enq_otd_2324,
             total_enq_2324,
             "Web Enquiries")

# Annotations
plt.text(total_enq_2425 - 55, y = -0.15, s = f"{total_enq_2425}", fontsize = 9, color = "white")
plt.text(total_enq_2324 - 35, y = 1.2, s = f"{total_enq_2324:,}", fontsize = 8, color = "#222222")
plt.text(total_enq_otd_2324 - 50, y = 0.8, s = f"{total_enq_otd_2324}", fontsize = 8, color = "#222222")

# Title for 2023 total
plt.figtext(0.75, 0.92,
            "2023 Total",
             color = "#222222",
             fontsize = 12)

# plt.yticks([0.5], ["Web Enquiries"]) # Title

fig.axes[0].set_title(f"2024 Total vs {today_date.strftime('%b %d %Y')}",
                       fontdict = {"fontsize": 12},
                       loc= "left",
                       pad = 20)

# Add x factor
plt.subplot(9,2,2)

plt.text(0.15, y = 0.45, s = f"{round(enq_percent,2)}x", fontsize = 9)
plt.yticks([])


########################   TOTAL BOOKINGS ######################


plt.subplot(9, 2, 3)

total_bk_2425 = accom_df[accom_df.Season == "'24/25'"].ID.nunique()
total_bk_2324 = accom_df[accom_df.Season == "'23/24'"].ID.nunique()
total_bk_otd_2324 = otd_df[otd_df.Season == "'23/24'"].ID.nunique()

bks_percent = total_bk_2425/total_bk_otd_2324

build_bullet(total_bk_2425,
             total_bk_otd_2324,
             total_bk_2324,
             "Bookings Total")


plt.text(total_bk_2324 - 40, y = 1.2, s = f"{total_bk_2324:,}", fontsize = 8, color = "#222222")
plt.text(total_bk_2425 - 75, y = -0.2, s = f"{total_bk_2425}", fontsize = 9, color = "white")
plt.text(total_bk_otd_2324 - 65, y = 0.8, s = f"{total_bk_otd_2324}", fontsize = 8, color = "#222222"	)

plt.subplot(9,2,4)
plt.text(0.15, y = 0.45, s = f"{round(bks_percent,2)}x", fontsize = 9)
plt.yticks([])


####################### GROSS ###############################

plt.subplot(9, 2, 5)


total_gross_2425 = accom_df[accom_df.Season == "'24/25'"].Gross.sum()
total_gross_2324 = accom_df[accom_df.Season == "'23/24'"].Gross.sum()
total_gross_otd_2324 = otd_df[otd_df.Season == "'23/24'"].Gross.sum()

gross_percent = total_gross_2425/total_gross_otd_2324

build_bullet(total_gross_2425,
             total_gross_otd_2324,
             total_gross_2324,
             "Gross ¥"
             )

display_2324 = round(int(total_gross_2324)*0.000001)
display_2425 = round(int(total_gross_2425)*0.000001)
display_otd_2324 = round(int(total_gross_otd_2324)*0.000001)


plt.text(total_gross_2324 * 0.97, y = 1.2, s = f"{display_2324}M", fontsize = 8, color = "#222222")
plt.text(total_gross_2425 * 0.89, y = -0.15, s = f"{display_2425}M", fontsize = 9, color = "white")
plt.text(total_gross_otd_2324 * 0.85, y = 0.85, s = f"{display_otd_2324}M", fontsize = 8, color = "#222222")

# Plot the x 
plt.subplot(9,2,6)

plt.text(0.15, y = 0.45, s = f"{round(gross_percent,2)}x", fontsize = 9)
plt.yticks([])


######################  NIGHTS    ####################################

plt.subplot(9, 2, 7)

total_nights_2425 = accom_df[accom_df.Season == "'24/25'"].Nights.sum()
total_nights_2324 = accom_df[accom_df.Season == "'23/24'"].Nights.sum()

total_nights_otd_2324 = otd_df[otd_df.Season == "'23/24'"].Nights.sum()


nights_percent = round(total_nights_2425/total_nights_otd_2324, 2)

build_bullet(total_nights_2425, 
             total_nights_otd_2324,
             total_nights_2324,
             "Nights Booked")

# Annotations
plt.text(total_nights_2324 * 0.96, y = 1.2, s = f"{total_nights_2324:,}", fontsize = 8, color = "#222222")
plt.text(total_nights_2425 * 0.85, y = -0.2, s = f"{total_nights_2425:,}", fontsize = 9, color = "white")
plt.text(total_nights_otd_2324 * 0.85, y = 0.8, s = f"{total_nights_otd_2324:,}", fontsize = 8, color = "#222222")

# Plot the x
plt.subplot(9, 2, 8)
plt.text(0.15, y = 0.45, s = f"{nights_percent}x", fontsize = 9)
plt.yticks([])


#################### NON MANAGED TOTAL ######################

plt.subplot(9, 2, 9)

non_managed_2425 = accom_df \
    .query("""HN_Prop == 0 and Season == "'24/25'" """).ID.nunique()

non_managed_2324 = accom_df \
    .query("""HN_Prop == 0 and Season == "'23/24'" """).ID.nunique()

otd_non_managed_2324 = otd_df\
    .query("""HN_Prop == 0 and Season == "'23/24'" """).ID.nunique()

non_managed_perc = round(non_managed_2425/otd_non_managed_2324, 2)

build_bullet(non_managed_2425,
             otd_non_managed_2324,
             non_managed_2324,
             "Non-managed")

plt.text(otd_non_managed_2324 * 0.92, y = 0.85, s = f"{otd_non_managed_2324}", fontsize = 8, color = "#222222")
plt.text(non_managed_2324 * 0.98, y = 1.2, s = f"{non_managed_2324}", fontsize = 8, color = "#222222")
plt.text(non_managed_2425 * 0.91, y = -0.2, s = f"{non_managed_2425}", fontsize = 9, color= "white")


# Plot x factor
plt.subplot(9, 2, 10)
plt.text(0.15, y = 0.45, s = f"{non_managed_perc}x", fontsize = 9)
plt.yticks([])


#################### NON MANAGED GROSS ######################

plt.subplot(9, 2, 11)

non_managed_gross_2425 = accom_df \
    .query("""HN_Prop == 0 and Season == "'24/25'" """).Gross.sum()

non_managed_gross_2324 = accom_df \
    .query("""HN_Prop == 0 and Season == "'23/24'" """).Gross.sum()

otd_non_managed_gross_2324 = otd_df \
    .query("""HN_Prop == 0 and Season == "'23/24'" """).Gross.sum()

nm_gross_perc = round(non_managed_gross_2425/otd_non_managed_gross_2324, 2)

build_bullet(non_managed_gross_2425,
             otd_non_managed_gross_2324,
             non_managed_gross_2324,
             "Non-managed Gross ¥")


nm_display_gross_2324 = round(int(non_managed_gross_2324)*0.000001)
nm_display_gross_2425 = round(int(non_managed_gross_2425)*0.000001)
nm_otd_display_gross_2425 = round(int(otd_non_managed_gross_2324)*0.000001)


plt.text(otd_non_managed_gross_2324 * 0.87, y = 0.8, s = f"{nm_otd_display_gross_2425}M", fontsize = 8)
plt.text(non_managed_gross_2324 * 0.97, y = 1.2, s = f"{nm_display_gross_2324}M", fontsize = 8)
plt.text(non_managed_gross_2425 * 0.88, y = -0.2, s = f"{nm_display_gross_2425}M", fontsize = 9, color = "white")



plt.subplot(9, 2, 12)
plt.text(0.15, y = 0.45, s = f"{nm_gross_perc}x", fontsize = 9)
plt.yticks([])

# plt.axis("off")

############### CURRENT MONTH COUNT ####################

# Get the current month name
current_month_name = datetime.datetime.now().strftime("%b")

plt.subplot(9, 2, 13)

month_books_2425 = accom_df.query(f""" Season == "'24/25'" and \
                            `Booking Month` == {current_month}""").ID.nunique()

month_books_2324 = accom_df.query(f""" Season == "'23/24'" and \
                            `Booking Month` == {current_month}""").ID.nunique()

month_books_otd_2324 = otd_df.query(f""" Season == "'23/24'" and \
                            `Booking Month` == {current_month}""").ID.nunique()

curr_month_perc = month_books_2425/month_books_otd_2324

build_bullet(month_books_2425,
             month_books_otd_2324,
             month_books_2324,
             f"{current_month_name} Bookings")



plt.text(month_books_otd_2324 * 0.85 , y = 0.8, s = f"{month_books_otd_2324}", fontsize = 8)
plt.text(month_books_2425 * 0.875, y = -0.2, s = f"{month_books_2425}", fontsize = 9, color ="white")
plt.text(month_books_2324 * 0.978, y = 1.2, s = f"{month_books_2324}", fontsize = 8)


# Plot the x factor
plt.subplot(9, 2, 14)
plt.text(0.15, y = 0.45, s = f"{round(curr_month_perc,2)}x", fontsize = 9)
plt.yticks([])


################### CURRENT MONTH GROSS ####################

plt.subplot(9, 2, 15)

month_gross_2425 = accom_df.query(f""" Season == "'24/25'" and \
                            `Booking Month` == {current_month}""").Gross.sum()

month_gross_2324 = accom_df.query(f""" Season == "'23/24'" and \
                            `Booking Month` == {current_month}""").Gross.sum()

month_gross_otd_2324 = otd_df.query(f""" Season == "'23/24'" and \
                            `Booking Month` == {current_month}""").Gross.sum()

month_gross_perc = round(month_gross_2425/month_gross_otd_2324, 2)

build_bullet(month_gross_2425,
             month_gross_otd_2324,
             month_gross_2324,
             f"{current_month_name} Gross ¥")

display_2324 = round(int(total_gross_2324) * 0.000001)
display_2425 = round(int(total_gross_2425) * 0.000001)
display_otd_2324 = round(int(total_gross_otd_2324) * 0.000001)


plt.text(month_gross_otd_2324 * 0.8, 
         y = 0.85, 
         s = f"{round(int(month_gross_otd_2324)*0.000001)}M",
         fontsize = 8, 
         color = "#222222")

plt.text(month_gross_2425 * 0.83, y = -0.15, s = f"{round(int(month_gross_2425)*0.000001)}M", fontsize = 9, color = "white")
plt.text(month_gross_2324 * 0.97 , y = 1.2, s = f"{round(int(month_gross_2324)*0.000001)}M", fontsize = 8, color = "#222222")


plt.subplot(9, 2, 16)
plt.text(0.15, y = 0.45, s = f"{round(month_gross_perc,2)}x", fontsize = 9)
plt.yticks([])

################### GS BOOKS ####################

plt.subplot(9, 2, 17)

# gs_2324 = gs_df.query("")
gs_2324_df = gs_df[gs_df.Season == "'23/24'"]
gs_2324_df.Created = pd.to_datetime(gs_2324_df.Created)

gs_total_2324 = gs_df.query("""Season == "'23/24'" """)\
                            ["Item Sell Price"].sum()

gs_total_2425 = gs_df.query("""Season == "'24/25'" """)\
                            ["Item Sell Price"].sum()

gs_otd_2324 = gs_2324_df[gs_2324_df.Created < today_date]\
                            ["Item Sell Price"].sum()


gs_percent = round(gs_total_2425/gs_otd_2324, 2)


build_bullet(gs_total_2425,
             gs_otd_2324,
             gs_total_2324,
             f"Guest Services ¥")

gs_display_2324 = round(int(gs_total_2324) * 0.000001)
gs_display_2425 = round(int(gs_total_2425) * 0.000001)
gs_display_otd_2324 = round(int(gs_otd_2324) * 0.000001)

plt.text(gs_otd_2324 * 0.6, y = 0.8, s = f"{gs_display_otd_2324}M", fontsize = 8)
plt.text(gs_total_2425 * 0.7, y = -0.2, s = f"{gs_display_2425}M", fontsize = 9, color ="white")
plt.text(gs_total_2324 * 0.95, y = 1.2, s = f"{gs_display_2324}M", fontsize = 8)


################ PLOT THE BULLETS ####################
fig.subplots_adjust(wspace=0, hspace=0.4)

with row0[1]: st.pyplot(fig)





##################################################################################








########### PLOT THE SPARKS  #####################

###################### BOOKING  RATE ########################

fig_rates,  (ax0, ax1, ax2, ax3) = plt.subplots(4, 2,
                                     width_ratios=[10, 1],
                                     sharex = True,
                                     figsize = (8,6))



plt.subplot(4, 2, 3)

epoch = time.time()
# today_date
dt = datetime.datetime.utcfromtimestamp(epoch)

idx = (dt.weekday() + 1) % 7
sun = dt - datetime.timedelta(days=idx)
sun = sun + pd.offsets.DateOffset(days=1)
sun = sun.strftime("%Y-%m-%d")


weekly_df = accom_df.query(f"""Season =="'24/25'" and \
                          (`Booking Month` > 0 and `Booking Month` < 12) \
                           and `Booking Year` == 2024 and \
                           Created < '{sun}' """) \
                    .groupby(["Season", pd.Grouper(key = "Created", freq="W-SUN")])["ID"] \
                    .nunique() \
                    .reset_index() \
                    .sort_values("Created")

weekly_df_2324 = accom_df.query("""Season =="'23/24'" and \
                                (`Booking Month` > 0 and `Booking Month` < 12) \
                                and `Booking Year` == 2023""") \
                    .groupby(["Season", pd.Grouper(key = "Created", freq="W-SUN")])["ID"] \
                    .nunique() \
                    .reset_index() \
                    .sort_values("Created")



# USe this to change to same year so can plot on same graph
weekly_df_2324["Created_delta"] = weekly_df_2324["Created"] + pd.offsets.DateOffset(years=1)

month_day_fmt = mdates.DateFormatter('%b') # "Locale's abbreviated month name. + day of the month"
month_ticks = mdates.MonthLocator()
fig_rates.get_axes()[2].get_xaxis().set_major_formatter(month_day_fmt)    
fig_rates.get_axes()[2].get_xaxis().set_major_locator(month_ticks)    

plt.axhline(y = 20, 
            xmin= 0.1,
            xmax= 0.6,
            linestyle = "--",
            color = "#D4D4D4",
            linewidth = 1)

plt.plot(weekly_df_2324["Created_delta"],
         weekly_df_2324.ID,
         color = '#DEDEDE', 
         )


plt.plot(weekly_df["Created"],
         weekly_df.ID,
         color = '#4571c4', 
         alpha = 0.8
        )



fig_rates.get_axes()[2].get_xaxis().set_tick_params(labelsize = 8, 
                                                    which = 'both',
                                                    color = '#D4D4D4')


plt.text(x = pd.to_datetime("2024-01-05"), y = 18, s = "20/ week", fontsize = 7, color = "grey")
plt.text(x = weekly_df.Created.values[-1], 
         y = weekly_df.ID.values[-1] - 10,
         s = weekly_df.ID.values[-1],
          fontsize = 7,
           color = "#4571c4" )  

fig_rates.get_axes()[2].spines[[ "left", "right", "top" ]].set_visible(False)
fig_rates.get_axes()[2].spines['bottom'].set_color('#D4D4D4')
# fig_rates.get_axes()[2].spines['top'].set_color('#D4D4D4')


fig_rates.get_axes()[2].set_ylabel("Bookings", 
                                   rotation = 0,
                                   fontdict = {"fontsize": 8} ,
                                   loc = "center",
                                   labelpad = 25)


fig_rates.get_axes()[2].set_yticklabels([])
fig_rates.get_axes()[2].set_yticks([])

fig_rates.get_axes()[0].set_title("2024 Weekly Rates vs 2023",
                                  fontdict = {"fontsize": 10},
                                  loc = 'left',
                                  pad = 10)



###################### ENQUIRIES RATE  #############################

plt.subplot(4, 2, 1)
plt.ylim([10,40])



weekly_enq_2324 = enq_df.query(f"""`Enquiry Date` > '2022-12-31' and Season == "'23/24'" \
                               and `Enquiry Date` < '2023-12-31' """) \
                .groupby(["Season", pd.Grouper(key = "Enquiry Date", freq = "W-SUN")])["Email"] \
                .nunique() \
                .reset_index() \
                .sort_values("Enquiry Date")

weekly_enq_2425 = enq_df.query(f"""(`Enquiry Date` > '2023-12-01' and `Enquiry Date` < '{sun}') \
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



fig_rates.get_axes()[0].get_xaxis().set_major_formatter(month_day_fmt)    


fig_rates.get_axes()[0].get_xaxis().set_tick_params(labelsize = 8, 
                                                    which = 'both',
                                                    color = '#D4D4D4')
fig_rates.get_axes()[0].tick_params(bottom = True)
fig_rates.get_axes()[0].spines[["top", "left", "right"]].set_visible(False)
fig_rates.get_axes()[0].spines['bottom'].set_color('#D4D4D4')


fig_rates.get_axes()[0].set_ylabel("Web Enquiries", 
                                   rotation = 0,
                                   fontdict = {"fontsize": 8} ,
                                   loc = "center",
                                   labelpad = 35)
fig_rates.get_axes()[0].set_yticklabels([])
fig_rates.get_axes()[0].set_yticks([])





######################### MailChimp Opening Rate   ###################

plt.subplot(4, 2, 5)
plt.ylim([0.25,0.45])

mc_df_23 = mc_df[mc_df["Send Time"].dt.date > pd.to_datetime("2022-12-31")]
mc_df_23 = mc_df_23[mc_df_23["Send Time"].dt.date < pd.to_datetime("2024-01-01")]
mc_df_23["Send Time"] = mc_df_23["Send Time"] + pd.offsets.DateOffset(years = 1)


mc_df_24 = mc_df[mc_df["Send Time"].dt.date > pd.to_datetime("2023-12-31")]
mc_df_24 = mc_df_24.sort_values("Send Time", ascending = True)



plt.axhline(y = 0.4,
            xmin= 0.05,
            xmax = 1, 
            linestyle = "--",
            color = "#D4D4D4",
            linewidth = 1)

plt.plot(mc_df_23["Send Time"],
    mc_df_23["Open Rate"],
    marker = "o",
    markersize = 3,
    color = '#DEDEDE')

plt.plot(mc_df_24["Send Time"],
    mc_df_24["Open Rate"],
    marker = "o",
    markersize = 3,
    color = '#4571c4')


plt.text(x = pd.to_datetime("2023-12-26"),
         y = 0.39,
         s = f"40%",
         fontsize = 7,
         color = "grey")


plt.text(x = mc_df_24["Send Time"].values[-1] + pd.offsets.DateOffset(days=3),
         y = mc_df_24["Open Rate"].values[-1] + 0.01,
         s = f"{round(mc_df_24['Open Rate'].values[-1], 3)*100}%",
         fontsize = 7,
         color='#4571c4')

fig_rates.get_axes()[4].get_xaxis().set_major_formatter(month_day_fmt)

fig_rates.get_axes()[4].get_xaxis().set_tick_params(labelsize = 8, 
                                                    which = 'both',
                                                    color = '#D4D4D4')
fig_rates.get_axes()[4].spines[["top", "left", "right"]].set_visible(False)
fig_rates.get_axes()[4].spines['bottom'].set_color('#D4D4D4')

fig_rates.get_axes()[4].set_ylabel("Email Open %", 
                                   rotation = 0,
                                   fontdict = {"fontsize": 8} ,
                                   loc = "center",
                                   labelpad = 35)
fig_rates.get_axes()[4].set_yticklabels([])
fig_rates.get_axes()[4].set_yticks([])

fig_rates.get_axes()[5].axis("off")


##################### GOOGLE ANALYTICS RATES #######################

plt.subplot(4,2,7)
plt.ylim([0, 5000])



plt.plot(ga_2023.Date,
         ga_2023.Users,
        #  marker = "o",
         markersize = 3,
         color = "#DEDEDE")

plt.plot(ga_2024.Date,
    ga_2024.Users,
    # marker = "o",
    markersize = 3,
    color = '#4571c4',
    alpha = 0.6)


plt.text(x = ga_2024.Date.values[-1],
         y = ga_2024.Users.values[-1] + 800,
         s = ga_2024.Users.values[-1],
         fontsize = 7,
         color = '#4571c4')

fig_rates.get_axes()[6].spines[["top", "left", "right"]].set_visible(False)
fig_rates.get_axes()[6].spines['bottom'].set_color('#D4D4D4')
fig_rates.get_axes()[6].set_yticklabels([])
fig_rates.get_axes()[6].set_yticks([])

fig_rates.get_axes()[6].get_xaxis().set_tick_params(labelsize = 9, 
                                                    which = 'both',
                                                    color = "#D4d4d4",
                                                    labelcolor = 'grey')



fig_rates.get_axes()[6].set_xlim([datetime.date(2024, 1, 1), datetime.date(2024, 12, 1)])
fig_rates.get_axes()[6].set_ylabel("Website Users", 
                                   rotation = 0,
                                   fontdict = {"fontsize": 8} ,
                                   loc = "center",
                                   labelpad = 35)

fig_rates.get_axes()[7].axis("off")

######################   LAST 7 DAYS BOOKINGS MEASURE  ######################

plt.subplot(4,2,4)



time_range_var = datetime.timedelta(days = 7)
time__accom_df = accom_df[accom_df.Created > (datetime.datetime.today() - time_range_var)]

last_wk_bks = time__accom_df.ID.nunique()

plt.text(pd.to_datetime("2024-05-01"), y = 0.4, s = f"{last_wk_bks}", fontsize = 8)

fig_rates.get_axes()[3].spines[[ "right", "left" ,"top"]].set_visible(False)
fig_rates.get_axes()[3].spines[['bottom', ]].set_color('#D4D4D4')

fig_rates.get_axes()[3].get_yaxis().set_visible(False)
fig_rates.get_axes()[3].get_xaxis().set_visible(False)
fig_rates.get_axes()[1].set_title("Last 7 Days",
                                  fontdict = {"fontsize": 8})



####################### LAST 7 DAYS ENQURIES MEASURE ###########################


plt.subplot(4,2,2)



time_enq_df = enq_df[enq_df["Enquiry Date"] > (datetime.datetime.today() - time_range_var)]

last_wk_enq = time_enq_df.Email.nunique()

plt.text(pd.to_datetime("2024-05-01"), y = 0.45, s = f"{last_wk_enq}", fontsize = 8)

fig_rates.get_axes()[1].spines[["top", "right", "left"]].set_visible(False)
fig_rates.get_axes()[1].get_yaxis().set_visible(False)
fig_rates.get_axes()[1].get_xaxis().set_visible(False)
fig_rates.get_axes()[1].spines[[ 'bottom']].set_color('#D4D4D4')


fig_rates.subplots_adjust(wspace=0, hspace=0.5)




with row0[0]:
    st.pyplot(fig_rates)

# plot_enqs = total_enq_2425.groupby("Stay Period")["Stay Period"].count().reset_index(name="THING")
# plot_enqs = plot_enqs[plot_enqs["Stay Period"] != "0"]


# plot_enqs["Stay Period"] = pd.Categorical(plot_enqs["Stay Period"], 
#                                         ["Early Dec", "Late Dec",
#                                          "Early Jan", "Late Jan",
#                                          "Early Feb", "Late Feb",
#                                          "Early Mar", "Late Mar"])

# plot_enqs.sort_values(by = "Stay Period", inplace=True)


# fig_sns = plt.figure(figsize=(10, 4))

