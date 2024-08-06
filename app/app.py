# app homepage for high level business metrics.

import datetime
import json
import numpy as np
import os
import pandas as pd
import requests
import streamlit as st

# from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
from plotly.subplots import make_subplots


# personal imports
from src.components.api_list_booking import call_api
from src.components.api_bks_changed_date import call_api_bks_changed
from src.components.api_bks_changed_date import get_etl_time
from src.components.api_bks_changed_date import transform_api_resp_df
from src.components.booking import Booking


st.set_page_config(page_title = "List Booking",
                   layout="wide")


row1 = st.columns([1,2.8,2.5])


def highlight_not_paid(s):
    
    

    if (s.Received == 0) & (s.HN_Prop == 0) & (s.Invoiced > 0):
        return ['background-color: #ffb09c'] * len(s)
    
    elif (s.Received == 0) & (s.Residency != "OTA") & (s.Invoiced > 0):

        return ['background-color: #ffead5'] * len(s)    
    
    else:
        return ['background-color: white'] * len(s)
    


def month_splits_2324(df,column, season):
    
    """Allocates a booking to a month period 
       NOT IDEAL AS COLUMN BASED ON START DATE
       NEED TO MAKE ROBUST FOR STAYS THAT CROSS OVER PERIODS"""
    first = season[0:2]
    second = season[2:4]

    
    df["Stay Period"] = np.where(df[column].between(f"20{first}-12-01",f"20{first}-12-15"),"Early Dec",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{first}-12-16",f"20{first}-12-31"),"Late Dec",df["Stay Period"]) 
    df["Stay Period"] = np.where(df[column].between(f"20{second}-01-01",f"20{second}-01-15"),"Early Jan",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-01-15",f"20{second}-01-31"),"Late Jan",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-02-01",f"20{second}-02-15"),"Early Feb",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-02-16",f"20{second}-02-29"),"Late Feb",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-03-01",f"20{second}-03-15"),"Early Mar",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-03-15",f"20{second}-03-31"),"Late Mar",df["Stay Period"])  

    return df


def clean_accom_df(accom_df):

    # Remove owner stays
    accom_df = accom_df[accom_df["Zero Stay"] == 0]
    accom_df["Count"] = 1 # column to utilise groupby sums
    accom_df.Created = pd.to_datetime(accom_df.Created, dayfirst = False)

    accom_df = accom_df[accom_df.Created > pd.to_datetime("20231230")]

    # for season in ["2324", "2425"]: add the start 1/2 month split
    accom_df["Stay Period"] = 0
    # accom_df = month_splits_2324(accom_df, "Start date", "1920")
    accom_df = month_splits_2324(accom_df, "Start date", "2324")
    accom_df = month_splits_2324(accom_df, "Start date", "2425")

    accom_df["Stay Month"] = pd.to_datetime(accom_df["Start date"]).dt.month_name()

    # keep only seasons we care about
    keepers = [ #"'18/19'", # "'14/15'", "'15/16'", "'16/17'", "'17/18'", 
            "'19/20'","'22/23'","'23/24'", "'24/25'"]

    accom_df = accom_df[accom_df.Season.isin(keepers)]

    accom_df = accom_df[["Created", "ID", "Lead Guest", "ChannelAS2", "HN_Prop",
                         "Vendor", "Gross", "Custom ID", "Residency", 
                         "Start date", "Nights", "Invoice Amount",
                         "Payment Amount", "ChannelAS1"]]
    
    # Create my standard date formatting
    accom_df["Start date"] = pd.to_datetime(accom_df["Start date"])
    accom_df["Checkin Date"] = accom_df["Start date"].dt.strftime("%d %b %Y")


    # So no thousand separators
    accom_df["ID"] = accom_df["ID"].astype(str)

    # Human readable tags
    accom_df["ChannelAS2"] = np.where(accom_df["ChannelAS2"] == "Agent", accom_df["Custom ID"], accom_df["ChannelAS2"])
    accom_df["ChannelAS2"] = np.where(accom_df["ChannelAS2"] == "Direct", "Book and Pay", accom_df["ChannelAS2"])

    


    accom_df.rename(columns = {"Payment Amount": "Received", 
                               "Invoice Amount": "Invoiced"},
                    inplace = True)


    accom_df[["Invoiced", "Received"]] = accom_df[["Invoiced", "Received"]].fillna(0)
    accom_df["Invoiced"] = accom_df["Invoiced"].astype(int)
    accom_df["Received"] = accom_df["Received"].astype(int)

    accom_df.sort_values(by = "Created", inplace = True, ascending = False)
    accom_df = accom_df[["Created", "ID", "Lead Guest", "ChannelAS1",
                                        "ChannelAS2", "Vendor", "Gross",
                                            "Residency", "Checkin Date",
                                            "Nights", "Invoiced",
                                            "Received", "HN_Prop",]]



    return accom_df



