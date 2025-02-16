# File to hold the utility functions

import datetime
import os
import glob
import gspread
import io
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
from pathlib import Path
from google.oauth2.service_account import Credentials


def create_cognito_link(reservation_number, check_in, check_out, accommodation, first_name, last_name, email):
    # Replace special characters
    formatted_email = email.replace('@', '%40')
    formatted_accommodation = accommodation.replace(' ', '%20')
    formatted_first_name = first_name.replace(' ', '%20')
    formatted_last_name = last_name.replace(' ', '%20')
    formatted_first_name = formatted_first_name.strip()
    formatted_last_name = formatted_last_name.strip()

    
    # Format dates to ensure they use hyphens in the URL
    formatted_check_in = check_in.replace('/', '-')
    formatted_check_out = check_out.replace('/', '-')
    
    base_url = "https://www.cognitoforms.com/HolidayNiseko/HolidayNisekoOnlineCheckinGuestRegistration"
    
    entry_data = {
        "HolidayNisekoReservationNumber": reservation_number,
        "CheckinDate": formatted_check_in,
        "CheckoutDate": formatted_check_out,
        "Accommodation": formatted_accommodation,
        "LeadGuestFirstName": formatted_first_name,
        "LeadGuestLastName": formatted_last_name,
        "Email": formatted_email
    }
    
    # Create the entry parameter
    entry = "%7B"  # Opening curly brace in URL encoding
    for i, (key, value) in enumerate(entry_data.items()):
        if i > 0:
            entry += "%2C"  # Comma in URL encoding
        entry += f'%22{key}%22%3A%22{value}%22'  # Key and value with quotes
    entry += "%7D"  # Closing curly brace in URL encoding
    
    return f"{base_url}?entry={entry}"

    
