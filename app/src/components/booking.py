# Booking class to parse API response 
# and organise booking details

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
# from src.utils import highlight_unpaid
from src.utils import set_management_variable

## TODO separate streamlit UI processes to separate class
## TODO get min checkin and max check-out date for email subject 
## TODO finish  attribute booking and move higher
## TODO find a way to separate 2 x same room diff dates kevinfz example

@dataclass
class Booking:
    
    """
     Parse API response from json
    """
    
    def __init__(self, json_response, api_type):
        
        self.json_response = json_response
        self.booking_id = ""
        self.eId = ""
        self.custom_id = ""
        self.package_gs_list = []



        # st.write(json_response)
        self.service_guide = \
            ("https://holidayniseko.com/sites/default"
             "/files/services/2024-08/Holiday%20Niseko"
             "%20Guest%20Service%20Guide%202024_2025.pdf")
        
        # self.get_hn_props()
        self.set_prop_management_lists()

        # 1 Get the dictionaries
        # check API type
        if api_type == "listBooking":
                
            # accom & service bookings
            self.booking_dict = json_response\
                .get("order", {}).get("bookings")
            
            self.lead_guest_dict = json_response\
                .get("order", {}).get("leadGuest", {})
            
            self.pay_inv_dict = json_response\
                .get("order", {}).get("invoicePayments", {})

        
            # 2 Parse dictionaries
            if self.booking_dict is not None:
                self.parse_book_dict()

            self.parse_lead_guest(self.lead_guest_dict)

            if self.pay_inv_dict:
                self.parse_payment_info(self.pay_inv_dict)
            
            # 2 here i use parsed data for link creation
            if self.booking_id:
                self.rboss_launch = \
                "https://app.roomboss.com/ui/"\
                "booking/edit.jsf?bid="\
                + self.booking_id 
                
                self.gsg_link = \
                "https://holidayniseko2.evoke.jp/public/booking/order02"\
                ".jsf?mv=1&vs=WinterGuestServices&bookingEid="\
                + str(self.eId)
                
            self.attribute_booking()

        else:

            st.write("Incorrect API type")     
        
        
    def get_hn_props(self):

        """Get list of hn_props"""
        
        #try catch to work locally
        try: 
            with open("data/hn_props.txt", 'r') as hn_props_text:
                hn_props_raw = hn_props_text.read().split(",")
                self.hn_props = [x.strip() for x in hn_props_raw]

        except FileNotFoundError as e:
            with open("app/data/hn_props.txt", 'r') as hn_props_text:
                hn_props_raw = hn_props_text.read().split(",")
                self.hn_props = [x.strip() for x in hn_props_raw]

            return
        
    def set_prop_management_lists(self):

        """Get list of props for each management company"""
        hn_props = []
        vn_props = []
        h2_props = [] 
        hokkaido_travel_props = []
        mnk_props = []
        nisade_props = []
        

        self.hn_props = set_management_variable(hn_props, "hn_props")
        self.vn_props = set_management_variable(vn_props, "vn_props")
        self.h2_props = set_management_variable(h2_props, "h2_props")
        self.nisade_props = set_management_variable(nisade_props, "nisade_props")
        self.mnk_props = set_management_variable(mnk_props, "mnk_props")
        self.hokkaido_travel_props = set_management_variable(hokkaido_travel_props,
                                                        "hokkaido_travel_props")


    def print_json(self):

        """Used during testing to see the full json response"""
        
        st.write(self.json_response)
        return

    def parse_lead_guest(self, lead_guest_dict):
        
        """ Get lead guest info from guest dict"""

        self.guest_email = lead_guest_dict.get("email", {None})
        self.guest_phone = lead_guest_dict.get("phoneNumber", {None})
        self.given_name = lead_guest_dict.get("givenName", {None})
        self.family_name = lead_guest_dict.get("familyName", {None})
        self.full_name = f"{self.given_name} {self.family_name}"
        self.nationality = lead_guest_dict.get("nationality", {None})

        # Don't show payment link if no eid or no email
        if (self.guest_email != None) & (self.eId != None):
            self.payment_link = \
            "https://holidayniseko.evoke.jp/public/yourbooking"\
            ".jsf?id=" + str(self.eId) + "&em=" + self.guest_email

        else:
            self.payment_link = ""
        return

    def parse_book_dict(self):
        
        """Checks if accom or service item and parse accordingly"""

        booking_dict = self.booking_dict


        for booking in booking_dict:

            if booking.get("bookingType") == "ACCOMMODATION":
                
                # Get the correct eId for the booking
                try:

                    self.eId = self.json_response.get("order", {})\
                        .get("bookings", {})[0].get("eId")

                    
                except Exception as e:
                    st.write(e)

                self.parse_accom_item(booking)
    
            if booking.get("bookingType") == "SERVICE":
                self.parse_service_item(booking, self.package_gs_list)

        return
    
    def parse_accom_item(self, booking):
        
        """ Get key info for accom item not nested within the 
        
        room dictionary 
        """

        # self.eId = booking.get("eId", {None})
        self.active_check = booking.get("active")
        self.booking_id = booking.get("bookingId")
        self.booking_source = booking.get("bookingSource", {})
        self.created_user = booking.get("createdUser", {})
        self.custom_id = booking.get("customId")
        self.notes = booking.get("notes")
        self.url = booking.get("url")

        # offset creation time to local time
        created_date = booking.get("createdDate", {})
        created_date = pd.to_datetime(created_date) + pd.offsets.Hour(9)
        self.created_date = created_date.strftime("%d-%b-%Y")
        
        self.extent = booking.get("extent", {})
        self.vendor_url = booking.get("hotel", {}).get("hotelUrl", {})
        self.vendor = booking.get("hotel", {}).get("hotelName", {})

        # I need to functionise this and move it #
        # Check if self managed or not 
        if self.vendor in self.hn_props:
            self.managed_by = "Holiday Niseko"

        elif self.vendor in self.vn_props:
            self.managed_by = "Vacation Niseko"
        
        elif self.vendor in self.mnk_props:
            self.managed_by = "Mnk (Midori no Ki)"

        elif self.vendor in self.nisade_props:
            self.managed_by = "Nisade"

        elif self.vendor in self.h2_props:
            self.managed_by = "H2"

        elif self.vendor in self.hokkaido_travel_props:
            self.managed_by = "Hokkaido Travel - Andy"

        else:
            self.managed_by = "~ not sure, check roomboss"
        self.rooms_booked = booking.get("items", {})
        
        # Pass rooms dict to parsing function
        self.room_list_todf = self.parse_room_list2(self.rooms_booked)

        return
 
    def parse_room_list(self, room_list):
        
        """
        Parses room dictionary and calculates total 
        cost for each room
        """
        
        rooms_dict = {}
        self.booking_accom_total = 0
        self.guests = 0


        # loop through each room and create a dictionary for each room
        for room in room_list:

            curr_room_dict = {}

            room_name = room.get("roomType", {}).get("roomTypeName", {})
            curr_room_dict["room_name"] = room_name

            dict_key = f"{self.vendor} {room_name}"

            room_checkin = room.get("checkIn", {})
            room_checkin = room_checkin.replace("-","/")
            curr_room_dict["check_in"] = room_checkin

            room_checkout = room.get("checkOut", {})
            room_checkout = room_checkout.replace("-","/")
            curr_room_dict["check_out"] = room_checkout
            
            room_guests = room.get("numberGuests", {})
            curr_room_dict["number_guests"] = room_guests
            self.guests += room_guests

            nights = (pd.to_datetime(room_checkout) - pd.to_datetime(room_checkin)).days
            curr_room_dict["nights"] = nights
            self.nights = nights

            curr_room_dict["room_rack"] = room.get("priceRack", {})
            curr_room_dict["room_net"] = room.get("priceNet", {})

            price_retail =  room.get("priceRetail", {})
            curr_room_dict["room_retail_price"] = price_retail

            # Add back to master dictionary          
            rooms_dict[f"{dict_key}"] = curr_room_dict
            
            # Add to the total if multiple rooms
            self.booking_accom_total += price_retail
   
        # set the total for the booking
        self.accom_total = self.booking_accom_total


        return rooms_dict
    
    def parse_room_list2(self, room_list):
        
        """
        Parses room dictionary and calculates total 
        cost for each room
        """
        
        rooms_list_todf = []
        self.booking_accom_total = 0
        self.guests = 0


        # loop through each room and add details to a list
        # list over dictoinary in case 2 x rooms with same name
        for room in room_list:

            curr_room_list = []

            curr_room_list.append(self.vendor)
            room_name = room.get("roomType", {}).get("roomTypeName", {})
            curr_room_list.append(room_name)

            # dict_key = f"{self.vendor} {room_name}"

            room_checkin = room.get("checkIn", {})
            room_checkin = room_checkin.replace("-","/")
            curr_room_list.append(room_checkin)

            room_checkout = room.get("checkOut", {})
            room_checkout = room_checkout.replace("-","/")
            curr_room_list.append(room_checkout)

            nights = (pd.to_datetime(room_checkout) - pd.to_datetime(room_checkin)).days
            curr_room_list.append(nights)
            self.nights = nights
            
            room_guests = room.get("numberGuests", {})
            curr_room_list.append(room_guests)
            self.guests += room_guests

            # curr_room_list.append(room.get("priceRack", {}))
            # curr_room_list.append(room.get("priceNet", {}))
            price_retail = room.get("priceRetail", {})
            curr_room_list.append(f"¥{price_retail:,.0f}")

            # Add back to master dictionary          
            rooms_list_todf.append(curr_room_list)
            
            # Add to the total if multiple rooms
            # self.booking_accom_total += price_retail
   
        # set the total for the booking
        self.accom_total = self.booking_accom_total


        return rooms_list_todf
            

    def parse_service_item(self, booking, package_gs_list):
        
        """Parse each guest service booking"""



        booking_list = []

        # st.write(booking)
        gs_items = booking.get("items", {})

        # for item in gs_items:
        #     st.write(item)

        
        active = booking.get("active", {})
        # self.eId  = booking.get("eId", {}) # need to add back in for GS table
        extent = booking.get("extent", {})
        guest_service_id = booking.get("bookingId")
        service_id = booking.get("eId", {})
        
        gs_items = booking.get("items", {})
        
        for item in gs_items:
                
            provider = booking.get("serviceProvider", {}).get("serviceProviderName")
            service_name = item.get("service", {}).get("serviceName", {})
            st.write(provider, service_name)
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

            return 

    def parse_payment_info(self, pay_inv_dict):

        """Get the payment info dictionary and parse into dataframe
        
        Set the self payment_info_df
        """

        self.payment_info_df = pd.DataFrame(
                    columns = ["Invoice", "Created", "Invoiced",
                               "Due", "Paid", "Date Paid",
                               "Payment ID"])

        for invoice in pay_inv_dict:

            invoice_number = invoice.get("invoiceNumber")
            amount = invoice.get("invoiceAmount", {})

            invoice_date = invoice.get("invoiceDate", {})
            invoice_number = invoice.get("invoiceNumber", {})
            invoice_due_date = invoice.get("invoiceDueDate", {})
            
            payment_amount = invoice.get("paymentAmount", {})
            

            payment_date = invoice.get("paymentDate", {})
            if payment_date == None:
                payment_date = ""

            payment_id = invoice.get("paymentId", {})
            
            # Do a quick regex check for flywire toka
            
            pay_line = [invoice_number, invoice_date, amount, invoice_due_date,
                        payment_amount, payment_date, payment_id]

            
            self.payment_info_df.loc[len(self.payment_info_df)] = pay_line

        self.amount_invoiced = self.payment_info_df.Invoiced.sum()
        self.amount_received = self.payment_info_df.Paid.sum()

        pass


    def write_payment_df(self):

        """Writes the payment info and invoices dataframe
            
        """
        management = self.managed_by

        def highlight_unpaid(s):
            
            """ Used to colour payment df if not paid """

            # For non managed not paid
            if (s["Paid"] == 0) & \
                (self.managed_by == "Non Managed") & (s.Invoiced > 0):
                return ['background-color: #ffb09c'] * len(s)
            
            # HN Managed not paid
            elif (s["Paid"] == 0) & \
                (self.booking_source_1 != "OTA") & (s.Invoiced > 0):

                return ['background-color: #ffead5'] * len(s)    
            
            # Paid
            else:
                return ['background-color: white'] * len(s)

        st.markdown("###### Invoices and Payments")


        if self.pay_inv_dict:
            payment_info_df = self.payment_info_df
            payment_info_df["Created"] = pd.to_datetime(payment_info_df["Created"])
            payment_info_df["Due"] = pd.to_datetime(payment_info_df["Due"])

            payment_info_df["Date Paid"] = pd.to_datetime(payment_info_df["Date Paid"], errors="coerce")


            st.markdown(self.payment_info_df.style.hide(axis="index")
                        .apply(highlight_unpaid, axis=1)
                        .format({"Created": lambda x: "{}".format(x.strftime("%d %b %Y")),
                                 "Due": lambda x: "{}".format(x.strftime("%d %b %Y")),
                                 "Date Paid": lambda x: "{}".format(x.strftime("%d %b %Y") if pd.notnull(x) else ''),
                                              "Invoiced": "¥{:,.0f}",
                                              "Paid": "¥{:,.0f}",
                                })
                        .set_table_styles([{'selector': 'th', 'props': [('font-size', '10pt'),('text-align','center')]}])
                        .set_properties(**{'font-size': '8pt','text-align':'center'}).to_html(),unsafe_allow_html=True)
        
        pass

    def write_invoice_sentences(self):

        """ Write the invoices, due dates and payment link quickly and easily"""
        
        invoices_expander = st.expander("Invoices", expanded = False)

        if self.payment_link:

            for invoice in self.pay_inv_dict:
                    if invoice["paymentAmount"] == 0:

                        with invoices_expander:
                                st.markdown(
                                    f"Your payment of ¥{invoice['invoiceAmount']:,.0f} \
                                    is due by \
                                    {pd.to_datetime(invoice['invoiceDueDate']).strftime('%B %d, %Y')}.")
                                
                                st.markdown(
                                    f"[You can view your booking details and make payments here](%s)" \
                                    % self.payment_link)
                    
                            
        pass

    def write_overdue_email(self):

        """ Write the invoices, due dates and payment link quickly and easily"""
        
        invoices_expander = st.expander("Overdue Payment", expanded = False)

        # if self.payment_link:


            # for invoice in self.pay_inv_dict:
            #         if invoice["paymentAmount"] == 0:
            #             pass

            #         else:
        with invoices_expander:
                st.write(
            f"""
            Holiday Niseko Payment Required - Reservation #{self.eId}

            Hi {self.given_name},  

            I hope this email finds you well. This is a friendly reminder that 
            we have not yet received payment for your upcoming accommodation at {self.vendor}.

            Please note that your reservation will be automatically canceled in 
            48 hours if payment is not received.  
            
            You can complete your payment securely through the following link:  
            <a href='{self.payment_link}'> View invoices and make payments here </a>   

            If you have already processed the payment or wish to cancel your 
            booking, please let us know immediately.  

            Should you have any questions or concerns, our team is here to help.
            
            """,
            unsafe_allow_html = True)
                    
                            
        pass


    def write_gsg_upsell(self):

        """Write the guest service upsell spiel"""
  
        try: 
            if self.guest_email == "" or "booking.com" in self.guest_email:
                pass   

            else:
            
                gs_upsell_expander = st.expander("GS Upsell", expanded = False)
                with gs_upsell_expander:
                    st.write(f"""
                    **Enhance Your Stay with Guest Services**  
                       
                    Make your Niseko trip even better! 
                    Add convenient transfers, expert lessons, or 
                    top-quality rentals to your booking.  
                    
                    Popular Services:
                    - Private Transfers: Stress-free airport-to-accommodation transportation  
                    - Ski & Snowboard Lessons: Personalized instruction for all skill levels  
                    - Equipment Rentals: Premium skis, snowboards, and accessories  
                     
                    <a href='{self.gsg_link}'> Book Your Services Here</a>  
                     
                    Additional Information: Browse our <a href='{self.service_guide}'> Guest Services Guide</a> for services, pricing, and availability.

                    Book your extras early - popular services fill up fast!
                    """,
                          unsafe_allow_html = True)

        # st.markdown("<p class='big-font'> You can make payment and check the details of your booking [here.](%s)" % pay_str)
        except TypeError:
            return
        pass


    def write_OTA_email(self):

        """Write the OTA email after they contact us"""
  
        try: 
            if self.guest_email == "" or "booking.com" in self.guest_email:
                pass        

            else:
            
                ota_email_expander = st.expander("OTA Email", expanded = False)
                with ota_email_expander:
                    st.write(f"""
                    
                    Hi {self.given_name},  

                    Thank you for getting back to us. We have linked your email and you can now book private transfers, rentals and more!

                    <a href='{self.gsg_link}'> Book your guest services here</a>  

                    For pricing and options, please see our <a href='{self.service_guide}'> Guest Services Guide</a>.

                    View your booking details and make payments here:  
                    <a href='{self.payment_link}'> View booking details</a>  
                    
                    What's Next? Our front desk team will contact you closer to your check-in date with:

                    - Arrival instructions
                    - Online check-in link
                    - Guest registration forms  \n

                      \n\n    

                    We look forward to welcoming you to Niseko soon!
                     
                     
                    """,
                          unsafe_allow_html = True)

        except TypeError:
            return

        pass

    def write_first_ota_email(self):

        """Write the OTA email after they contact us"""
        if "booking.com" in self.guest_email:
            return

        if len(self.guest_email) > 1:
            return


        try: 
            
            
            ota_email_expander = st.expander(
                "First OTA message in app - Before guest registers email",
                expanded = False)
            
            with ota_email_expander:
                st.markdown(f"""
                
                Hi {self.given_name},  

                Thank you for your booking. We're Holiday Niseko, the local property manager for your accommodation.


                To receive your door codes and check-in details, please confirm your email address here:
                https://holidayniseko.com/email/{self.eId}

                By doing so, you'll unlock access to:  
                -- Your door codes and entry instructions  
                -- Online check-in  
                -- Our local support team  
                -- Book airport transfers, lift tickets, ski rentals, and more  


                This essential step is required for accessing your accommodation and our services.


                If you have any concerns, please contact us at res@holidayniseko.com
                    
                    
                """,
                        unsafe_allow_html = True)

        except TypeError:
            return

        pass

    def write_second_OTA_email(self):

        """Write the OTA email after they contact us"""
  
        try: 
            if self.guest_email == "" or "booking.com" in self.guest_email:
                pass        

            else:
            
                ota_email_expander = st.expander(
                    "Second OTA Email - After guest registers email",
                    expanded = False)
                
                with ota_email_expander:
                    st.write(f"""
                             
                    Access Your Holiday Niseko Booking - Reservation #{self.eId}
                    
                    Hi {self.given_name},  

                    Thank you for registering your email. Your MyBooking page is now ready.

                    Access MyBooking here: https://holidayniseko.com/my-booking/  
                    Your Reservation ID: {self.eId}


                    To log in, simply enter your email address and reservation ID shown above.


                    On MyBooking, you can: 
                    - View door codes and check-in instructions
                    - Book guest services (airport transfers, lift tickets, etc) - Popular services book quickly
                    - Complete online check-in 


                    Questions? Contact us anytime. 

                    We look forward to welcoming you to Niseko!

                    """,
                          unsafe_allow_html = True)

        except TypeError:
            return

        pass

    def write_links_box(self):

        """Writes the expandable links box to the bottom
        
        of the app
        """
        wine_dine_link = "https://www.winedineniseko.com/"

        rhythm_referral_link = "https://book.rhythmjapan.com/public/booking/order02.jsf?mv=1&vs=rhythmniseko&segment=HolidayNiseko"

        gsg_link = "https://holidayniseko.com/sites/default/files/services/2024-08/Holiday%20Niseko%20Guest%20Service%20Guide%202024_2025.pdf"

        

        with st.container():

            links_expander = st.expander(
                    "Links",
                    expanded = False)
            
            with links_expander:
                st.markdown(f"[Niseko Wine and Dine link](%s)" % wine_dine_link)
                st.markdown(f"[Rhythm referral link](%s)" % rhythm_referral_link)
                st.markdown(f"[Guest Service Guide link](%s)" % gsg_link)
                




    def write_key_booking_info(self):

        """Writes key info to left col app"""
        st.markdown(f"##### {self.vendor} #{self.eId}")
        
        st.markdown(f"###### {self.full_name}")

        st.write(f"Created - {self.created_date} ")

        # st.write(f"Managed by {self.managed_by}")
        if self.managed_by == 'Holiday Niseko':
            st.write(f"**:green[Managed by Holiday Niseko]**")

        else:
            st.write(f"**:red[Managed by {self.managed_by}]**")


        if self.active_check == True:
            st.write(f"**:green[Booking is Active]**")
        else:
            st.write(f":red[Booking is Cancelled]")

        st.markdown(f"[Open #{self.eId} in RoomBoss](%s)" % self.rboss_launch)
        
        if self.guest_phone:
            st.write(f":telephone_receiver:", self.guest_phone)

        try :
            if ("booking.com" not in self.guest_email) \
                & (self.guest_email != ""):
                st.write(f":email: {self.guest_email}")
                st.write("---")


                if (self.guest_email != None) & (self.eId != None):
                    st.markdown(f"[View booking details and make payments here](%s)" % self.payment_link)

                    st.markdown(f"[Book your guest services here](%s)" % self.gsg_link)

            else:
                st.write(f":red[Need to get guest email]")
                st.write("---")


        except TypeError:
            st.write(self.guest_email)
        


    def write_email_subject(self):

        """Subject line for the email"""

        self.email_subject_line = (f"{self.vendor} Booking #{self.eId} ~  "
                                f"{self.accom_checkin} - {self.accom_checkout} "
                                f"({self.nights} nights) {self.guests} guests")
        
        st.write(self.email_subject_line)

        return None


    def write_guest_info(self):
        
        """Guest contact details"""
        if self.guest_phone:
            st.write(f":telephone_receiver:", self.guest_phone)

        else:
            st.write("No phone number in roomboss")
        if self.guest_email:
            st.write(self.guest_email)
        else:
            st.write("No email")
        pass


    def write_room_info(self, room_list_todf):
        
        """Take room dictionary return the room 
        
        info in df format to write to streamlit
        """

        # init dataframe for accom bookings
        booking_df = pd.DataFrame(
                            room_list_todf,
                            columns=[
                                "Property", "Room", "Check-in", "Check-out",
                                "Nights", "Guests",  "Rate"])

        st.markdown(f"###### Booking #{self.eId}")

        # Here I set the accom min check in and max check out
        self.accom_checkin = booking_df["Check-in"].min()
        self.accom_checkout = booking_df["Check-out"].max()



        st.markdown(booking_df.style.hide(axis="index")\
            .set_table_styles([{'selector': 'th', 
                                'props': [('font-size',
                                            '10pt'),('text-align','center')]}])\
            .set_properties(**{'font-size': '8pt',
                               'text-align':'center'}).to_html(),
                               unsafe_allow_html=True)

   
        return None


    def attribute_booking(self):

        """Split sales channel 1 and 2 and set self.channel 1 & 2
        
        Channel 1 = OTA, Website, Agent
        
        Channel 2 = Agent Name, Airbnb, Mailchimp, Facebook etc.
        """
        
        ### I reckon find the source 2 and work backwards
        self.booking_source_1 = ""
        self.booking_source_2 = ""

        # If airbnb then check custom id matches, bk source: rb channel manager
        airbnb_prefixes = ["hmc" "HMNAYYQCQR"]  # len() of custom id string is 10

        if self.custom_id != None:

            if len(self.custom_id) > 0:
                if (self.custom_id[0] == "H") & \
                (self.booking_source.lower() == "roomboss channel manager"):
                    
                    self.booking_source_1 = "OTA"

                    self.booking_source_2 = "Airbnb"

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

        
    def highlight_unpaid(s):

        """ Used to colour payment df if not paid """

        # For non managed not paid
        if (s["Paid"] == 0) & \
            (self.managed_by == "Non Managed") & (s.Invoiced > 0):
            return ['background-color: #ffb09c'] * len(s)
        
        # HN Managed not paid
        elif (s["Paid"] == 0) & \
            (self.booking_source_1 != "OTA") & (s.Invoiced > 0):

            return ['background-color: #ffead5'] * len(s)    
        
        # Paid
        else:
            return ['background-color: white'] * len(s)
        
    def write_notes(self):

        if self.notes == "" or self.notes == None:
            return
        
        # with st.container(border = True):
        st.markdown(f"###### Notes")
        st.markdown(self.notes)
        pass