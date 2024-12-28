from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Product, User
from django.core import mail
from rest_framework.test import APIClient

class ProductTests(APITestCase):
    def setUp(self):
        # Create an admin user
        self.admin_user = User.objects.create_user('admin', 'admin@test.com', 'password')
        self.admin_user.role = 'admin'
        self.admin_user.save()
        self.client.force_authenticate(user=self.admin_user)
        
        # Create a staff user
        self.staff_user = User.objects.create_user('staffuser', 'staffuser@test.com', 'password')
        self.staff_user.role = 'staff'
        self.staff_user.save()

        # Define the URL for creating a product
        self.create_product_url = reverse('products-list')

    def test_create_product(self):
        data = {
            'name': 'Test Product',
            'description': 'Test Description',
            "price": 1200,
            "stock_quantity": 100,
            "min_stock_level": 5
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)

    def test_staff_cannot_create_product(self):
        # Authenticate as the staff user
        self.client.force_authenticate(user=self.staff_user)

        # Attempt to create a product
        data = {
            'name': 'Unauthorized Product',
            'description': 'This should not be allowed.',
            'price': 100.00,
            'stock_quantity': 10,
            'min_stock_level': 5,
        }
        response = self.client.post(self.create_product_url, data, format='json')

        # Assert that the staff user cannot create a product
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'You do not have permission to perform this action.')

    def test_get_product(self):
        product = Product.objects.create(name="Test Product", description="Description", min_stock_level=5, price="1200", stock_quantity=100)
        response = self.client.get(reverse('products-detail', args=[product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_update_product(self):
        product = Product.objects.create(name="Test Product", description="Description", min_stock_level=5, price="1200", stock_quantity=100)
        response = self.client.put(reverse('products-detail', args=[product.id]), {
            'name': 'Updated Product',
            'description': 'Updated Description',
            'price': '1200',
            'stock_quantity': 100,
            'min_stock_level': 10
        }, format='json')
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Updated Product')

    def test_delete_product(self):
        product = Product.objects.create(name="Test Product", description="Description", min_stock_level=5, price="1200", stock_quantity=100)
        response = self.client.delete(reverse('products-detail', args=[product.id]))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Product.objects.count(), 0)

class StockTransactionTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user('staff', 'staff@test.com', 'password')
        self.staff_user.role = 'staff'
        self.staff_user.save()
        self.client.force_authenticate(user=self.staff_user)
        self.product = Product.objects.create(name="Test Product", description="Description", min_stock_level=5, price="1200", stock_quantity=100)

    def test_create_stock_transaction(self):
        data = {
            'product': self.product.id,
            'transaction_type': 'out',
            'quantity': 10
        }
        response = self.client.post('/api/stock-transactions/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 90)


class CriticalStockAlertTests(TestCase):

    def setUp(self):
        # Use APIClient for testing
        self.client = APIClient()

        # Create an admin user to authenticate the requests
        self.admin_user = User.objects.create_user(
            username='admin', email='admin@test.com', password='password'
        )
        self.admin_user.role = 'admin'
        self.admin_user.save()

        # Authenticate as the admin user
        self.client.force_authenticate(user=self.admin_user)

        # Create a product with stock below the minimum level
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=10.99,
            stock_quantity=10,  
            min_stock_level=10  
        )

    def test_critical_stock_alert(self):
        # Perform a stock transaction to reduce stock below the critical level
        data = {
            'product': self.product.id,
            'transaction_type': 'out',
            'quantity': 10  
        }
        response = self.client.post(reverse('stock-transactions-list'), data, format='json')

        # Check if the stock transaction was successful
        self.assertEqual(response.status_code, 201)

        # Check if the product stock was updated correctly
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)  

        # Check that an email alert was sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify the email subject and body
        self.assertIn('Critical Stock Alert', mail.outbox[0].subject)  
        self.assertIn('Test Product', mail.outbox[0].body)  
        self.assertIn('Current Stock: 0', mail.outbox[0].body)  
        self.assertIn('Critical Level: 10', mail.outbox[0].body) 