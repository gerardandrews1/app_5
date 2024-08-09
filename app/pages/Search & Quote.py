# Search and quote 

import glob
import io
import json

import numpy as np
import os
import pandas as pd
import pprint
import requests
import streamlit as st

import time
from dotenv import load_dotenv
from pandas.io.json import json_normalize
from pathlib import Path

from src.components.parse_available_hotels import RbAvailableHotel 
from src.utils import get_prop_management 

st.set_page_config(page_title = "Search & Quote",
                       layout = "wide")

auth = (st.secrets["api_id"], st.secrets["api_key"])

get_prop_management()
    
writing_container = st.container()


management_dict = get_prop_management()

if "nights" not in st.session_state:
    st.session_state.nights = 0



#1 get available hotel list from roomboss
#2 get hotel ids from hotel list
#3 add hotel ids to available rooms API query (only 100 per query) 
#4 query api

def get_RBhotel_list(auth):

    """
    Get the ids of available hotels from the API and return 
    API only allows up to 100 id's to be queries at one time,
    hence multiple lists are needed
    
    Returns
        hotel_ids_list: list of 2 lists of available hotel ids
    """ 

    hotel_list_url = f"https://api.roomboss.com/extws/hotel/v1/list?countryCode=jp&locationCode=niseko"
    

    json_hotels = requests.get(hotel_list_url, auth=auth)
    json_string = json.loads(json_hotels.text)


    hotel_ids= []
    for hotel in json_string.get("hotels",{}):

        string = hotel.get("hotelId")
        string = f"&hotelId={string}"
        hotel_ids.append(string)
    
        # Split url api call into 2 calls due to length
        hotel_ids_one = hotel_ids[0:100]
        hotel_ids_two = hotel_ids[100:]

        # Convert list to string 
        hotel_ids_string_one = "".join(hotel_ids_one)
        hotel_ids_string_two = "".join(hotel_ids_two)

        hotel_ids_list = [hotel_ids_string_one, hotel_ids_string_two] 


    return hotel_ids_list


def get_stays_string(auth, hotel_ids_list, checkin, checkout, guests):


    checkin = checkin
    checkout = checkout
    guests = guests

   
    # Convert dates        
    date_checkin = pd.to_datetime(checkin).date()
    date_checkout = pd.to_datetime(checkout).date()

    # Calc nights
    nights = (date_checkout - date_checkin).days

    resp_lists = []
    for id_list in hotel_ids_list:


        api_list_avail = (
                f"https://api.roomboss.com/extws/hotel/v1/listAvailable?1&"
                f"checkIn={checkin}&checkOut={checkout}&numberGuests={guests}"
                f"&excludeConditionsNotMet&rate=ota&locationCode=NISEKO&"
                f"countryCode=JP{id_list}")
        


        # Get the available rooms, returns json formatted string
        avail_hotels = requests.get(api_list_avail, auth = auth)
        # avail_hotels_two = requests.get(list_avail_two, auth = auth)

        resp_dict = json.loads(avail_hotels.text)

        resp_lists.append(resp_dict)
        # stays_string_two = json.loads(avail_hotels_two.text)


    return resp_lists



def create_quote_df(resp_lists, management_dict):



    stays_dict = {}
    hotel_names = []


    for response in resp_lists:

        for hotel in response.get("availableHotels",{}):
        
        
            avail_hotel = RbAvailableHotel(hotel, management_dict)


            for key, avail_room in avail_hotel.avail_rooms.items():
                
                stays_dict[f"{key}"] = avail_room


    raw = pd.DataFrame(stays_dict).T


    raw["Managed By"] = raw["Managed By"].map({
                                    "hn_props": "HN",
                                    "h2_props" : "h2",
                                    "wow_props": "Niseko Wow",
                                    "nisade_props": "NISADE",
                                    "vn_props" : "VN",
                                    "mnk_props" : "MnK",
                                    "hokkaido_travel_props" : "Hokkaido Travel",
                                    None : "TELL ANDREW"})

    return raw
        

### UI & SIDE BAR ###