def connect_to_gspread():
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']

    credentials_dict = {
        "type": st.secrets["general"]["type"],
        "project_id": st.secrets["general"]["project_id"],
        "private_key_id": st.secrets["general"]["private_key_id"],
        "private_key": st.secrets["general"]["private_key"],
        "client_email": st.secrets["general"]["client_email"],
        "client_id": st.secrets["general"]["client_id"],
        "auth_uri": st.secrets["general"]["auth_uri"],
        "token_uri": st.secrets["general"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["general"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["general"]["client_x509_cert_url"]
    }

    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scope
    )

    return gspread.authorize(credentials)

def get_cognito_sheet_data():


    try:
        # Connect to Google Sheets
        gc = connect_to_gspread()

        # Open spreadsheet and worksheet
        spreadsheet = gc.open("All Bookings")
        worksheet = spreadsheet.get_worksheet(2)
        
        # Read data
        data = worksheet.get_all_values()
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        
        return df


    except Exception:
        return


def get_cognito_info(ebook_id, df):

    result = df.loc[df["HolidayNisekoReservationNumber"] == ebook_id]

    # I will do some cleaning of the result here

    return result

    
def build_css_table(eId,
                    phone,
                    arv_time,
                    cognito_done):
                  
    if phone == "":
        phone = "-"

    
# Custom CSS for the table
    css = f"""
            <style>
            .booking-table {{
                width: 100%;
                border-collapse: collapse;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}

            .booking-table th {{
                background-color: #f8f8f8;
                padding: 12px 8px;
                text-align: left;
                border-bottom: 2px solid #2B7A33;
                width: 40%;
            }}

            .booking-table td {{
                padding: 12px 8px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}

            .status {{
                padding: 2px 8px;
                border-radius: 12px;
                background-color: #FFD700;
            }}

            .reference {{
                color: #2B7A33;
                font-weight: 500;
            }}
            </style>

            <table class="booking-table">
                <tr>
                    <th>Cognito Completed</th>
                    <td><span class="reference">{cognito_done}</span></td>
                </tr>
                <tr>
                    <th>&#128222</th>
                    <td>{phone}</td>
                </tr>
                <tr>
                    <th>Expected arrival time Niseko</th>
                    <td>{arv_time}</td>
                </tr>
           
                
                
            </table>    
                """
                
    st.markdown(css, unsafe_allow_html=True)

        
    pass



def set_management_variable(variable, file_name):
    
    """Opens the file and gets the list of current props
    
    for that management company
    """

    try: 
        with open(f"data/{file_name}.txt", 'r') as text:
            props_raw = text.read().split(",")
            prop_list = [x.strip() for x in props_raw]
            return prop_list

    # File setup different locally vs on the github instance
    except FileNotFoundError as e:
        
        with open(f"app/data/{file_name}.txt", 'r') as text:
            props_raw = text.read().split(",")
            prop_list = [x.strip() for x in props_raw]
            return prop_list
    pass


def percent_change(percent_change_figure):
                    
                if percent_change_figure > 0: 
                    css_class = "increase"
                    arrow = "&#9650"
                
                else: 
                    css_class = "decrease"
                    arrow = "&#9660"

                return css_class, arrow

def single_hbar_setup(title: str):

    """Setup the hbars for breakdowns"""
    
    fig, ax = plt.subplots(figsize = (4,2.5))
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(title,
                size = 8,
                loc = "left")
    
    
    fig.axes[0].spines[["top", "left", "right", "bottom"]].set_visible(False)
    fig.axes[0].xaxis.set_major_formatter(formatter)
    fig.axes[0].tick_params(
                                top=False,
                                bottom=True,
                                left=True,
                                right=False,
                                labelleft=True,
                                labelbottom=False,
                                labelsize = 6,
                                color = "#D4D4D4",
                                labelcolor = "#4C4646",
                                length = 1,
                                pad = 1)
    
    plt.subplots_adjust(left=-0.04)

    return fig, ax
    
def single_hbar_labels(ax):

    """Add bar labels to single hbars"""
    for i in ax.containers:
        ax.bar_label(
                    i,
                    fmt = format_millions,
                    color = "#4C4646",
                    size = 6.5)
        
    pass

def add_bar_labels(ax, total_23):# Add bar labels
    
    # Add labels to bar on graph
    # for axis in ax:
    #     for sub_axis in axis:
    for i in ax.containers:
        ax.bar_label(
            i,
            fmt = format_millions,
            color = "#242124",
            size = 6)
        # Add 23 total

        # formatted_total = format_millions(total_23)
        ax.set_xticks([total_23],
                      labels = [format_millions(total_23)]
                      )
    pass

def plot_setup(rows, cols):

    fig, ax = plt.subplots(rows, cols,
                           width_ratios=[9, 1.3],
                           figsize = (8,4))
    plt.subplot(rows,cols,1)

    for x in range(0,rows*cols,2):
        
        # Horizontal bars
        fig.axes[x].tick_params(
                            top=False,
                            bottom=True,
                            left=False,
                            right=False,
                            labelleft=False,
                            labelbottom=True,
                            labelsize = 6,
                            color = "#4C4646",
                            labelcolor = "#4C4646",
                            length = 1,
                            pad = 1)
        
        fig.axes[x].spines[["top", "left", "right"]].set_visible(False)
        fig.axes[x].spines[["bottom", ]].set_color('#D4D4D4')

        
        # Numbers subplot formatting
        fig.axes[x+1].tick_params(
                            top=False,
                            bottom=False,
                            left=False,
                            right=False,
                            labelleft=False,
                            labelbottom=False,
                            labelsize = 6,
                            color = "#D4D4D4",
                            )
        
        fig.axes[x+1].spines[["top", "left", "right"]].set_visible(False)
        fig.axes[x+1].spines[["bottom", ]].set_color('#D4D4D4')

    fig.subplots_adjust(wspace=0.05, hspace=0.3)
    fig.axes[0].xaxis.set_major_formatter(formatter)

    
    return fig, ax


def formatter(x, pos):
    return f"¥{int(round(x / 1e6, 0))}M"

def plot_xfactors(fig_dict, rows, cols):
        count = 2    
        for k in fig_dict.keys():
            
            plt.subplot(rows,cols,count)

            plt.annotate(
                f"{round(fig_dict[k][0]/fig_dict[k][1], 2)}x",
                (0.2, 0.35),
                fontsize = 7,
                color = "#4C4646")
            count += 2

def format_millions(figure):

    """Format millions for graphing"""

    if figure > 1000000:

        return f"¥{figure * 0.000001:.0f}M"
    
    elif figure > 15000:
        return f"¥{figure:,.0f}"

    else:
        return f"{figure:,.0f}"
    

def build_hbars(axis, figures_list, title: str):

    """Plot hbars for dashboard 2"""

    # 23 first
    axis.barh(
        y = [0.8],
        width = figures_list[1],
        color = "#DEDEDE", 
        height = 0.8,
        )
    
    axis.barh(
            y = [0],
            width = figures_list[0], # width of the bar from left position below
            left = [0],
            color = "#4571c4",
            height = 0.8,
            )
    
    axis.set_ylabel(title,
                    rotation = 0,
                    labelpad = 20,
                    fontsize = 8,
                    color = "#4C4646")
    # axis.yaxis.set_label_coords(-0.08,0.30)

    axis.vlines(x = figures_list[2],
        ymin = -0.2,
        ymax = 0.8,
        color = "#DEDEDE",
        linewidth = 1)
    

    # for idx, figure in enumerate(figures_list):

    #     if idx == 0:

    #         axis.annotate(
    #             format_millions(figure),
    #             (figures_list[idx], -0.1),
    #             fontsize = 3,
    #             color = "#4C4646")
                
    #     elif idx == 1:

    #         axis.annotate(
    #             format_millions(figure),
    #             (figures_list[idx], 0.7),
    #             fontsize = 3,
    #             color = "#4C4646") 

    pass
    

def build_bullet(total_2425, otd_2324, total_2324, title: str):

    """Plot bullet/bar charts for dashboard"""
    
    plt.barh(
         y = [1],
         width = [otd_2324], # width of the bar from left position below
         left = [0],
         color = '#DEDEDE',
         height = 1
    )

    plt.barh(
        y = [0],
        width = [total_2425],
        color = "#4571c4", 
        height = 1    
    )

    plt.vlines(x = total_2324,
            ymin = -0.2,
            ymax = 0.8,
            color = "#bbbbbb",
            linewidth = 3)
    
    plt.yticks([0.5], [title]) # Title


    pass

def month_splits_2324(df,column, season):
    
    """Allocates a booking to a month period 

    NOT IDEAL AS COLUMN BASED ON START DATE
    
    NEED TO MAKE ROBUST FOR STAYS THAT CROSS OVER PERIODS
    """
    
    first = season[0:2]
    second = season[2:4]

    # df[column] = pd.to_datetime(df[column])

    df["Stay Period"] = np.where(df[column].between(f"20{first}-12-01",f"20{first}-12-15"),"Early Dec",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{first}-12-16",f"20{first}-12-31"),"Late Dec",df["Stay Period"]) 
    df["Stay Period"] = np.where(df[column].between(f"20{second}-01-01",f"20{second}-01-15"),"Early Jan",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-01-15",f"20{second}-01-31"),"Late Jan",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-02-01",f"20{second}-02-15"),"Early Feb",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-02-16",f"20{second}-02-29"),"Late Feb",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-03-01",f"20{second}-03-15"),"Early Mar",df["Stay Period"])  
    df["Stay Period"] = np.where(df[column].between(f"20{second}-03-15",f"20{second}-03-31"),"Late Mar",df["Stay Period"])  

    return df

