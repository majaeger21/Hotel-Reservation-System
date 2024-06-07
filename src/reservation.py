class Reservation:
    def __init__(self, code, room, check_in, checkout, rate, last_name, first_name, adults, kids):
        self.code = code
        self.room = room
        self.check_in = check_in
        self.checkout = checkout
        self.rate = rate
        self.last_name = last_name
        self.first_name = first_name
        self.adults = adults
        self.kids = kids
