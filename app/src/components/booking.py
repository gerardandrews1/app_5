# Booking class to parse API response 
import csv
import datetime
import json
import os
import pandas as pd
import requests
import numpy as np
import streamlit as st


from ratelimit import limits, sleep_and_retry
from dataclasses import dataclass, asdict


@dataclass
class Booking:
    
    """
     Parse API response from json
    """
    
    given_name: str
    family_name: str
    guest_email: str
    booking_id: int # maybe change this name hey
    eId: int
    main_component: str
    created_date: str
    inv_pays = False
    rboss_launch = str


    def __init__(self, json_response, api_type):
        

        self.booking_id = ""
        self.eId = ""
        self.custom_id = ""


        self.get_hn_props()

        # 1 Get the dictionaries

        # this is where I get check the API type
        self.json_response = json_response


        if api_type == "listBooking":
                
            self.booking_dict = json_response.get("order", {}).get("bookings")
            self.lead_guest_dict = json_response.get("order", {}).get("leadGuest", {})
            self.pay_inv_dict = json_response.get("order", {}).get("invoicePayments", {})

        
            # 2 Parse the dictionaries
            if self.booking_dict is not None:
                self.parse_book_dict()

            self.parse_lead_guest(self.lead_guest_dict)

            
            # Here I feel like I need to run self check function on booking
            # like check if accom or float, check if cancelled, check blah blah

            if self.pay_inv_dict:
                self.parse_payment_info(self.pay_inv_dict)
            # 2 here i use parsed data to add additional info to booking

            if self.booking_id:
                self.rboss_launch = f"https://app.roomboss.com/ui/"+\
                                     "booking/edit.jsf?bid={self.booking_id}" 
                
                self.gsg_link = f"https://holidayniseko2.evoke.jp/public/booking/order02.jsf?mv=1&vs=WinterGuestServices&bookingEid={self.eId}"
        
            self.attribute_booking()

        else:

            st.write("Incorrect API type")     
        
        
  
        # Helper function used to colour payments

    def get_hn_props(self):

        # Get list of hn_props
        with open("app/data/hn_props.txt", 'r') as hn_props_text:
            hn_props_raw = hn_props_text.read().split(",")
            self.hn_props = [x.strip() for x in hn_props_raw]

            return


    def print_json(self):
        st.write(self.json_response)


    def parse_lead_guest(self, lead_guest_dict):
        
        # Get lead guest info from guest dict

        self.guest_email = lead_guest_dict.get("email", {None})
        self.guest_phone = lead_guest_dict.get("phoneNumber", {None})
        self.given_name = lead_guest_dict.get("givenName", {None})
        self.family_name = lead_guest_dict.get("familyName", {None})
        self.full_name = f"{self.given_name} {self.family_name}"
        self.nationality = lead_guest_dict.get("nationality", {None})

        if (self.guest_email != None) & (self.eId != None):
            self.payment_link = f"https://holidayniseko.evoke.jp/public/"+\
                            "yourbooking.jsf?id={self.eId}&em={self.guest_email}"


        return

    
    
    def parse_book_dict(self):
        
        # Checks if accom or service booking and then parses accordingly
        booking_dict = self.booking_dict

        for booking in booking_dict:

            if booking.get("bookingType") == "ACCOMMODATION":
                
                self.parse_accom_item(booking)
    
            elif booking.get("bookingType") == "SERVICE":
                self.parse_service_item(booking)

        return
    
    def parse_accom_item(self, booking):
        
        # create all the values/attributes for the booking
        # return nothing really, maybe just a true

        booking_df = pd.DataFrame(
                            columns=["Check-in","Check-out", "Nights",
                                    "Guests", "Property","Room","Rate"])


        self.eId = booking.get("eId", {None})
        self.active_check = booking.get("active")
        self.booking_id = booking.get("bookingId")
        self.booking_source = booking.get("bookingSource", {})
        self.created_user = booking.get("createdUser", {})
        self.custom_id = booking.get("customId")
        created_date = booking.get("createdDate", {})
        created_date = pd.to_datetime(created_date) + pd.offsets.Hour(9)


        self.created_date = created_date.strftime("%d-%b-%Y")
        self.extent = booking.get("extent", {})
        self.vendor_url = booking.get("hotel", {}).get("hotelUrl", {})
        self.vendor = booking.get("hotel", {}).get("hotelName", {})

        self.managed_by = ""


        if self.vendor in self.hn_props:
            self.managed_by = "HN"


        else:

            self.managed_by = "Non Managed"

        self.url = booking.get("url")
        self.rooms_booked = booking.get("items", {})
        self.notes = booking.get("notes")

        # Finally extract the rooms booked
        self.room_dict = self.parse_room_list(self.rooms_booked)

        pass
 
    def parse_room_list(self, room_list):
        

        # Next I need to parse the rooms
        rooms_dict = {}
        booking_accom_total = 0

        for room in room_list:

            curr_room_dict = {}

            room_name = room.get("roomType", {}).get("roomTypeName", {})
            curr_room_dict["room_name"] = room_name

            dict_key = f"{self.vendor} {room_name}"
            vendor = self.vendor

            room_checkin = room.get("checkIn", {})
            room_checkin = room_checkin.replace("-","/")

            self.accom_checkin = room_checkin
            curr_room_dict["check_in"] = room_checkin

            room_checkout = room.get("checkOut", {})
            room_checkout = room_checkout.replace("-","/")
            self.accom_checkout = room_checkout
            curr_room_dict["check_out"] = room_checkout
            
            
            room_guests = room.get("numberGuests", {})
            curr_room_dict["number_guests"] = room_guests
            self.guests = room_guests

            nights = (pd.to_datetime(room_checkout) - pd.to_datetime(room_checkin)).days
            self.nights = nights
            curr_room_dict["nights"] = nights

            curr_room_dict["room_rack"] = room.get("priceRack", {})
            curr_room_dict["room_net"] = room.get("priceNet", {})

            price_retail =  room.get("priceRetail", {})
            curr_room_dict["room_retail_price"] = price_retail

            
            rooms_dict[f"{dict_key}"] = curr_room_dict
            
            # Add to the total if multiple rooms
            booking_accom_total += price_retail
   
        # set the total for the booking
        self.accom_total = booking_accom_total


            
        return rooms_dict
            


    def parse_service_item(self, booking):
        
        # I'd like to make a headline for each guest service

        active = booking.get("active", {})
        self.eId  = booking.get("eId", {})
        extent = booking.get("extent", {})
        guest_service_id = booking.get("bookingId")
        service_id = booking.get("eId", {})
        
        gs_items = booking.get("items", {})
        
        for item in gs_items:
                
            provider = booking.get("serviceProvider", {}).get("serviceProviderName")
            service_name = item.get("service", {}).get("serviceName", {})
            start_date = item.get("startDate")
            end_date = item.get("endDate")

            # Adjustment string dates and calc days
            start_date = start_date.replace("-","/")
            end_date = end_date.replace("-","/")
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
            
            price_net = item.get("priceNet", {})
            price_rack = item.get("priceRack", {})
            price_sell = item.get("priceRetail", {})
            price_sell = f"¥{price_sell:,.0f}"

            # Add days to description of Rhythm items
            if provider == "Rhythm Niseko":
                days = days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
                
                service_name = f"{service_name} - {days} days"

            return None

    def parse_payment_info(self, pay_inv_dict):

        """
        Get the payment info dictionary and parse into dataframe
        Set the self payment_info_df
        
            Returns
                payment_info_df: dataframe to be written to app (not yet styled)
        """

        self.payment_info_df = pd.DataFrame(
                    columns = ["Invoice Number", "Date Created", "Amount",
                               "Due Date", "Payment Amount", "Date Paid",
                               "Payment ID"])



        for invoice in pay_inv_dict:

            invoice_number = invoice.get("invoiceNumber")
            amount = invoice.get("invoiceAmount", {})
            # st.write(amount)
            # amount = f"¥{amount:,.0f}"
            invoice_date = invoice.get("invoiceDate", {})
            invoice_number = invoice.get("invoiceNumber", {})
            due_date = invoice.get("invoiceDueDate", {})
            payment_amount = invoice.get("paymentAmount", {})
            # payment_amount = f"¥{payment_amount:,.0f}"

            payment_date = invoice.get("paymentDate", {})
            if payment_date == None:
                payment_date = ""

            payment_id = invoice.get("paymentId", {})
            
            # Do a quick regex check for flywire toka
            
            pay_line = [invoice_number, invoice_date, amount, due_date,
                        payment_amount, payment_date, payment_id]
            # st.write(pay_line)
            
            self.payment_info_df.loc[len(self.payment_info_df)] = pay_line

        self.amount_invoiced = self.payment_info_df.Amount.sum()
        self.amount_received = self.payment_info_df["Payment Amount"].sum()

        pass



    def write_payment_info(self):

        """ Creates the payments and invoices dataframe to the system
            
            Returns
                payment_html_string: pandas styler to render dataframe in html
        """
        management = self.managed_by


        def highlight_unpaid(s):
            """ Used to colour payment df if not paid """
            

            # For non managed not paid

            if (s["Payment Amount"] == 0) & (self.managed_by == "Non Managed") & (s.Amount > 0):
                return ['background-color: #ffb09c'] * len(s)
            
            # HN Managed not paid
            elif (s["Payment Amount"] == 0) & (self.booking_source_1 != "OTA") & (s.Amount > 0):

                return ['background-color: #ffead5'] * len(s)    
            
            # Paid
            else:
                return ['background-color: white'] * len(s)

        st.markdown("###### Invoices and Payments")

        # if self.payment_info_df:
        if self.pay_inv_dict:
            payment_info_df = self.payment_info_df
            payment_info_df["Date Created"] = pd.to_datetime(payment_info_df["Date Created"])
            payment_info_df["Due Date"] = pd.to_datetime(payment_info_df["Due Date"])

            payment_info_df["Date Paid"] = pd.to_datetime(payment_info_df["Date Paid"], errors="coerce")


            st.markdown(self.payment_info_df.style.hide(axis="index")
                        .apply(highlight_unpaid, axis=1)
                        .format({"Date Created": lambda x: "{}".format(x.strftime("%d %b %Y")),
                                 "Due Date": lambda x: "{}".format(x.strftime("%d %b %Y")),
                                 "Date Paid": lambda x: "{}".format(x.strftime("%d %b %Y") if pd.notnull(x) else ''),
                                              "Amount": "¥{:,.0f}",
                                              "Payment Amount": "¥{:,.0f}",
                                })
                        .set_table_styles([{'selector': 'th', 'props': [('font-size', '10pt'),('text-align','center')]}])
                        .set_properties(**{'font-size': '8pt','text-align':'center'}).to_html(),unsafe_allow_html=True)
        
        pass


    def write_gsg_upsell(self):

        """ The plan is that we want to use this function to
            write all of the email blah blah
            that I would normallly write"""        


        st.markdown("""
                    <style>
                    .email-font {
                        font-size:12px ;   white-space: nowrap;

                    }
                    </style>
                    """, unsafe_allow_html=True)
        
        if self.guest_email == None:
            st.markdown("No email")        

        else:
            st.markdown(f"""<p class='email-font'> You can make payment \n
                        and check the details of your booking
                         <a href='{self.gsg_link}'>here</a> </p>""",
                          unsafe_allow_html = True)

        # st.markdown("<p class='big-font'> You can make payment and check the details of your booking [here.](%s)" % pay_str)

        pass





    def write_key_booking_info(self):

        # st.write(f"{self.active_check}")
        st.markdown(f"###### {self.eId} - {self.full_name}")

        st.write(f"Created - {self.created_date} ")

        st.write(f"{self.managed_by}")

        if self.active_check == True:
            st.write(f"Booking is **:green[Active]**")
        else:
            st.write(f"Booking is :red[Cancelled]")

        st.write(self.guest_email)


        st.markdown(f"[Open #{self.eId} in RoomBoss](%s)" % self.rboss_launch)



        if (self.guest_email != None) & (self.eId != None):
            st.markdown(f"[Payment Link](%s)" % self.payment_link)

        st.markdown(f"[GSG Link #{self.eId}](%s)" % self.gsg_link)


    def write_email_subject(self):

        self.email_subject_line = (f"Booking #{self.eId} {self.vendor} "
                                f"{self.accom_checkin} - {self.accom_checkout} "
                                f"({self.nights} nights, {self.guests} guests)")
        
        st.write(self.email_subject_line)

        return None


    def write_guest_info(self):
        

        if self.guest_phone:
            st.write(f":telephone_receiver:", self.guest_phone)

        else:
            st.write("No phone number in roomboss")
        if self.guest_email:
            st.write(self.guest_email)
        else:
            st.write("No email")
        pass




    def write_room_info(self, room_dict):
        """Take room dictionary return 
           the room info in df format to write to streamlit"""

        # init dataframe for accom bookings
        booking_df = pd.DataFrame(
                        columns=["Check-in", "Check-out", "Nights",
                                "Guests", "Property", "Room", "Rate"])

        st.markdown(f"###### Booking #{self.eId}")

        for key, value in room_dict.items():

            booking_line = [room_dict[key].get("check_in"),
                            room_dict[key].get("check_out"),
                            room_dict[key].get("nights"),
                            room_dict[key].get("number_guests"),
                            self.vendor,
                            room_dict[key].get("room_name"),
                            f"¥{room_dict[key].get('room_retail_price'):,.0f}"]



                
            booking_df.loc[len(booking_df)] = booking_line


        st.markdown(booking_df.style.hide(axis="index")\
                .set_table_styles([{'selector': 'th', 'props': [('font-size', '10pt'),('text-align','center')]}])\
                .set_properties(**{'font-size': '8pt','text-align':'center'}).to_html(),unsafe_allow_html=True)

   
        return None


    def attribute_booking(self):

        """
        Split booking source by channel 1 and 2 and set self.channel 1 & 2
        Channel 1 = OTA, Website, Agent
        Channel 2 = Agent Name, Airbnb, Mailchimp, Facebook etc.
        """
        
        ### I reckon find the source 2 and work backwards
        self.booking_source_1 = ""
        self.booking_source_2 = ""

        # st.write(self.created_user, self.custom_id, self.booking_source)


        # If airbnb then check custom id matches, bk source: rb channel manager
        airbnb_prefixes = ["hmc" "HMNAYYQCQR"]  # len() of custom id string is 10

        if self.custom_id != None:

            if len(self.custom_id) > 0:
                if (self.custom_id[0] == "H") & \
                (self.booking_source.lower() == "roomboss channel manager"):
                    
                    self.booking_source_1 = "OTA"

                    self.booking_source_2 = "Airbnb"

            # st.write(self.booking_source_2)
        # booking.com, created user: Null, bk source: rb channel manager
        booking_dot_com = [4187716971, 4129682983, 4009522141, 4146358347]

        # if book and pay, no custom ID and web on the invoice number, Created user: Null
        if self.custom_id == None or self.custom_id == "":
            self.booking_source_1 = "Book and Pay"


        # if custom id is anything else then attribute to agent,
        agents = ["j", "d", "as", "perrin", "ash", "ryo"]

        if self.custom_id != None:
            if self.custom_id.lower() in agents:
                self.booking_source_1 = "HN Staff"
                self.booking_source_2 = self.custom_id 
            # if self.custom_id != "":


        pass


    def to_dataframe(self, json_response):

        if self.managed_by == "HN":
            hn_prop = 1
        else:
            hn_prop = 0

        bk_details_dict = {

                        "Created" : self.created_date,
                        "ID" : self.eId,
                        "Lead Guest" : self.full_name,
                        "Vendor" : self.vendor,
                        "Gross" : "¥0 TO DO",
                        "Residency" : "TO DO",
                        "Checkin Date" : self.accom_checkin,
                        "Nights" : self.nights,
                        "HN_Prop" : hn_prop
                        }
        