def clean_enq_df(enq_df):
    # Make first and last name one column

    enq_df["Name"] = enq_df["First Name"].astype(str) + " " + enq_df["Last Name"].astype(str)
    enq_df["PAX"] = enq_df["Adults"] + enq_df["Children 13 - 15 years"] + enq_df["Children 7 - 12 years"] 

    enq_df = enq_df[["Booking ID", "Name", "Month Split", 
                     "Nights", "Booking Source", "Country", 
                     "Bedrooms", "PAX" , "Enquiry Date"]]

    return enq_df




################ IMPORT DATA ##################

# Want to add other data sources soon
raw_file = load_data("../../Downloads/Bookings Clean.csv")
accom_df = clean_accom_df(raw_file)

enq_df = pd.read_csv("../../Downloads/Enquiries Clean.csv")
enq_df["Enquiry Date"] = pd.to_datetime(enq_df["Enquiry Date"]).dt.date

enq_df = clean_enq_df(enq_df)


payment_info_df = load_data("../../Downloads/Invoices and Payments Clean.csv")

# resp = call_api_bks_changed("20240607", hn_id, hn_key)

# new_books, mod_books = transform_api_resp_df(resp)

# new_books = new_books[["Created", "ID", "Lead Guest", 
#                         "ChannelAS2", "Vendor", "Gross",
#                         "Residency", "Checkin Date",
#                         "Nights", "Invoiced",
#                         "Received", "HN_Prop"]]

# accom_df = pd.concat([new_books, accom_df])

################ SIDEBAR  START ################

## This is the multiselect for key stats routine ## 
time_periods = [1, 2, 5, 7, 10, 14, "MTD", 30, 60, 90]

# I need to write a get current month to date logic here
with st.sidebar:
    st.session_state.time_range = st.multiselect(
    "Select time period",
    options = time_periods,
    default = 2)


with st.sidebar:
    user_input = st.text_input("Input Booking ID").strip()



################ SIDEBAR FINISH ################



def accom_time_df(time_period, accom_df):
    """
    Create the dataframe that coresponds to 
    the time range set in the sidebar multiselect
       
       Returns
       time_df: Pandas DataFrame"""
    time_df = pd.DataFrame()
    accom_df.Created = pd.to_datetime(accom_df.Created) 
    


    # Create the current month for the month to date to compare against
    if time_period == "MTD":

        time_df = accom_df[accom_df.Created > datetime.datetime.today().replace(day=1,minute=0,second=0, hour=0)]
        
        return time_df
    
    else:
        # create the dataframe with bookings falling in the correct range
        time_range_var = datetime.timedelta(days = time_period)
        time_df = accom_df[accom_df.Created > (datetime.datetime.today() - time_range_var)]

        return time_df
        


def enq_time_df(time_period, enq_df):
    

    """
    Create the dataframe that coresponds to 
    the time range set in the sidebar multiselect
       
       Returns
       time_df: Pandas DataFrame"""
    
    ## logic for enquiries

    enq_df["Enquiry Date"] = pd.to_datetime(enq_df["Enquiry Date"]) 



    # Creaate the current month for the month to date to compare against
    if time_period == "MTD":

        time_enq_df = enq_df[enq_df["Enquiry Date"] > datetime.datetime.today().replace(day=1,minute=0,second=0, hour=0)]
        
        return time_enq_df
    
    else:
        time_range_var = datetime.timedelta(days = time_period)

        time_enq_df = enq_df[enq_df["Enquiry Date"] > (datetime.datetime.today() - time_range_var)]


        return time_enq_df


def payment_info_time_df(time_period, payment_df):
    """
    Create the payment info df that coresponds to 
    the time range set in the sidebar multiselect
       
       Returns
       payment_info_time_df: Pandas DataFrame"""
    time_df = pd.DataFrame()
    payment_df["Payment Date"] = pd.to_datetime(payment_df["Payment Date"]) 
    


    # Creaate the current month for the month to date to compare against
    if time_period == "MTD":

        time_df = payment_df[payment_df["Payment Date"] > datetime.datetime.today().replace(day=1,minute=0,second=0, hour=0)]
        
        return time_df
    
    else:
        # create the dataframe with bookings falling in the correct range
        time_range_var = datetime.timedelta(days = time_period)
        time_df = payment_df[payment_df["Payment Date"] > (datetime.datetime.today() - time_range_var)]

        return time_df
        