checkin_input = st.sidebar.text_input("Checkin").replace("-", "")
checkout_input = st.sidebar.text_input("Checkout").replace("-", "")
guests_input = st.sidebar.text_input("No. of guests")


################ SEARCH BUTTON RUN SCRIPTS #############
if "stays" not in st.session_state:
    st.session_state["stays"] = \
            pd.DataFrame(columns =  ["Price", "Rate Plan",
                                    "Bedrooms", "Bathrooms",
                                    "Max Guests", "Quant Avail",
                                    "Hotel Name", "Room Name",
                                    "Managed By"])
    

if st.sidebar.button("Search & Quote"):
    st.session_state.checkin_dt = pd.to_datetime(checkin_input)
    st.session_state.checkout_dt = pd.to_datetime(checkout_input)
    st.session_state.nights = (st.session_state.checkout_dt - st.session_state.checkin_dt).days

    
    st.session_state.checkin = checkin_input
    st.session_state.checkout = checkout_input
    st.session_state.guests_input = guests_input

    
    
    start_time = time.time()


    hotel_ids_list = get_RBhotel_list(auth = auth)

    hotel_list_time = time.time() - start_time


    resp_dict = get_stays_string(auth,
                                 hotel_ids_list,
                                 checkin_input,
                                 checkout_input,
                                 guests_input)


    st.session_state.stays = create_quote_df(resp_dict, management_dict)



if "checkin_dt" and "checkout_dt" in st.session_state:
    with writing_container:
            date_line = f"**Check in** - {st.session_state.checkin_dt.strftime('%B %d, %Y')} and  \
                        **check out** - {st.session_state.checkout_dt.strftime('%B %d, %Y')} \
                        ({st.session_state.nights} nights)"
            st.write(date_line)
            st.write(f" Your early bird price for guests is - ")
            st.write(f"Early bird pricing requires full payment by ")


bed_bath_list = ["-All", 1, 2, 3, 4, 5, 6, 7, 8]
bedrooms = st.sidebar.multiselect(
    "Filter by bedrooms",
    options= bed_bath_list,
    default="-All"     
    )


if "-All" in bedrooms:
    bedrooms = bed_bath_list



df_selection = st.session_state.stays


management_list = df_selection["Managed By"].unique().tolist()
management_list.insert(0, "-All")


management = st.sidebar.multiselect(
    "Filter management company",
    options = management_list,
    default = "-All"
)

if "-All" in management:
    management = management_list

if "Hotels" in management:
    management = ["Chatrium Niseko", "Aya Niseko", "The Vale Niseko",
                  "Niseko Kyo",]


unbookable_list = ["SnowDog Village",
              "Suiboku",
              "Always Niseko",
              "Roku"
              ]


unbookable = st.sidebar.multiselect(
        "Include all properties",
        options = ["Yes", "No"],
        default = ["No"]
)

if "No" in unbookable:
    df_selection = df_selection[~df_selection["Hotel Name"].isin(unbookable_list)]


df_selection = df_selection[df_selection["Rate Plan"] != "HN OTA"]

df_selection["hotel_room_name"] = df_selection["Hotel Name"] + \
                                        " " + df_selection["Room Name"]

df_selection["Commission"] = np.where(df_selection["Managed By"] == "HN",
                                      df_selection.Price * 0.25, df_selection.Price * 0.2)
df_selection["Commission"] = df_selection["Commission"].astype(int)

df_selection["Per Night"] = df_selection["Price"].astype(int) / st.session_state.nights

df_selection = df_selection.query("""Bedrooms == @bedrooms \
                                            & `Managed By` == @management""") #& `Max Guests` == @max_guests
# df_selection.index.name = "index"

df_selection = df_selection.reset_index().rename(columns={"index": "Room"})

df_selection.sort_values(by = ["Price","Room"], inplace= True)


st.write(f"###### {df_selection.hotel_room_name.nunique()} Rooms")



st.dataframe(df_selection[["Room", "Price", "Per Night", "Bedrooms", 
                           "Bathrooms", "Max Guests",
                           "Quant Avail","Managed By"]],
                           1100, 700, hide_index = True,)



