from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from orders.entities.order import Order
from orders.entities.product import Product


class ProcessOrderNormalProductTests(TestCase):
    def _post_order(self, products):
        for p in products:
            p.save()
        order = Order.objects.create()
        order.products.set(products)
        url = reverse('process_order', args=[order.id])
        return self.client.post(url, content_type='application/json'), order

    def test_normal_in_stock_decrements_available(self):
        product = Product(
            name="USB Cable", type="NORMAL", available=15, lead_time=30,
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(14, product.available)

    @patch('orders.services.implementations.product_service.ns')
    def test_normal_out_of_stock_notifies_delay(self, mock_ns):
        product = Product(
            name="RJ45 Cable", type="NORMAL", available=0, lead_time=15,
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(0, product.available)
        mock_ns.send_delay_notification.assert_called_once_with(15, "RJ45 Cable")

    def test_normal_out_of_stock_zero_lead_time_does_nothing(self):
        product = Product(
            name="USB Dongle", type="NORMAL", available=0, lead_time=0,
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(0, product.available)


class ProcessOrderExpirableProductTests(TestCase):
    def _post_order(self, products):
        for p in products:
            p.save()
        order = Order.objects.create()
        order.products.set(products)
        url = reverse('process_order', args=[order.id])
        return self.client.post(url, content_type='application/json')

    def test_expirable_valid_decrements_available(self):
        product = Product(
            name="Butter",
            type="EXPIRABLE",
            available=15,
            lead_time=30,
            expiry_date=date.today() + timedelta(days=26),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(14, product.available)

    @patch('orders.services.implementations.product_service.ns')
    def test_expirable_expired_sets_available_to_zero(self, mock_ns):
        product = Product(
            name="Milk",
            type="EXPIRABLE",
            available=90,
            lead_time=6,
            expiry_date=date.today() - timedelta(days=2),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(0, product.available)
        mock_ns.send_expiry_notification.assert_called_once_with("Milk")


class ProcessOrderSeasonalProductTests(TestCase):
    def _post_order(self, products):
        for p in products:
            p.save()
        order = Order.objects.create()
        order.products.set(products)
        url = reverse('process_order', args=[order.id])
        return self.client.post(url, content_type='application/json')

    def test_seasonal_in_season_with_stock_decrements_available(self):
        product = Product(
            name="Watermelon",
            type="SEASONAL",
            available=15,
            lead_time=30,
            season_start_date=date.today() - timedelta(days=2),
            season_end_date=date.today() + timedelta(days=58),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(14, product.available)

    @patch('orders.services.implementations.product_service.ns')
    def test_seasonal_in_season_out_of_stock_notifies_delay(self, mock_ns):
        product = Product(
            name="Watermelon",
            type="SEASONAL",
            available=0,
            lead_time=12,
            season_start_date=date.today() - timedelta(days=2),
            season_end_date=date.today() + timedelta(days=58),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(0, product.available)
        mock_ns.send_delay_notification.assert_called_once_with(12, "Watermelon")
        mock_ns.send_out_of_stock_notification.assert_not_called()

    @patch('orders.services.implementations.product_service.ns')
    def test_seasonal_before_season_notifies_out_of_stock(self, mock_ns):
        product = Product(
            name="Grapes",
            type="SEASONAL",
            available=15,
            lead_time=30,
            season_start_date=date.today() + timedelta(days=180),
            season_end_date=date.today() + timedelta(days=240),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(15, product.available)
        mock_ns.send_out_of_stock_notification.assert_called_once_with("Grapes")

    @patch('orders.services.implementations.product_service.ns')
    def test_seasonal_lead_time_exceeds_season_marks_unavailable(self, mock_ns):
        product = Product(
            name="Pumpkin",
            type="SEASONAL",
            available=0,
            lead_time=60,
            season_start_date=date.today() - timedelta(days=10),
            season_end_date=date.today() + timedelta(days=5),
        )
        self._post_order([product])
        product.refresh_from_db()
        self.assertEqual(0, product.available)
        mock_ns.send_out_of_stock_notification.assert_called_once_with("Pumpkin")


class ProcessOrderFullScenarioTests(TestCase):
    @patch('orders.my_views.ps')
    def test_process_order_returns_200_and_order_id(self, mock_ps):
        products = [
            Product(available=15, lead_time=30, type="NORMAL", name="USB Cable"),
            Product(available=10, lead_time=0, type="NORMAL", name="USB Dongle"),
            Product(
                available=15, lead_time=30, type="EXPIRABLE", name="Butter",
                expiry_date=date.today() + timedelta(days=26),
            ),
            Product(
                available=90, lead_time=6, type="EXPIRABLE", name="Milk",
                expiry_date=date.today() - timedelta(days=2),
            ),
            Product(
                available=15, lead_time=30, type="SEASONAL", name="Watermelon",
                season_start_date=date.today() - timedelta(days=2),
                season_end_date=date.today() + timedelta(days=58),
            ),
            Product(
                available=15, lead_time=30, type="SEASONAL", name="Grapes",
                season_start_date=date.today() + timedelta(days=180),
                season_end_date=date.today() + timedelta(days=240),
            ),
        ]
        for p in products:
            p.save()
        order = Order.objects.create()
        order.products.set(products)

        url = reverse('process_order', args=[order.id])
        response = self.client.post(url, content_type='application/json')

        self.assertEqual(200, response.status_code)
        self.assertEqual({'id': order.id}, response.json())

    def test_process_order_full_scenario_updates_stock(self):
        products = [
            Product(available=15, lead_time=30, type="NORMAL", name="USB Cable"),
            Product(available=10, lead_time=0, type="NORMAL", name="USB Dongle"),
            Product(
                available=15, lead_time=30, type="EXPIRABLE", name="Butter",
                expiry_date=date.today() + timedelta(days=26),
            ),
            Product(
                available=90, lead_time=6, type="EXPIRABLE", name="Milk",
                expiry_date=date.today() - timedelta(days=2),
            ),
            Product(
                available=15, lead_time=30, type="SEASONAL", name="Watermelon",
                season_start_date=date.today() - timedelta(days=2),
                season_end_date=date.today() + timedelta(days=58),
            ),
            Product(
                available=15, lead_time=30, type="SEASONAL", name="Grapes",
                season_start_date=date.today() + timedelta(days=180),
                season_end_date=date.today() + timedelta(days=240),
            ),
        ]
        for p in products:
            p.save()
        order = Order.objects.create()
        order.products.set(products)

        url = reverse('process_order', args=[order.id])
        response = self.client.post(url, content_type='application/json')

        self.assertEqual(200, response.status_code)
        expected = {
            "USB Cable": 14,
            "USB Dongle": 9,
            "Butter": 14,
            "Milk": 0,
            "Watermelon": 14,
            "Grapes": 15,
        }
        for p in products:
            p.refresh_from_db()
            self.assertEqual(expected[p.name], p.available, p.name)
