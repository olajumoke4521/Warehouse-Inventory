# inventory/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Warehouse, Customer, Product, WarehouseStock, StockTransaction

class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'get_authorized_users', 'created_at')
    search_fields = ('name', 'location')
    filter_horizontal = ('authorized_users',)
    list_filter = ('location',)

    def get_authorized_users(self, obj):
        return ", ".join([user.username for user in obj.authorized_users.all()])
    get_authorized_users.short_description = 'Authorized Users'

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('customer_type', 'is_active')
    search_fields = ('name', 'contact_person', 'email')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'minimum_stock', 'created_at')
    search_fields = ('name', 'sku')
    list_filter = ('created_at',)

class WarehouseStockAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'product', 'quantity', 'updated_at')
    list_filter = ('warehouse', 'product')
    search_fields = ('warehouse__name', 'product__name')

class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('get_transaction_details', 'product', 'quantity', 'transaction_type', 
                   'transfer_type', 'performed_by', 'created_at')
    list_filter = ('transaction_type', 'transfer_type', 'created_at')
    search_fields = ('product__name', 'source_warehouse__name', 
                    'destination_warehouse__name', 'customer__name')
    readonly_fields = ('created_at', 'updated_at')

    def get_transaction_details(self, obj):
        if obj.transaction_type == 'WW':
            return f"{obj.source_warehouse} → {obj.destination_warehouse}"
        elif obj.transaction_type == 'WC':
            return f"{obj.source_warehouse} → {obj.customer}"
        else:  # CW
            return f"{obj.customer} → {obj.destination_warehouse}"
    get_transaction_details.short_description = 'Transaction'

class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('get_warehouses',)
    
    def get_warehouses(self, obj):
        return ", ".join([warehouse.name for warehouse in obj.authorized_warehouses.all()])
    get_warehouses.short_description = 'Assigned Warehouses'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register all models
admin.site.register(Warehouse, WarehouseAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(WarehouseStock, WarehouseStockAdmin)
admin.site.register(StockTransaction, StockTransactionAdmin)