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

st.markdown(
    """
    <style>
        footer {display: none}
        [data-testid="stHeader"] {display: none}
    </style>
    """, unsafe_allow_html = True
)
row0 = st.columns([1.8,2.5, 1.8])
divider = st.columns(1)

row1 = st.columns([2, 2.8, 2.5])
row2 = st.columns([2, 2.5, 2])

# with open('style.css') as f:
#     st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html = True)


def highlight_not_paid(s):
    
    

    if (s.Received == 0) & (s.HN_Prop == 0) & (s.Invoiced > 0):
        return ['background-color: #ffb09c'] * len(s)
    
    elif (s.Received == 0) & (s.Residency != "OTA") & (s.Invoiced > 0):

        return ['background-color: #ffead5'] * len(s)    
    
    else:
        return ['background-color: white'] * len(s)
    

################ SIDEBAR START  ################# 

# with st.sidebar:
with row0[0]: 
    with st.container(border = True):
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
        with row0[0]: 
            with st.container(border = True):
                bk.write_key_booking_info()
                # bk.write_gsg_guide()
                bk.write_notes()

        
        with row0[1]:
                with st.container():
                        
                    bk.write_room_info(bk.room_list_todf) 
                    st.write("---")
                    bk.write_payment_df()
                


        
        with divider[0]: st.write("---")
        
        # write email templates 
        with row1[2]: 
            
            with st.container():
                bk.write_email_subject()
                bk.write_gsg_upsell()
                bk.write_first_ota_email()
                bk.write_second_OTA_email()
                bk.write_OTA_email()
                bk.write_overdue_email()


        with row1[0]:
            with st.container():
                bk.write_links_box()

        with row0[2]:
            with st.container():
                st.markdown("##### Check-in")
                bk.write_cognito()
                bk.write_days_to_checkin()
                # bk.write_booking_info()


       