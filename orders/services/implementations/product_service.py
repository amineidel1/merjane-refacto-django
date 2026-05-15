from datetime import date, timedelta

from ...repositories.product_repository import pr
from .notification_service import ns


class ProductService:
    def process_product(self, p):
        if p.type == "NORMAL":
            self._handle_normal(p)
        elif p.type == "SEASONAL":
            self._handle_seasonal(p)
        elif p.type == "EXPIRABLE":
            self._handle_expirable(p)

    def _handle_normal(self, p):
        if p.available > 0:
            p.available -= 1
            pr.save(p)
        elif p.lead_time > 0:
            self.notify_delay(p.lead_time, p)

    def _handle_seasonal(self, p):
        in_season = (
            date.today() > p.season_start_date
            and date.today() < p.season_end_date
            and p.available > 0
        )
        if in_season:
            p.available -= 1
            pr.save(p)
        else:
            self.handle_seasonal_product(p)

    def _handle_expirable(self, p):
        if p.available > 0 and p.expiry_date > date.today():
            p.available -= 1
            pr.save(p)
        else:
            self.handle_expired_product(p)

    def notify_delay(self, lead_time, p):
        p.lead_time = lead_time
        pr.save(p)
        ns.send_delay_notification(lead_time, p.name)

    def handle_seasonal_product(self, p):
        if date.today() + timedelta(days=p.lead_time) > p.season_end_date:
            ns.send_out_of_stock_notification(p.name)
            p.available = 0
            pr.save(p)
        elif p.season_start_date > date.today():
            ns.send_out_of_stock_notification(p.name)
            pr.save(p)
        else:
            self.notify_delay(p.lead_time, p)

    def handle_expired_product(self, p):
        if p.available > 0 and p.expiry_date > date.today():
            p.available -= 1
            pr.save(p)
        else:
            p.available = 0
            pr.save(p)
            ns.send_expiry_notification(p.name)


ps = ProductService()
