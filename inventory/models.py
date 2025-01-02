from django.db import models

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    authorized_users = models.ManyToManyField(
        User, 
        related_name='authorized_warehouses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    customer_type = models.CharField(max_length=50, choices=[
        ('BUSINESS', 'Business'),
        ('INDIVIDUAL', 'Individual')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
# Product Model
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    sku = models.CharField(max_length=50, unique=True)
    minimum_stock = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['warehouse', 'product']

    def __str__(self):
        return f"{self.product.name} at {self.warehouse.name}: {self.quantity}"

# Stock Transaction Model
class StockTransaction(models.Model):
    TRANSFER_TYPES = [
        ('SHIP', 'Ship'),
        ('PLANE', 'Plane'),
        ('TRUCK', 'Truck'),
    ]
    TRANSACTION_TYPES = [
        ('WW', 'Warehouse to Warehouse'),
        ('WC', 'Warehouse to Customer'),
        ('CW', 'Customer to Warehouse'),
    ]

    source_warehouse = models.ForeignKey(Warehouse, related_name='source_transactions', on_delete=models.CASCADE, null=True, blank=True)
    destination_warehouse = models.ForeignKey(Warehouse, related_name='destination_transactions', on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    transfer_type = models.CharField(max_length=50, choices=TRANSFER_TYPES, null=True, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.transaction_type == 'WW':
            if not self.source_warehouse or not self.destination_warehouse:
                raise ValidationError(
                    'Warehouse to Warehouse transfer requires both source and destination warehouses'
                )
            if self.customer:
                raise ValidationError('Customer should not be set for Warehouse to Warehouse transfer')
                
        elif self.transaction_type == 'WC':
            if not self.source_warehouse or not self.customer:
                raise ValidationError(
                    'Warehouse to Customer transfer requires source warehouse and customer'
                )
            if self.destination_warehouse:
                raise ValidationError(
                    'Destination warehouse should not be set for Warehouse to Customer transfer'
                )
                
        elif self.transaction_type == 'CW':
            if not self.destination_warehouse or not self.customer:
                raise ValidationError(
                    'Customer to Warehouse transfer requires destination warehouse and customer'
                )
            if self.source_warehouse:
                raise ValidationError(
                    'Source warehouse should not be set for Customer to Warehouse transfer'
                )

        # Check if source warehouse has enough stock
        if self.source_warehouse:
            try:
                stock = WarehouseStock.objects.get(
                    warehouse=self.source_warehouse,
                    product=self.product
                )
                if stock.quantity < self.quantity:
                    raise ValidationError(
                        f'Insufficient stock in {self.source_warehouse.name}. '
                        f'Available: {stock.quantity}, Requested: {self.quantity}'
                    )
            except WarehouseStock.DoesNotExist:
                raise ValidationError(
                    f'No stock record found for {self.product.name} '
                    f'in {self.source_warehouse.name}'
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Update warehouse stock levels
        if self.transaction_type == 'WW':
            # Deduct from source warehouse
            source_stock = WarehouseStock.objects.get(
                warehouse=self.source_warehouse,
                product=self.product
            )
            source_stock.quantity -= self.quantity
            source_stock.save()
            
            # Add to destination warehouse
            dest_stock, created = WarehouseStock.objects.get_or_create(
                warehouse=self.destination_warehouse,
                product=self.product,
                defaults={'quantity': 0}
            )
            dest_stock.quantity += self.quantity
            dest_stock.save()

            # Check critical levels for both warehouses
            self._check_critical_stock(source_stock)
            self._check_critical_stock(dest_stock)
            
        elif self.transaction_type == 'WC':
            source_stock = WarehouseStock.objects.get(
                warehouse=self.source_warehouse,
                product=self.product
            )
            source_stock.quantity -= self.quantity
            source_stock.save()

            # Check critical level
            self._check_critical_stock(source_stock)
            
        elif self.transaction_type == 'CW':
            dest_stock, created = WarehouseStock.objects.get_or_create(
                warehouse=self.destination_warehouse,
                product=self.product,
                defaults={'quantity': 0}
            )
            dest_stock.quantity += self.quantity
            dest_stock.save()

            # Check critical level
            self._check_critical_stock(dest_stock)

    def _check_critical_stock(self, stock):
        """Check if stock is at critical level and send alert if necessary"""
        if stock.quantity <= stock.product.minimum_stock:
            # Get admin users and warehouse authorized users
            admin_users = User.objects.filter(is_staff=True)
            warehouse_users = stock.warehouse.authorized_users.all()
            all_users = set(list(admin_users) + list(warehouse_users))

            # Create email message
            message = f"""
Critical Stock Alert!

Warehouse: {stock.warehouse.name}
Product: {stock.product.name}
Current Stock: {stock.quantity}
Minimum Stock Level: {stock.product.minimum_stock}
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated notification. Please take necessary action to replenish the stock.
"""
            # Send email
            send_mail(
                subject=f'Critical Stock Alert - {stock.warehouse.name} - {stock.product.name}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email for user in all_users if user.email],
            )