## THIS IS HOW I WILL DISPLAY FOR NOW ##
if len(st.session_state.time_range) > 0:

    display_accom_df = accom_time_df(st.session_state.time_range[0], accom_df)


    ### Here I will start the new api intro

    # Key stats for the topline

    ota_books = display_accom_df[display_accom_df["ChannelAS1"] == "OTA"].ID.nunique()
    website_books = display_accom_df[display_accom_df["ChannelAS1"] == "Direct"].ID.nunique()
    agent_books = display_accom_df[display_accom_df["ChannelAS1"] == "Agent"].ID.nunique()

    display_accom_df = display_accom_df[["Created", "ID", "Lead Guest", 
                                        "ChannelAS2", "Vendor", "Gross",
                                            "Residency", "Checkin Date",
                                            "Nights", "Invoiced",
                                            "Received", "HN_Prop",]]
    
    # display_accom_df.drop_duplicates(inplace = True)

    display_accom_df.groupby(["Created", "ID", "Lead Guest", 
                                        "ChannelAS2", "Vendor", 
                                            "Residency", "Checkin Date",
                                            "Nights", "Invoiced",
                                            "Received", "HN_Prop"])["Gross"].sum()
    
    books_time_per = display_accom_df.ID.nunique()
    gross_time_per = display_accom_df.Gross.sum()
    hn_books_time = display_accom_df[display_accom_df["HN_Prop"] == 1].ID.nunique()
    non_man_books_time = display_accom_df[display_accom_df["HN_Prop"] == 0].ID.nunique()


    accom_html =  display_accom_df.style.format({"Created": lambda x: "{}".format(x.strftime("%d %b -- %H:%M")),
                                              "Gross": "¥{:,.0f}",
                                              "Invoiced": "¥{:,.0f}",
                                              "Received": "¥{:,.0f}"

                                             }).apply(highlight_not_paid, axis = 1)
    
    # accom_html = accom_html.hide_columns(["HN_Prop"])
    #Enquiry datafrmae generation
    display_enq_df = enq_time_df(st.session_state.time_range[0], enq_df)


    display_payment_info_df = payment_info_time_df(st.session_state.time_range[0], payment_info_df)
    display_payment_info_df.sort_values(by = "Payment Date", inplace = True, ascending = False)
    display_payment_info_df["Booking ID"] = display_payment_info_df["Booking ID"].astype(str)
    # display_payment_info_df_html = display_payment_info_df.style.format({
    #                                         "Booking ID": str
    # })
    

    with row0[1]:
        tab1, tab2, tab3 = st.tabs(["Accom Bookings", 
                                    "Payments",
                                    "Enquiries"])

    with tab1:
                
        st.dataframe(accom_html,
                     hide_index = True,
                     use_container_width = True,
                     height = 450)

    
    with tab2:
        st.dataframe(display_payment_info_df,
                     hide_index = True,
                     use_container_width = True,
                     height = 450)

    with tab3:
            st.dataframe(display_enq_df, 
                         hide_index = True, 
                         use_container_width = True, 
                         height = 450)

with row0[0]:
    
    with st.container():
        
        if len(st.session_state.time_range) > 0:

        
            enq_per_time = display_enq_df.shape[0]
            unique_enq_per_time = display_enq_df.Name.nunique()


            if st.session_state.time_range[0] == 1:
                st.markdown(f"##### In the last day: ")

            elif st.session_state.time_range[0] == "MTD":
                st.markdown(f"##### Month to date: ")

            else:
                st.markdown(f"##### In the last {st.session_state.time_range[0]} days: ")
 
            st.write(f" {books_time_per} bookings &nbsp;  -   &nbsp; ¥{gross_time_per:,.0f}")

            st.write(
                f"""
            ###### Sales Channel
            - {ota_books} - OTA bookings
            - {website_books} - Book and pay bookings
            - {agent_books} - Holiday Niseko staff bookings
            """)

            st.write(f" ###### Management")
            st.write(
            f"""
            - {hn_books_time} - Holiday Niseko managed boookings
            - {non_man_books_time} - Non managed boookings
            """)
            
            st.write(f" ###### Enquiries")

            st.write(
                f"""
                - {enq_per_time} - Enquiries
                - {unique_enq_per_time} - Unique
                      """)

with rowhalf[0]:
    st.write("---")


if user_input:
    response = call_api(user_input, hn_id, hn_key)

    if response.ok:
        bk = Booking(json.loads(response.text), api_type = "listBooking")
        
        with row1[0]: bk.write_key_booking_info()
        with row1[1]: bk.write_payment_info()
        with row1[2]: bk.write_room_info(bk.room_dict)
        with row1[2]: bk.write_email_subject()

        # Self gsg link
        # https://holidayniseko2.evoke.jp/public/booking/order02.jsf?mv=1&vs=WinterGuestServices&bookingEid=