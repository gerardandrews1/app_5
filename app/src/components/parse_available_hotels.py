 
# Parse the available hotels from json 
# response to list available stays

from src.utils import get_prop_management 


class RbAvailableHotel:


    def __init__(self, dictionary_entry, management_dict):

        self.dict = dictionary_entry
        self.management_dict = management_dict
        self.managed_by = None

        hotel_name = self.dict.get("hotelName", {None})

        for key, d in management_dict.items():

            if hotel_name in d:
                self.managed_by = key

        self.avail_rooms = {}

        self.parse_avail_rooms(hotel_name)


        
        return None
    


    def parse_avail_rooms(self, hotel_name):



        self.hotel_url = self.dict.get("hotelUrl", None) 

        self.pos_managed = self.dict.get("pos_managed", None)
    
        avail_room_types = self.dict.get("availableRoomTypes", None)
        # st.write(avail_rooms_dict)
        
        for avail_room in avail_room_types: 

            room_name = avail_room.get("roomTypeName", {None})
            entry = self.parse_avail_room_types(avail_room, hotel_name, room_name)


        return pd.DataFrame(self.avail_rooms).T

    
    
    def parse_avail_room_types(self, avail_room_type, hotel_name, room_name, ):

        """
        Return the dict of the available rooms with info
        """

       
        quantity_avail = avail_room_type.get("quantityAvailable", None)

        if quantity_avail == 0:
            
            return False

        num_bedrooms = avail_room_type.get("numberBedrooms", None)

        num_bathrooms = avail_room_type.get("numberBathrooms", None)

        max_guests = avail_room_type.get("maxNumberGuests", None)


        rate_plan_dict = avail_room_type.get("ratePlan", {None})

        price, rate_plan = self.parse_rateplans(rate_plan_dict)

        
        entry = {
            
            "Price" : price,
            "Rate Plan": rate_plan,
            "Bedrooms" : num_bedrooms,
            "Bathrooms" : num_bathrooms,
            "Max Guests": max_guests,
            "Quant Avail": quantity_avail,
            "Hotel Name" : hotel_name,
            "Room Name" : room_name,
            "Managed By" :self.managed_by
        }

        # Key needs to be unique hotel, room and rate plan
        self.avail_rooms[f"{hotel_name} - {room_name} - {rate_plan}"] = entry

        return entry
    
    def parse_rateplans(self, rate_plan_dict):

        
                
        rate_name_dict = {  
                   
                    487111 : "WOW Standard",

                    493448 : "Aya Standard",

                    479226 : "H2 Standard",
                    
                    459248: "VN standard",
                    459290: "VN AP",

                    457905: "HN standard",
                    444942: "HN OTA",

                    444506: "Chat standard",
                    
                    460349 : "NISADE Standard",
                    460468 :  "NISADE EB",
                    
                    484750 : "NISADE EB & 9+ nights",

                    460411: "NISADE EB",
                    460292: "NISADE Standard",
                    
                    485536: "MnK Stand",
                    485566 : "MnK EB",

                    474983 : "Hokkaido Travel EB",
                    440650: "Hokkaido Travel stand",
                    }


        price_retail = rate_plan_dict.get("priceRetail")

        rate_plan_id = rate_plan_dict.get("ratePlanId")

        rate_name = rate_name_dict.get(rate_plan_id)



        return price_retail, rate_name
