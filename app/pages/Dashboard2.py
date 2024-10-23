# Marketing dashboard lookigng at Mailchimp, Enquiries & GA4

import datetime
import os
import itertools
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px

import pandas as pd
import streamlit as st
import seaborn as sns

from src.utils import load_csv_data

from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

st.set_page_config(page_title = "Marketing Dashboard",
                   layout="wide")



load_dotenv()
ga4_prop_id = os.getenv("ga4_prop_id")
hn_key = os.getenv("api_key")


# ga4_prop_id = "385376735"
start_date = "01092024"
end_date = "08092024"

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv("ga4_json_creds")


def get_mailchimp():

    df = load_csv_data("../../Downloads/Mailchimp.csv")

    df["Send Time"] = pd.to_datetime(df["Send Time"]).dt.tz_localize(None)
    df["Sent"] = pd.to_datetime(df["Sent"]).dt.date


    df = df[df["Send Time"] > pd.to_datetime("2023/01/01 01:00:00")]



    df["Open Rate"] = round(df["Open Rate"] * 100,1)

    # Filter to split year
    df["Year"] = np.where(df["Send Time"].between(
                                            "2024-01-01","2024-12-31"),
                                            "2024",
                                            "2023"
                                            )

    df["Send Time"] = np.where(df["Year"] == "2023",
                               df["Send Time"] + pd.DateOffset(years=1),
                               df["Send Time"])

    df.sort_values(
                by = "Send Time",
                ascending = True,
                inplace = True)

    st.write(df)
    return df

def plot_open_rate(mc_df):

    fig = px.line(
        mc_df,
        x = "Send Time",
        y = "Unique Opens",
        color = "Year",
        markers = True
        # text = "Open Rate",
        
        )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(
        dtick = "M1",
        tickformat = "%b"
    )
    
    fig.update_layout(
    xaxis=dict(
        showline=True,
        showgrid=False,
        showticklabels=True,
        linecolor='rgb(204, 204, 204)',
        linewidth=2,
        ticks='outside',
        tickfont=dict(
            family='Arial',
            size=12,
            color='rgb(82, 82, 82)',
        ),
    ),
    yaxis=dict(
        showgrid=True,
        zeroline=False,
        showline=False,
        showticklabels=True,
    ),
    autosize=False,
    margin=dict(
        autoexpand=False,
        l=100,
        r=20,
        t=110,
    ),
    showlegend=True,
    plot_bgcolor='white'
)

    
    st.plotly_chart(fig)
    pass

def get_weekly_views(property_id = ga4_prop_id):
    
    """Runs a simple report on a Google Analytics 4 property."""

    # [START analyticsdata_run_report_initialize]
    # Using a default constructor instructs the client to use the credentials
    # specified in GOOGLE_APPLICATION_CREDENTIALS environment variable.
    client = BetaAnalyticsDataClient()
    # [END analyticsdata_run_report_initialize]

    # [START analyticsdata_run_report]
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="week")],
        metrics=[Metric(name="activeUsers")],
        date_ranges=[DateRange(start_date="2024-01-01", end_date="today")],
        # order_by= ["VALUE",
        #       "sortOrder": "DESCENDING",
        #       "fieldName": "ga:searchUniques"
    )
    response = client.run_report(request)
    # [END analyticsdata_run_report]

    # [STA
    # RT analyticsdata_run_report_response]

    df = convert_to_pandas(response)
    
    df.sort_values(by = "week", ascending= False, inplace=True)

    return df


def convert_to_pandas(data):

    # Grab all the columns in the result
    st.write("IN THE FUNCTION")
    columns = []
    for col in data.dimension_headers:
        columns.append(col.name)
    for col in data.metric_headers:
        columns.append(col.name)

    # Grab all the rows in the result.
    rows = []
    for row_data in data.rows:
        row = []
        for val in row_data.dimension_values:
            row.append(val.value)
        for val in row_data.metric_values:
            row.append(val.value)
        rows.append(row)

    # convert to data frame
    return pd.DataFrame(rows, columns=columns)

if __name__ == "__main__":
    # get_weekly_views()
    df = get_mailchimp()
    plot_open_rate(df)