def create_otd_df(df, metric):

    years = {"2019":"'19/20'", "2022":"'22/23'", "2023":"'23/24'", "2024":"'24/25'"}

    new_df = pd.DataFrame()

    # This creates an on this day dataframe 

        

        

        


        # today_gb = today_df.groupby("Season")[metric].sum().reset_index().sort_values(by = "Season",ascending = True)
        # new_df = pd.concat([new_df, today_df])

    today_df = df[df.Season == "'23/24'"]

    today_str = "2024" + datetime.datetime.today().strftime('%Y-%m-%d')[4:]
    
    today_date = pd.to_datetime(today_str)

    today_df = today_df[today_df.Created <= today_date]

    # Sort first
    today_df.sort_values(by="Season", ascending=False, inplace=True)

    st.write("TODAY",today_df)
    
    # # Only set to 0 if we have that season
    # season_24_25 = new_df[new_df.Season == "'24/25'"]
    # if not season_24_25.empty:
    #     new_df.loc[new_df.Season == "'24/25'", metric] = 0

    return today_df
    


@st.cache_data
def load_env_var():
    # Load env variables

    load_dotenv()

    hn_id = os.getenv("api_id")
    hn_key = os.getenv("api_key")

    auth = (hn_id, hn_key)

    return auth


def get_prop_management():

    """
    Get the management dictionaries 
    """
    # Load global variables hotel management lists
    props_directory = "data/"
    localVars = locals()

    file_list = glob.glob(props_directory + "/*.txt")

    # Sets variables for hn, h2, vn, hokkaido_travel, mnk, nisade etc
    management_dict = {}
    for file in file_list:

        with open(file) as text_file:
            
            holder = text_file.read().split(",") 
            management_dict[Path(file).stem] = [x.strip() for x in holder] 

    return management_dict

