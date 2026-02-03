from datetime import datetime, time, date

class MarketSchedule:
    @staticmethod
    def is_market_open() -> bool:
        """
        Check if current time is within trading hours.
        Rules: Mon-Fri, 9:25-11:30, 13:00-15:00
        """
        now = datetime.now()
        
        # 1. Check Weekend
        if now.weekday() >= 5: # Saturday=5, Sunday=6
            return False
            
        # 2. Check Holidays (TODO: Fetch from API or Config)
        # We can implement a simple list here or integration later
        # For prototype, assume strict Mon-Fri
        
        # 3. Check Time
        current_time = now.time()
        
        # Morning Session (Include Call Auction 9:25)
        morning_start = time(9, 25)
        morning_end = time(11, 30)
        
        # Afternoon Session
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end
        
        return is_morning or is_afternoon

