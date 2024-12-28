from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Product, StockTransaction
from .serializers import ProductSerializer, StockTransactionSerializer
from django.core.mail import send_mail
from .permissions import IsAdmin, IsStaffOrAdmin
from rest_framework.exceptions import ValidationError
from django.conf import settings  
from inventory.models import User
from smtplib import SMTPException

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAdmin]

    def perform_create(self, serializer):
        transaction_type = serializer.validated_data['transaction_type']
        quantity = serializer.validated_data['quantity']
        product = serializer.validated_data['product']

        # Update the product's stock_quantity based on transaction type
        if transaction_type == 'in':
            product.stock_quantity += quantity
        elif transaction_type == 'out':
            if product.stock_quantity < quantity:
                raise ValidationError("Insufficient stock for this transaction.")
            product.stock_quantity -= quantity

        # Save the updated product
        product.save()

        # Trigger a critical stock alert if the stock is less than or equal to the critical level
        if product.stock_quantity < product.min_stock_level:
            self.trigger_critical_stock_alert(product)

        # Save the transaction with the user who performed it
        serializer.save(performed_by=self.request.user)

    def trigger_critical_stock_alert(self, product):
        try:
            """
            Send an email alert to admins when the stock of a product falls below its critical level.
            """
            subject = f"Critical Stock Alert for {product.name}"
            message = (
                f"The stock for {product.name} has reached a critical level.\n\n"
                f"Current Stock: {product.stock_quantity}\n"
                f"Critical Level: {product.min_stock_level}\n\n"
                "Please restock the item immediately."
            )
            admin_emails = [admin.email for admin in User.objects.filter(is_active=True, role='admin')]
            recipient_list= admin_emails
            from_email = settings.EMAIL_HOST_USER 
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except SMTPException as e:
            print(f"Failed to send email: {e}")