def highlight_unpaid_inv(s):
    
    """Highlight non managed unpaid invoices"""

    if (s["HN_Prop"] == 0):
        return ['background-color: #ffb09c'] * len(s)
    
    # HN Managed not paid
    # elif (s["Received"] == 0) & \
    #     (s["Sales Channel"] != "OTA") & (s["Invoiced"] > 0):

    #     return ['background-color: #ffead5'] * len(s)    
    
    # # Paid
    # else:
    #     return ['background-color: white'] * len(s)
    
    pass

def highlight_unpaid(s):

    """ Used to colour payment df if not paid """
    

    # For non managed not paid

    if (s["Received"] == 0) & \
        (s["Managed by"] != "HN") & (s["Invoiced"] > 0):
        return ['background-color: #ffb09c'] * len(s)
    
    # HN Managed not paid
    elif (s["Received"] == 0) & \
        (s["Sales Channel"] != "OTA") & (s["Invoiced"] > 0):

        return ['background-color: #ffead5'] * len(s)    
    
    # Paid
    else:
        return ['background-color: white'] * len(s)
    
    pass


@st.cache_data
def load_csv_data(path: str):

    """Function to cache csv for streamlit"""

    df = pd.read_csv(path)
    return df


def clean_accom_df(accom_df, month_split_column, remove_zero = False):

    # Remove owner stays
    if remove_zero ==  True:
        accom_df = accom_df[accom_df["Zero Stay"] == 0]
    
    accom_df["Count"] = 1 # column to utilise groupby sums
    accom_df.Created = pd.to_datetime(accom_df.Created, dayfirst = False)

    # for season in ["2324", "2425"]: add the start 1/2 month split
    accom_df["Stay Period"] = 0

    accom_df = month_splits_2324(accom_df, month_split_column, "1920")
    accom_df = month_splits_2324(accom_df, month_split_column, "2324")
    accom_df = month_splits_2324(accom_df, month_split_column, "2425")

    accom_df["Stay Month"] = pd.to_datetime(accom_df[month_split_column])\
                                                    .dt.month_name()

    # keep only seasons we care about
    keepers = [ #"'18/19'", # "'14/15'", "'15/16'", "'16/17'", "'17/18'", 
            "'19/20'","'22/23'","'23/24'", "'24/25'"]

    accom_df = accom_df[accom_df.Season.isin(keepers)]

    return accom_df

def clean_payments_df(payment_df):


    payment_df["Count"] = 1 # column to utilise groupby sums
    payment_df["Booking ID"] = payment_df["Booking ID"].astype(str)
    # Cast columns to datetime
    payment_df.Created = pd.to_datetime(payment_df.Created, dayfirst = False)
    payment_df["Due Date"] = pd.to_datetime(payment_df["Due Date"],
                                            dayfirst = False)

    # for season in ["2324", "2425"]: add the start 1/2 month split
   
    # keep only seasons we care about
    keepers = [ #"'18/19'", # "'14/15'", "'15/16'", "'16/17'", "'17/18'", 
            "'19/20'","'22/23'","'23/24'", "'24/25'"]

    payment_df = payment_df[payment_df.Season.isin(keepers)]

    return payment_df