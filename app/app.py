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


# personal imports
from src.components.api_list_booking import call_api
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


################ SIDEBAR START  ################# 

with st.sidebar:
    user_input = st.text_input("Input Booking ID").strip()



################ SIDEBAR FINISH ################




if user_input:
    response = call_api(user_input,
                        st.secrets["api_id"],
                        st.secrets["api_key"])

    if response.ok:
        bk = Booking(json.loads(response.text), api_type = "listBooking")
        
        with row1[0]: bk.write_key_booking_info()
        with row1[1]: bk.write_payment_info()
        with row1[2]: bk.write_room_info(bk.room_dict)
        with row1[2]: bk.write_email_subject()

        # Self gsg link
        # https://holidayniseko2.evoke.jp/public/booking/order02.jsf?mv=1&vs=WinterGuestServices&bookingEid=