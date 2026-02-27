class Account:
    def __init__(self, initial_cash=1000000):
        # --- Financial Truth ---
        self.cash = initial_cash
        self.market_value = 0
        self.liabilities = 0
        self.accumulated_liabilities = 0
        self.NAV = initial_cash

        self.positions = [] # could be used to store the position with open price on first trade date


    def update_cash(self, cash):
        self.cash = cash
        return self.cash


    def update_market_value(self, market_value):
        self.market_value = market_value
        return self.market_value


    def update_positions(self, positions):
        self.positions = positions
        return self.positions


    def update_liabilities(self, liabilities):
        self.liabilities = liabilities
        return self.liabilities


    def update_accumulated_liabilities(self, liabilities):
        self.accumulated_liabilities += liabilities
        return self.accumulated_liabilities


    def reset_accumulated_liabilities(self):
        self.accumulated_liabilities = 0


    def update_NAV(self, NAV):
        self.NAV = NAV
        return self.NAV




