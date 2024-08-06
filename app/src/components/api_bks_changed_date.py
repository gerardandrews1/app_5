# call the api for the bookings changed today
from datetime import datetime
import glob
import os
import json
import pandas as pd
import requests

from src.components.booking import BookingChangedDate

from ratelimit import limits

two_mins = 120 # For function below

# api call function
@limits(calls = 15, period = two_mins)
def call_api_bks_changed(date, api_id, api_key):
    
    """
    Call API with wrapper only 15 calls
    per 2 min limit imposed
    Using API credentials
    """


    url = f"https://api.roomboss.com/extws/hotel/v1/listBookings?date={date}&bookingType=ACCOMMODATION"
    
    auth = (api_id, api_key)
    
    response = requests.get(url, auth = auth)

    if response.status_code != 200:
        st.write(f"Error {response.status_code}")
        # raise Exception('API response: {}'.format(response.status_code))
    return response


def get_etl_time():
    """Silly little function to get the datetime the 
       etl process was run"""
    
    etl_filename = glob.glob("../../Downloads/ETL*")
    etl_filename = etl_filename[0][19:-4]

    # Probably a better way to do this
    year = etl_filename[0:5]
    month = etl_filename[5:7]
    day = etl_filename[7:9]
    hour = etl_filename[10:12]
    minute = etl_filename[12:14]

    etl_datetime = datetime(int(year), int(month), int(day),
                            int(hour), int(minute))
 
    return etl_datetime

def transform_api_resp_df(api_response):
     
    """ Get the api response and parse to dfs
        One for new bookings and then another 
        for updating """
     
    if api_response.status_code == 200:
        

        etl_time = get_etl_time()

        json_string = json.loads(api_response.text)


        returned_bookings = {}

        for count, booking in enumerate(json_string.get("bookings", {None})):
            
                eId = booking.get("eId")

                bk = BookingChangedDate(booking, "getChangedBookings")
                dict_line = bk.to_dict()
                returned_bookings[count] = dict_line


        api_df = pd.DataFrame(returned_bookings).T


        # Let's get new boooks

        api_df.Created = pd.to_datetime(api_df.Created).dt.tz_localize(None)
        api_df.Modified = pd.to_datetime(api_df.Modified).dt.tz_localize(None)

        new_books = api_df[(api_df.Created > etl_time) \
                           & api_df.Active == True]
        
        # new_books = new_books[[]]

        modified_books = api_df[api_df.Modified > etl_time]


        return new_books, modified_books
