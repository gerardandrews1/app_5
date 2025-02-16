import streamlit as st
import requests
import json
from datetime import datetime
import base64

# Page config
st.set_page_config(page_title="RoomBoss Package API Tester", layout="wide")

def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return date_str

def get_package_details(identifier, id_type="package"):
    """Fetch package details from the API"""
    base_url = "https://api.roomboss.com/extws/gs/v1/package"
    
    # Get credentials from secrets and create Basic Auth
    credentials = f"{st.secrets.api_id}:{st.secrets.api_key}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    # Print debug info
    st.sidebar.write("API ID:", st.secrets.api_id)
    st.sidebar.write("API Key:", st.secrets.api_key)
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    params = {
        "packageId" if id_type == "package" else "bookingEid": identifier,
        "lang": "en"
    }
    
    try:
        # Build complete URL for debugging
        complete_url = f"{base_url}?{requests.compat.urlencode(params)}"
        st.write("API URL being called:", complete_url)
        
        response = requests.get(base_url, headers=headers, params=params)
        
        # Always show the complete response
        st.write("Complete Response Details:")
        st.write("Status Code:", response.status_code)
        st.write("Response Headers:", dict(response.headers))
        try:
            json_response = response.json()
            st.json(json_response)
        except:
            st.write("Raw Response Content:", response.text)
            
        if response.status_code != 200:
            response.raise_for_status()
            
        return json_response
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# Sidebar for input
with st.sidebar:
    st.title("Search Options")
    search_type = st.radio("Search by:", ["Package ID", "Booking ID"])
    identifier = st.text_input("Enter ID", value="2050856")
    
    if st.button("Search"):
        if identifier:
            id_type = "package" if search_type == "Package ID" else "booking"
            data = get_package_details(identifier, id_type)
            if data:
                st.session_state.api_response = data
        else:
            st.warning("Please enter an ID")

# Main content area
st.title("RoomBoss Package API Tester")

if 'api_response' in st.session_state:
    data = st.session_state.api_response
    
    # Show raw JSON response
    with st.expander("Raw JSON Response", expanded=True):
        st.json(data)
    
    # Package Overview
    st.header("Package Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Package ID", data.get('package', {}).get('id', 'N/A'))
    with col2:
        st.metric("Total Amount", f"{data.get('package', {}).get('totalAmount', 0)} {data.get('package', {}).get('currencyCode', '')}")
    with col3:
        st.metric("Received Amount", f"{data.get('package', {}).get('receivedAmount', 0)} {data.get('package', {}).get('currencyCode', '')}")

    # Company Info
    st.subheader("Company Information")
    st.json({
        "Company Name": data.get('package', {}).get('companyName', ''),
        "Email": data.get('package', {}).get('companyEmail', ''),
        "Phone": data.get('package', {}).get('companyPhone', '')
    })

    # Bookings
    st.header("Bookings")
    bookings = data.get('package', {}).get('bookings', [])
    for idx, booking in enumerate(bookings):
        with st.expander(f"Booking {idx + 1} - ID: {booking.get('bookingId', 'N/A')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("Basic Information")
                st.json({
                    "Booking ID": booking.get('bookingId'),
                    "Custom ID": booking.get('customId'),
                    "Status": "Active" if booking.get('active') else "Cancelled",
                    "Type": booking.get('bookingType'),
                    "Source": booking.get('bookingSource'),
                    "Created": format_date(booking.get('createdDate')),
                    "Last Modified": format_date(booking.get('lastModifiedDate'))
                })
            
            with col2:
                if booking.get('serviceProvider'):
                    st.write("Service Provider")
                    st.json(booking['serviceProvider'])
            
            if booking.get('items'):
                st.write("Booking Items")
                for item in booking['items']:
                    st.json(item)

    # Invoice Payments
    st.header("Invoice & Payments")
    payments = data.get('package', {}).get('invoicePayments', [])
    for payment in payments:
        with st.expander(f"Invoice {payment.get('invoiceNumber', 'N/A')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("Invoice Details")
                st.json({
                    "Invoice Number": payment.get('invoiceNumber'),
                    "Amount": payment.get('invoiceAmount'),
                    "Due Date": payment.get('invoiceDueDate'),
                    "Created By": payment.get('invoiceCreatedBy'),
                    "Created Date": payment.get('invoiceCreatedDate')
                })
            
            with col2:
                st.write("Payment Details")
                st.json({
                    "Payment ID": payment.get('paymentId'),
                    "Amount": payment.get('paymentAmount'),
                    "Method": payment.get('paymentMethod'),
                    "Date": payment.get('paymentDate'),
                    "Created By": payment.get('paymentCreatedBy')
                })

else:
    st.info("Enter a Package ID or Booking ID in the sidebar to fetch data")