from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from inventory.models import Warehouse, Product, WarehouseStock, Customer, StockTransaction
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core import mail
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True
)

class WarehouseTests(APITestCase):
   def setUp(self):
       self.user = User.objects.create_user('testuser', 'test@test.com', 'password123')
       self.warehouse = Warehouse.objects.create(name='Test Warehouse', location='Test Location')
       self.warehouse.authorized_users.add(self.user)

   def test_warehouse_access(self):
       self.assertTrue(self.user in self.warehouse.authorized_users.all())

class StockTransactionAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'adminpass')
        self.regular_user = User.objects.create_user('user', 'user@test.com', 'userpass')

        # Get tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.user_token = str(RefreshToken.for_user(self.regular_user).access_token)

        # Create warehouses
        self.warehouse_a = Warehouse.objects.create(name='Warehouse A', location='Location A')
        self.warehouse_b = Warehouse.objects.create(name='Warehouse B', location='Location B')
        self.warehouse_a.authorized_users.add(self.regular_user)

        # Create product
        self.product = Product.objects.create(name='Test Product', sku='TEST-001', minimum_stock=10)
        
        # Create initial stock
        self.stock = WarehouseStock.objects.create(warehouse=self.warehouse_a, product=self.product, quantity=100)
        

    def test_admin_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/warehouses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both warehouses

    def test_user_limited_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/warehouses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see Warehouse A

    def test_insufficient_stock(self):
       with self.assertRaises(ValidationError):
           StockTransaction.objects.create(
               source_warehouse=self.warehouse_a,
               destination_warehouse=self.warehouse_b,
               product=self.product,
               quantity=150,  # More than available
               transaction_type='WW',
               transfer_type='TRUCK',
               performed_by=self.admin_user
           )
