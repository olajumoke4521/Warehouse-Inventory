from django.contrib import admin

from .models import User, Product, StockTransaction

admin.site.register(User)
admin.site.register(Product) 
admin.site.register(StockTransaction)