import unittest
from datetime import date, timedelta
from unittest.mock import patch

from orders.entities.product import Product
from orders.services.implementations.product_service import ProductService


class ProductServiceNotifyDelayTests(unittest.TestCase):
    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_notify_delay_updates_lead_time_and_notifies(self, mock_pr, mock_ns):
        p = Product(name="RJ45 Cable", type="NORMAL", available=0, lead_time=15)

        ProductService().notify_delay(15, p)

        self.assertEqual(0, p.available)
        self.assertEqual(15, p.lead_time)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_delay_notification.assert_called_once_with(15, "RJ45 Cable")


class ProductServiceSeasonalTests(unittest.TestCase):
    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_seasonal_lead_time_exceeds_season_marks_unavailable(self, mock_pr, mock_ns):
        p = Product(
            name="Pumpkin",
            type="SEASONAL",
            available=0,
            lead_time=60,
            season_start_date=date.today() - timedelta(days=10),
            season_end_date=date.today() + timedelta(days=5),
        )

        ProductService().handle_seasonal_product(p)

        self.assertEqual(0, p.available)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_out_of_stock_notification.assert_called_once_with("Pumpkin")
        mock_ns.send_delay_notification.assert_not_called()

    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_seasonal_before_season_start_notifies_out_of_stock(self, mock_pr, mock_ns):
        p = Product(
            name="Grapes",
            type="SEASONAL",
            available=15,
            lead_time=30,
            season_start_date=date.today() + timedelta(days=180),
            season_end_date=date.today() + timedelta(days=240),
        )

        ProductService().handle_seasonal_product(p)

        self.assertEqual(15, p.available)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_out_of_stock_notification.assert_called_once_with("Grapes")
        mock_ns.send_delay_notification.assert_not_called()

    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_seasonal_in_season_out_of_stock_notifies_delay(self, mock_pr, mock_ns):
        p = Product(
            name="Watermelon",
            type="SEASONAL",
            available=0,
            lead_time=12,
            season_start_date=date.today() - timedelta(days=2),
            season_end_date=date.today() + timedelta(days=58),
        )

        ProductService().handle_seasonal_product(p)

        self.assertEqual(0, p.available)
        self.assertEqual(12, p.lead_time)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_delay_notification.assert_called_once_with(12, "Watermelon")
        mock_ns.send_out_of_stock_notification.assert_not_called()


class ProductServiceExpirableTests(unittest.TestCase):
    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_expirable_valid_product_decrements_stock(self, mock_pr, mock_ns):
        p = Product(
            name="Butter",
            type="EXPIRABLE",
            available=5,
            lead_time=0,
            expiry_date=date.today() + timedelta(days=10),
        )

        ProductService().handle_expired_product(p)

        self.assertEqual(4, p.available)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_expiry_notification.assert_not_called()

    @patch('orders.services.implementations.product_service.ns')
    @patch('orders.services.implementations.product_service.pr')
    def test_expirable_expired_product_marks_unavailable_and_notifies(self, mock_pr, mock_ns):
        p = Product(
            name="Milk",
            type="EXPIRABLE",
            available=90,
            lead_time=6,
            expiry_date=date.today() - timedelta(days=2),
        )

        ProductService().handle_expired_product(p)

        self.assertEqual(0, p.available)
        mock_pr.save.assert_called_once_with(p)
        mock_ns.send_expiry_notification.assert_called_once_with("Milk")


if __name__ == '__main__':
    unittest.main()
