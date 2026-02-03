from datetime import datetime, time, date
import os

class MarketSchedule:
    @staticmethod
    def is_market_open() -> bool:
        """
        Check if current time is within trading hours.
        Rules: Mon-Fri, 9:25-11:30, 13:00-15:00
        """
        # Debug Override
        if os.getenv("FORCE_MARKET_OPEN", "false").lower() == "true":
            return True

        now = datetime.now()
        
        # 1. Check Weekend
        if now.weekday() >= 5: # Saturday=5, Sunday=6
            return False
            
        # 2. Check Holidays (2026 Manual List)
        today_date = now.date()
        # 2026 Holidays (Estimated for SSE/SZSE)
        holidays_2026 = [
            date(2026, 1, 1),   # New Year
            # CNY 2026: Feb 17 (New Year's Day). Usually off Feb 16-22 or similar.
            # Adding common windows.
            date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18), date(2026, 2, 19), date(2026, 2, 20),
            date(2026, 4, 5),   # Qingming (Approx)
            date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3), # Labor Day
            date(2026, 6, 19),  # Duanwu (Approx)
            date(2026, 9, 24),  # Mid-Autumn
            date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7) # National Day
        ]
        
        if today_date in holidays_2026:
            return False
            
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

