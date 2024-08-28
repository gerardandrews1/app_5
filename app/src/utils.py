# File to hold the utility functions

import datetime
import os
import glob
import io
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
from pathlib import Path


def plot_setup(rows, cols):

    fig, ax = plt.subplots(rows, cols,
                           width_ratios=[9, 1],
                           figsize = (4,1.75))
    plt.subplot(rows,cols,1)

    for x in range(0,6,2):
        
        # Horizontal bars
        fig.axes[x].tick_params(
                            top=False,
                            bottom=True,
                            left=False,
                            right=False,
                            labelleft=False,
                            labelbottom=True,
                            labelsize = 4,
                            color = "#D4D4D4",
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
                            labelsize = 4,
                            color = "#D4D4D4",
                            )
        
        fig.axes[x+1].spines[["top", "left", "right"]].set_visible(False)
        fig.axes[x+1].spines[["bottom", ]].set_color('#D4D4D4')

    fig.subplots_adjust(wspace=0.05, hspace=0.3)
    fig.axes[0].xaxis.set_major_formatter(formatter)

    return fig, ax


def formatter(x, pos):
    return f"¥{int(round(x / 1e6, 0))}M"

def plot_xfactors(fig_dict):
        count = 2    
        for k in fig_dict.keys():
            
            plt.subplot(3,2,count)

            plt.annotate(
                f"{round(fig_dict[k][0]/fig_dict[k][1], 2)}x",
                (0.2, 0.35),
                fontsize = 5,
                color = "#4C4646")
            count += 2

def format_millions(figure):

    """Format millions for graphing"""

    if figure > 1000000:

        return f"¥{figure * 0.000001:.0f}M"
    
    else:
        return figure
    

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
            height = 0.8
            )
    
    axis.set_ylabel(title,
                    rotation = 0,
                    labelpad = 20,
                    fontsize = 6)
    axis.yaxis.set_label_coords(-0.1,0.30)

    axis.vlines(x = figures_list[2],
        ymin = -0.2,
        ymax = 0.8,
        color = "#bbbbbb",
        linewidth = 1.5)
    

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
    for key, value in years.items():

        today_str = key + datetime.datetime.today().strftime('%Y-%m-%d')[4:]

        today_df = df[df.Season == value]

        today_date = pd.to_datetime(today_str)

        today_df = today_df[today_df.Created < today_date]


        # today_gb = today_df.groupby("Season")[metric].sum().reset_index().sort_values(by = "Season",ascending = True)

        new_df = pd.concat([new_df, today_df])



    new_df.iloc[3, 1] = 0 # Sets the value for 24/25 to 0 so it doesn't draw over the top
    # To make the graph make sense
    new_df.sort_values(by = "Season", ascending = False, inplace = True)
    
    return new_df


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


def highlight_unpaid(self, s):

    """ Used to colour payment df if not paid """
    

    # For non managed not paid

    if (s["Payment Amount"] == 0) & \
        (self.managed_by == "Non Managed") & (s.Amount > 0):
        return ['background-color: #ffb09c'] * len(s)
    
    # HN Managed not paid
    elif (s["Payment Amount"] == 0) & \
        (self.booking_source_1 != "OTA") & (s.Amount > 0):

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


def clean_accom_df(accom_df, remove_zero=True):

    # Remove owner stays
    if remove_zero ==  True:
        accom_df = accom_df[accom_df["Zero Stay"] == 0]
    
    accom_df["Count"] = 1 # column to utilise groupby sums
    accom_df.Created = pd.to_datetime(accom_df.Created, dayfirst = False)

    # for season in ["2324", "2425"]: add the start 1/2 month split
    accom_df["Stay Period"] = 0

    accom_df = month_splits_2324(accom_df, "Start date", "1920")
    accom_df = month_splits_2324(accom_df, "Start date", "2324")
    accom_df = month_splits_2324(accom_df, "Start date", "2425")

    accom_df["Stay Month"] = pd.to_datetime(accom_df["Start date"]).dt.month_name()

    # keep only seasons we care about
    keepers = [ #"'18/19'", # "'14/15'", "'15/16'", "'16/17'", "'17/18'", 
            "'19/20'","'22/23'","'23/24'", "'24/25'"]

    accom_df = accom_df[accom_df.Season.isin(keepers)]

    return accom_df