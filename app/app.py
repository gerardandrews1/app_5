# app homepage to list booking details 

import datetime
import json
import numpy as np
import os
import pandas as pd
import requests
import streamlit as st

from ratelimit import limits, sleep_and_retry
from src.components.api_list_booking import call_api
from src.components.booking import Booking

# page and column setup
st.set_page_config(page_title = "List Booking",
                   layout="wide")

row1 = st.columns([1, 2.8, 2.5])
divider = st.columns(1)
row2 = st.columns([2, 2, 2])

def highlight_not_paid(s):
    
    

    if (s.Received == 0) & (s.HN_Prop == 0) & (s.Invoiced > 0):
        return ['background-color: #ffb09c'] * len(s)
    
    elif (s.Received == 0) & (s.Residency != "OTA") & (s.Invoiced > 0):

        return ['background-color: #ffead5'] * len(s)    
    
    else:
        return ['background-color: white'] * len(s)
    



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


################ SIDEBAR FINISH #################


if user_input:

    # response is checked in call_api function
    response = call_api(user_input,
                        st.secrets["api_id"],
                        st.secrets["api_key"])

    if response.ok:
        bk = Booking(json.loads(response.text),
                     api_type = "listBooking")
        
        # write booking info
        with row1[0]: bk.write_key_booking_info()
        with row1[1]: bk.write_payment_info()
        with row1[2]: bk.write_room_info(bk.room_dict)
        with row1[2]: bk.write_email_subject()
        
        with divider[0]: st.write("---")
        
        # write email templates 
        with row2[0]: bk.write_gsg_upsell()

    


       