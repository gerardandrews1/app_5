# Booking class to parse API response 
# and organise booking details

import csv
import datetime
import json
import os
import pandas as pd
import pyperclip

import requests
import numpy as np
import streamlit as st
from typing import Dict, Optional, Any, Union, List


from ratelimit import limits, sleep_and_retry
from dataclasses import dataclass, asdict
from urllib.parse import urlencode
# from src.utils import highlight_unpaid
from src.utils import set_management_variable
from src.utils import get_cognito_sheet_data
from src.utils import get_cognito_info
from src.utils import build_css_table
from src.utils import connect_to_gspread
from src.utils import create_cognito_link

## TODO separate streamlit UI processes to separate class
## TODO get min checkin and max check-out date for email subject 
## TODO finish  attribute booking and move higher
## TODO find a way to separate 2 x same room diff dates kevinfz example



@dataclass
class CheckInInstructions:
    def __init__(self):
        self.instructions = st.secrets.get("property_instructions", {})
        
    def write_instructions(self, vendor_name: str, room_name: Optional[str] = None) -> None:
        """Write minimal check-in instructions UI with copy button"""
        try:
            instructions = self._find_instructions(vendor_name, room_name)
            
            if not instructions:
                st.warning(f"No check-in instructions found for {vendor_name} - {room_name}")
                return
            
            plain_text = self._prepare_clipboard_text(instructions)
            sanitized_text = plain_text.split("Kind regards")[0].strip()
            
            container = st.container()
            
            with container:
                if st.button("Check-in Instructions", help="Copy check-in instructions"):
                    with st.expander("Instructions", expanded=True):
                        st.code(sanitized_text)
                        
        except Exception as e:
            st.error(f"Error with check-in instructions: {str(e)}")

    def _format_code_instructions(self, code: Union[str, List[str]]) -> str:
        """Format door code instructions, handling both string and list inputs"""
        if isinstance(code, list):
            return "\n".join(code)
        return str(code)

    def _format_address(self, address: str) -> str:
        """Format address into two lines based on common patterns"""
        if not address:
            return ""
            
        parts = address.split(", ")
        if "Hokkaido" in address:
            street_parts = []
            prefecture_parts = []
            found_hokkaido = False
            
            for part in parts:
                if "Hokkaido" in part or found_hokkaido:
                    found_hokkaido = True
                    prefecture_parts.append(part)
                else:
                    street_parts.append(part)
                    
            line1 = ", ".join(street_parts)
            line2 = ", ".join(prefecture_parts)
            
            return f"{line1}\n{line2}"
            
        if len(parts) > 1:
            return f"{', '.join(parts[:-1])}\n{parts[-1]}"
            
        return address

    def _format_access_instructions_html(self, instructions: Dict[str, Any]) -> str:
        """Format access instructions section based on available information"""
        check_in = instructions.get('checkInInstructions')
        check_out = instructions.get('checkOutInstructions')
        
        if check_in or check_out:
            instructions_html = []
            if check_in:
                instructions_html.append(
                    "<p><strong>Check-in Instructions:</strong><br>"
                    f"{check_in}</p>"
                )
            if check_out:
                instructions_html.append(
                    "<p><strong>Check-out Instructions:</strong><br>"
                    f"{check_out}</p>"
                )
            return ''.join(instructions_html)
        
        exterior_code = instructions.get('exteriorDoorCode')
        unit_code = instructions.get('doorCode')
        
        if not unit_code and not exterior_code:
            return ""
            
        if exterior_code:
            formatted_exterior = self._format_code_instructions(exterior_code)
            formatted_unit = self._format_code_instructions(unit_code)
            return (
                "<p><strong>Entry Instructions:</strong><br>"
                f"Building Entry:<br>{formatted_exterior.replace(chr(10), '<br>')}<br>"
                f"Unit Entry:<br>{formatted_unit.replace(chr(10), '<br>')}</p>"
            )
        else:
            formatted_code = self._format_code_instructions(unit_code)
            return (
                "<p><strong>Entry Instructions:</strong><br>"
                f"{formatted_code.replace(chr(10), '<br>')}</p>"
            )

    def _format_access_instructions_text(self, instructions: Dict[str, Any]) -> str:
        """Format access instructions section for plain text"""
        check_in = instructions.get('checkInInstructions')
        check_out = instructions.get('checkOutInstructions')
        
        if check_in or check_out:
            instructions_text = []
            if check_in:
                instructions_text.append(f"Check-in Instructions:\n{check_in}")
            if check_out:
                instructions_text.append(f"\nCheck-out Instructions:\n{check_out}")
            return '\n'.join(instructions_text)
        
        exterior_code = instructions.get('exteriorDoorCode')
        unit_code = instructions.get('doorCode')
        
        if not unit_code and not exterior_code:
            return ""
            
        if exterior_code:
            formatted_exterior = self._format_code_instructions(exterior_code)
            formatted_unit = self._format_code_instructions(unit_code)
            return (
                f"Entry Instructions:\n"
                f"Building Entry:\n{formatted_exterior}\n"
                f"Unit Entry:\n{formatted_unit}"
            )
        else:
            formatted_code = self._format_code_instructions(unit_code)
            return f"Entry Instructions:\n{formatted_code}"


    def _prepare_clipboard_html(self, instructions: Dict[str, Any]) -> str:
        """Format instructions as HTML for rich clipboard content"""
        access_instructions = self._format_access_instructions_html(instructions)
        formatted_address = self._format_address(instructions.get('address', ''))
        
        html_parts = [
            "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>",
            f"<p><strong>Please see the entry details for</strong> {instructions.get('name')} - {instructions.get('description', '')}</p>",
            access_instructions,
            "<p><strong>Address:</strong><br>",
            formatted_address.replace('\n', '<br>'),
            "</p>",
            f"<p><strong>Map Code:</strong><br>",
            f"{instructions.get('mapCode', '')}</p>",
            "<p><strong>Google Maps:</strong><br>",
            f"<a href='{instructions.get('googleMaps', '')}'>{instructions.get('googleMaps', '')}</a></p>",
            "<p><strong>Parking:</strong><br>",
            f"{instructions.get('parking', '')}</p>",
            "If you're arriving after 11pm this must be communicated in advance.</p>",
            "<p><strong>Please Note:</strong><br>",
            "If you have not already completed the online check-in please do so here:<br>",
            "<a href='https://holidayniseko.com/welcome'>https://holidayniseko.com/welcome</a></p>",
            "<p><strong>Contact Information:</strong><br>",
            "Email: <a href='mailto:frontdesk@holidayniseko.com'>frontdesk@holidayniseko.com</a><br>",
            "Tel: +81-136-21-6221 (08:30 - 18:30)<br>",
            "Tel: +81-80-6910-7502 (18:30 - 23:00)<br>",
            "Emergency Only: +81-80-6066-6891 (charges apply for non-emergency calls)</p>",
            "<p><strong>Check-in/Check-out Times:</strong><br>",
            "Check in is at 15:00 or after and Check out at 10:00am<br>",
            "Late check outs are not possible and charges may apply.</p>",
            "</div>"
        ]
        
        return ''.join(html_parts)

    def _prepare_clipboard_text(self, instructions: Dict[str, Any]) -> str:
        """Format instructions for plain text clipboard"""
        access_instructions = self._format_access_instructions_text(instructions)
        formatted_address = self._format_address(instructions.get('address', ''))
        
        text_parts = [
            f"Please see the entry details for {instructions.get('name')} - {instructions.get('description', '')}",
            "",
            access_instructions,
            "",
            "Address:",
            formatted_address,
            "",
            "Map Code:",
            instructions.get('mapCode', ''),
            "",
            "Google Maps:",
            instructions.get('googleMaps', ''),
            "",
            "Parking:",
            instructions.get('parking', ''),
            "",
            "If you're arriving after 11pm this must be communicated in advance.",
            "",
            "Please Note:",
            "If you have not already completed the online check-in please do so here:",
            "https://holidayniseko.com/welcome",
            "",
            "Contact Information:",
            "Email: frontdesk@holidayniseko.com",
            "Tel: +81-136-21-6221 (08:30 - 18:30)",
            "Tel: +81-80-6910-7502 (18:30 - 23:00)",
            "",
            "Emergency Only: +81-80-6066-6891 (charges apply for non-emergency calls)",
            "",
            "Check-in/Check-out Times:",
            "Check-in is at 15:00 or after and check-out at 10:00am",
            "Late check outs are not possible and charges may apply."
        ]
        
        return '\n'.join(text_parts)

    def _find_instructions(self, vendor_name: str, room_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Find instructions by matching vendor and room to TOML key"""
        try:
            vendor_key = vendor_name.upper().replace(" ", "_")
            
            if room_name and "#" in room_name:
                base_name, room_number = room_name.split("#")
                room_number = f"#{room_number.strip()}"
                base_name = base_name.strip()
                room_key = base_name.upper().replace(" ", "_") + "_" + room_number
            else:
                room_key = room_name.upper().replace(" ", "_") if room_name else ""
                
            search_key = f"{vendor_key}_{room_key}"
            
            return next((value for key, value in self.instructions.items() 
                        if search_key in key), None)
        except Exception as e:
            st.error(f"Error finding instructions: {str(e)}")
            return None


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
            self.price_retail = price_retail
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

    def write_booking_confirmation(self):
        """Write the booking confirmation with multiple rooms in a single table with columns"""
        try: 
            if self.guest_email == "" or "booking.com" in self.guest_email:
                pass        
            else:
                bk_confirmation_expander = st.expander(
                    f"Booking Confirmation #{self.eId}",
                    expanded=False)
                
                with bk_confirmation_expander:
                    # CSS styling
                    st.markdown("""
                        <style>
                        .streamlit-expanderContent {
                            white-space: nowrap !important;
                        }
                        .element-container {
                            white-space: nowrap !important;
                        }
                        .table-wrapper {
                            border: 1px solid #e0e0e0;
                            border-top: 4px solid #0C8C3C;
                            background: white;
                            padding: 0;
                            margin: 0 0 20px 0;
                            white-space: nowrap;
                            overflow-x: auto;
                            max-width: 100%;
                            display: inline-block;
                        }
                        .single-room-table {
                            width: 350px;
                        }
                        .multi-room-table {
                            width: 100%;
                        }
                        .multi-room-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 14px;
                        }
                        .header-row {
                            background: white;
                            border-bottom: 1px solid #e0e0e0;
                        }
                        .header-cell {
                            padding: 15px;
                            color: #333;
                            text-align: left;
                        }
                        .booking-id {
                            color: #000000;
                            font-size: 14px;
                            margin: 0 0 10px 0;
                        }
                        .login-button {
                            display: inline-block;
                            background-color: #FFB800;
                            color: #000000;
                            padding: 6px 12px;
                            text-decoration: none;
                            border-radius: 4px;
                            font-weight: 600;
                            font-size: 13px;
                        }
                        .property-row th {
                            font-weight: 500;
                            color: #333;
                            background: #f8f8f8;
                            padding: 10px;
                            border: 1px solid #e0e0e0;
                        }
                        .multi-room-table th {
                            width: 130px;
                            font-weight: 500;
                            color: #333;
                            background: #f8f8f8;
                            padding: 10px;
                            border: 1px solid #e0e0e0;
                        }
                        .multi-room-table td {
                            background: white;
                            padding: 10px;
                            border: 1px solid #e0e0e0;
                            text-align: center;
                        }
                        </style>
                    """, unsafe_allow_html=True)

                    # Header section
                    st.markdown(f"""
                    Booking Confirmation #{self.eId} - {self.vendor}  
                                        
                    Hi {self.given_name},

                    Thank you for choosing Holiday Niseko! We're delighted to confirm your booking with us.
                    
                    Please take a moment to review your booking confirmation below to ensure everything is correct.
                    
                    **To secure your booking a 20% non-refundable deposit is required within 3 days**  
                    """, unsafe_allow_html=True)

                    # Group rooms by booking to display them together
                    bookings_with_rooms = {}
                    
                    for booking in self.booking_dict:
                        if booking.get('bookingType') == 'ACCOMMODATION':
                            booking_id = booking.get('eId', '')
                            vendor = booking.get('hotel', {}).get('hotelName', '')
                            
                            # Create URL-encoded parameters for the my-booking link
                            from urllib.parse import urlencode
                            params = {
                                'email': self.guest_email,
                                'reservation_eid': booking_id
                            }
                            
                            # Create the URL with parameters
                            my_booking_url = f"https://holidayniseko.com/my-booking?{urlencode(params)}"
                            
                            # Extract all rooms for this booking
                            rooms = []
                            for room in booking.get('items', []):
                                rooms.append({
                                    'room_name': room.get('roomType', {}).get('roomTypeName', ''),
                                    'check_in': pd.to_datetime(room.get('checkIn', '')).strftime('%b %d, %Y'),
                                    'check_out': pd.to_datetime(room.get('checkOut', '')).strftime('%b %d, %Y'),
                                    'nights': (pd.to_datetime(room.get('checkOut', '')) - pd.to_datetime(room.get('checkIn', ''))).days,
                                    'guests': room.get('numberGuests', 0),
                                    'rate': f"¥{room.get('priceRetail', 0):,.0f}"
                                })
                            
                            bookings_with_rooms[booking_id] = {
                                'vendor': vendor,
                                'rooms': rooms,
                                'my_booking_url': my_booking_url
                            }
                    
                    # Generate tables for each booking
                    for booking_id, booking_data in bookings_with_rooms.items():
                        rooms = booking_data['rooms']
                        vendor = booking_data['vendor']
                        my_booking_url = booking_data['my_booking_url']
                        
                        if not rooms:
                            continue
                        
                        # Start table - use single-room-table class if only one room
                        table_class = "single-room-table" if len(rooms) == 1 else "multi-room-table"
                        table_html = f"""
                        <div class="table-wrapper">
                            <table class="{table_class}">
                                <tr class="header-row">
                                    <td colspan="{len(rooms) + 1}" class="header-cell" style="text-align: left; padding-left: 20px;">
                                        <div class="booking-id">Booking ID: {booking_id}</div>
                                        <a href="{my_booking_url}" class="login-button">Login to MyBooking</a>
                                    </td>
                                </tr>
                                <tr class="property-row">
                                    <th>Property</th>
                                    <th colspan="{len(rooms)}">{vendor}</th>
                                </tr>
                                <tr>
                                    <th>Room</th>
                        """
                        
                        # Add room name cells
                        for room in rooms:
                            table_html += f'<td>{room["room_name"]}</td>'
                        
                        # Continue with the rest of the rows
                        table_html += """
                                </tr>
                                <tr>
                                    <th>Check-in</th>
                        """
                        
                        for room in rooms:
                            table_html += f'<td>{room["check_in"]}</td>'
                        
                        table_html += """
                                </tr>
                                <tr>
                                    <th>Check-out</th>
                        """
                        
                        for room in rooms:
                            table_html += f'<td>{room["check_out"]}</td>'
                        
                        table_html += """
                                </tr>
                                <tr>
                                    <th>Nights</th>
                        """
                        
                        for room in rooms:
                            table_html += f'<td>{room["nights"]}</td>'
                        
                        table_html += """
                                </tr>
                                <tr>
                                    <th>Guests</th>
                        """
                        
                        for room in rooms:
                            table_html += f'<td>{room["guests"]}</td>'
                        
                        table_html += """
                                </tr>
                                <tr>
                                    <th>Rate</th>
                        """
                        
                        for room in rooms:
                            table_html += f'<td>{room["rate"]}</td>'
                        
                        # Close the table
                        table_html += """
                                </tr>
                            </table>
                        </div>
                        """
                        
                        # Output the complete table
                        st.markdown(table_html, unsafe_allow_html=True)
                    
                    # Footer section
                    st.markdown(f"""
                    **Payment Information**
                    - Initial deposit: 20% (due within 3 days)
                    - Final balance: Due 60 days before check-in  
                    
                    <a href="https://holidayniseko.evoke.jp/public/yourbooking.jsf?id={self.eId}&em={self.guest_email}">Pay securely in your local currency here</a>

                    *We've partnered with Flywire to offer payments in your local currency, reducing exchange fees while we receive payment in JPY.*

                    **Important Links**
                    - <a href="https://holidayniseko.com/terms-and-conditions"> Terms and Conditions</a>
                    - <a href="https://holidayniseko2.evoke.jp/public/booking/order02.jsf?mv=1&vs=WinterGuestServices&bookingEid={self.eId}">Book Guest Services (transfers, rentals, lessons)</a>
                    - <a href="https://holidayniseko.com/sites/default/files/services/2024-08/Holiday%20Niseko%20Guest%20Service%20Guide%202024_2025.pdf">2023/24 Guest Services Guide for reference only - to be updated for winter 2024/25</a>
                    - <a href="https://holidayniseko.com/faq">FAQ</a>
                    - <a href="https://holidayniseko.com/my-booking">Login to MyBooking to check your details anytime</a>

                    *We recommend securing travel insurance to protect your booking.*
                    """, unsafe_allow_html=True)
                        
        except Exception as e:
            st.error(f"Error in write_booking_confirmation: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

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
        """
        Display room information in a multi-column table, similar to the booking confirmation format.
        Rooms are grouped by property and displayed side by side when possible.
        """
        # Return early if no room data
        if not room_list_todf or len(room_list_todf) == 0:
            st.warning("No room information available.")
            return None
        
        st.markdown(f"###### Room Information")
        
        # First, apply CSS for the table
        st.markdown("""
            <style>
            .table-wrapper {
                border: 1px solid #e0e0e0;
                border-top: 4px solid #0C8C3C;
                background: white;
                padding: 0;
                margin: 0 0 20px 0;
                white-space: nowrap;
                overflow-x: auto;
                max-width: 100%;
                display: inline-block;
            }
            .single-room-table {
                width: 350px;
                border-collapse: collapse;
                font-size: 14px;
            }
            .multi-room-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            .header-row {
                background: white;
                border-bottom: 1px solid #e0e0e0;
            }
            .header-cell {
                padding: 15px;
                color: #333;
                text-align: left;
            }
            .booking-id {
                color: #000000;
                font-size: 14px;
                margin: 0 0 10px 0;
            }
            .property-row th {
                font-weight: 500;
                color: #333;
                background: #f8f8f8;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
            th {
                width: 130px;
                font-weight: 500;
                color: #333;
                background: #f8f8f8;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
            td {
                background: white;
                padding: 10px;
                border: 1px solid #e0e0e0;
                text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Group rooms by property
        rooms_by_property = {}
        for room in room_list_todf:
            property_name = room[0]  # Property is first item
            if property_name not in rooms_by_property:
                rooms_by_property[property_name] = []
            rooms_by_property[property_name].append(room)
        
        # Set min check-in and max check-out for email subject
        all_checkins = []
        all_checkouts = []
        
        # For each property, create a table with all its rooms
        for property_name, rooms in rooms_by_property.items():
            # Determine table class based on room count
            table_class = "single-room-table" if len(rooms) == 1 else "multi-room-table"
            
            # Start building the table
            table_html = f"""
            <div class="table-wrapper">
                <table class="{table_class}">
                    <tr class="header-row">
                        <td colspan="{len(rooms) + 1}" class="header-cell" style="text-align: left; padding-left: 20px;">
                            <div class="booking-id"><strong>Booking ID: #{self.eId}</strong></div>
                        </td>
                    </tr>
                    <tr class="property-row">
                        <th>Property</th>
                        <th colspan="{len(rooms)}">{property_name}</th>
                    </tr>
                    <tr>
                        <th>Room</th>
            """
            
            # Add room names
            for room in rooms:
                table_html += f'<td>{room[1]}</td>'  # Room name is second item
            
            # Add check-in dates
            table_html += """
                    </tr>
                    <tr>
                        <th>Check-in</th>
            """
            for room in rooms:
                checkin_raw = room[2]  # Check-in is third item
                all_checkins.append(checkin_raw)
                # Format date to Jan 02, 2025 format
                try:
                    checkin_date = pd.to_datetime(checkin_raw)
                    formatted_checkin = checkin_date.strftime('%b %d, %Y')
                except:
                    formatted_checkin = checkin_raw  # Keep original if parsing fails
                table_html += f'<td>{formatted_checkin}</td>'
            
            # Add check-out dates
            table_html += """
                    </tr>
                    <tr>
                        <th>Check-out</th>
            """
            for room in rooms:
                checkout_raw = room[3]  # Check-out is fourth item
                all_checkouts.append(checkout_raw)
                # Format date to Jan 02, 2025 format
                try:
                    checkout_date = pd.to_datetime(checkout_raw)
                    formatted_checkout = checkout_date.strftime('%b %d, %Y')
                except:
                    formatted_checkout = checkout_raw  # Keep original if parsing fails
                table_html += f'<td>{formatted_checkout}</td>'
            
            # Add nights
            table_html += """
                    </tr>
                    <tr>
                        <th>Nights</th>
            """
            for room in rooms:
                table_html += f'<td>{room[4]}</td>'  # Nights is fifth item
            
            # Add guests
            table_html += """
                    </tr>
                    <tr>
                        <th>Guests</th>
            """
            for room in rooms:
                table_html += f'<td>{room[5]}</td>'  # Guests is sixth item
            
            # Add rates
            table_html += """
                    </tr>
                    <tr>
                        <th>Rate</th>
            """
            for room in rooms:
                table_html += f'<td>{room[6]}</td>'  # Rate is seventh item
            
            # Close the table
            table_html += """
                    </tr>
                </table>
            </div>
            """
            
            # Output the table
            st.markdown(table_html, unsafe_allow_html=True)
        
        # Set min check-in and max check-out
        if all_checkins:
            self.accom_checkin = min(all_checkins)
        if all_checkouts:
            self.accom_checkout = max(all_checkouts)
        
        return None

    def write_cognito(self):

        """Queries the google sheet to check if
        
        the customer has completed cognito online
        
        check-in """

        if self.managed_by != "Holiday Niseko":
            front_desk_manual_link = "https://docs.google.com/document/d/1-R1zBxcY9sBP_ULDc7D0qaResj9OTU2s/r/edit/edit#heading=h.rus25g7i893t"
            st.markdown(f"**Don't send Holiday Niseko online check-in** [FD MANUAL](%s)" % front_desk_manual_link)
            return



        df =  get_cognito_sheet_data()
        cognito_entry = get_cognito_info(str(self.eId), df)

        # eId = cognito_entry["HolidayNisekoReservationNumber"].values[0]

        try:
            eId = cognito_entry["HolidayNisekoReservationNumber"].values[0]
        except Exception:
            eId = "-"

        try:
            phone = cognito_entry["Phone"].values[0]
        except Exception:
            phone = "-"

        try:
            arv = cognito_entry["ExpectedArrivalTimeInNiseko"].values[0] + " " \
                + cognito_entry["ArrivingInNisekoBy"].values[0]
        
        except IndexError:
            arv = "-"

        if eId == "-":
            cognito_done = "No"
            # Example usage:
            link = create_cognito_link(
                                    reservation_number = self.eId,
                                    check_in = self.accom_checkin,
                                    check_out = self.accom_checkout,
                                    accommodation = self.vendor,
                                    first_name = self.given_name,
                                    last_name = self.family_name,
                                    email = self.guest_email
                                    )

            st.write("[Online Check-in Link](%s)" % link)
        
        else:
            cognito_done = "Yes"

        
        build_css_table(eId,
                        phone,
                        arv,
                        cognito_done)
        


   
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


    def write_booking_info(self):

            st.markdown(f"""
                <style>
                .booking-header {{
                    background-color: #3d8b44;
                    color: white;
                    padding: 10px 14px;
                    border-radius: 4px 4px 0 0;
                    margin-bottom: 0;
                    width: 400px;
                }}
                .booking-badge {{
                    background-color: #FFB800;
                    color: black;
                    padding: 3px 10px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    display: inline-block;
                    margin-bottom: 6px;
                }}
                .booking-title {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 3px;
                }}
                .booking-subtitle {{
                    font-size: 12px;
                    opacity: 0.9;
                }}
                .booking-table {{
                    width: 400px;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    border: 1px solid #e5e7eb;
                }}
                .label {{
                    width: 130px;
                    background-color: #f8f9fa;
                    padding: 10px 14px;
                    border-bottom: 1px solid #2B7A33;
                    border-right: 1px solid #2B7A33;
                    font-weight: 500;
                    font-size: 13px;
                }}
                .value {{
                    padding: 10px 14px;
                    border-bottom: 1px solid #2B7A33;
                    font-size: 13px;
                }}
                .total {{
                    font-weight: bold;
                    font-size: 14px;
                }}
                </style>
                
                <div class="booking-header">
                    <div class="booking-badge">MyBooking</div>
                    <div class="booking-title">{self.vendor}</div>
                    <div class="booking-subtitle">{self.active_check}</div>
                </div>
                <table class="booking-table">
                    <tr>
                        <td class="label">Check-in</td>
                        <td class="value">{self.accom_checkin}</td>
                    </tr>
                    <tr>
                        <td class="label">Check-out</td>
                        <td class="value">{self.accom_checkout}</td>
                    </tr>
                    <tr>
                        <td class="label">Length of Stay</td>
                        <td class="value">{self.nights} nights</td>
                    </tr>
                    <tr>
                        <td class="label">Guests</td>
                        <td class="value">{self.guests}</td>
                    </tr>
                    <tr>
                        <td class="label">Total Price</td>
                        <td class="value total">{self.accom_total}</td>
                    </tr>
                </table>
            """, unsafe_allow_html=True)


    def write_days_to_checkin(self):
        date_checkin = pd.to_datetime(self.accom_checkin).normalize()  # Set to midnight
        date_checkout = pd.to_datetime(self.accom_checkout).normalize()
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # Set to midnight
        
        days_to_checkin = (date_checkin - today).days
        days_after_checkout = (date_checkout - today).days

        # Check-in scenarios
        if days_to_checkin > 0:
            st.write(f"{days_to_checkin} days until check-in")
        elif days_to_checkin == 0:
            st.write("Check-in is today")
        else:
            # Already checked in, handle check-out scenarios
            if days_after_checkout < 0:
                st.write(f"Checked out {abs(days_after_checkout)} days ago")
            elif days_after_checkout == 0:
                st.write("Check-out is today!")
            else:
                st.write(f"Currently staying: {days_after_checkout+1} days until check-out")


    def write_checkin_instructions(self):
        """Write check-in instructions for the accommodation"""
        try:
            if not hasattr(self, '_checkin_instructions'):
                self._checkin_instructions = CheckInInstructions()
            
            if not hasattr(self, 'vendor'):
                st.warning("Unable to find property information for check-in instructions")
                return
            
            # Get the first room's name
            room_name = None
            if hasattr(self, 'rooms_booked') and self.rooms_booked:
                first_room = self.rooms_booked[0]
                if isinstance(first_room, dict) and 'roomType' in first_room:
                    room_type = first_room.get('roomType', {})
                    if isinstance(room_type, dict):
                        room_name = room_type.get('roomTypeName')
            
            # Debug information
            # st.write("DEBUG: Booking Information")
            # st.write(f"Vendor: {self.vendor}")
            # st.write(f"Room Name: {room_name}")
            
            self._checkin_instructions.write_instructions(self.vendor, room_name)
            
        except Exception as e:
            st.error(f"Error in write_checkin_instructions: {str(e)}")
            import traceback
            st.write("Full error traceback:")
            st.code(traceback.format_exc())

        