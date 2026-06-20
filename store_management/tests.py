from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Product, StoreTransaction


class StockReleaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        self.product = Product.objects.create(name='Test Product')

    def test_stock_adds_to_existing_transaction(self):
        """Subtraction/stock should update existing transaction on same product."""
        StoreTransaction.objects.create(
            product=self.product,
            date='2026-05-01',
            quantity_stocked=Decimal('100'),
            unit_price=Decimal('10'),
            purchase_status='CASH',
        )

        response = self.client.post(
            reverse('store_management:stock_item'),
            {'product': self.product.id, 'quantity_stocked': '50'},
        )

        self.assertTrue(response.json()['success'])
        txn = StoreTransaction.objects.get(product=self.product)
        self.assertEqual(txn.quantity_stocked, Decimal('150'))

    def test_release_adds_to_quantity_released(self):
        """Deduction/release should update existing transaction on same product."""
        StoreTransaction.objects.create(
            product=self.product,
            date='2026-05-01',
            quantity_stocked=Decimal('100'),
            quantity_released=Decimal('10'),
            unit_price=Decimal('10'),
            purchase_status='CASH',
        )

        response = self.client.post(
            reverse('store_management:release_item'),
            {'product': self.product.id, 'quantity_released': '20'},
        )

        self.assertTrue(response.json()['success'])
        txn = StoreTransaction.objects.get(product=self.product)
        self.assertEqual(txn.quantity_released, Decimal('30'))

    def test_release_fails_without_stocked_inventory(self):
        """Release should fail if no stocked inventory exists."""
        response = self.client.post(
            reverse('store_management:release_item'),
            {'product': self.product.id, 'quantity_released': '10'},
        )

        self.assertFalse(response.json()['success'])
