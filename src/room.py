class Room:
    def __init__(self, room_code, room_name, beds, bed_type, max_occ, base_price, decor):
        self.room_code = room_code
        self.room_name = room_name
        self.beds = beds
        self.bed_type = bed_type
        self.max_occ = max_occ
        self.base_price = base_price
        self.decor = decor
