# File to hold the utility functions
import os
import glob
import io
import streamlit as st


from dotenv import load_dotenv
from pathlib import Path


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

