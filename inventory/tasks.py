
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.models import User
from weasyprint import HTML
from django.conf import settings
from .models import WarehouseStock, Warehouse
from django.core.mail import EmailMessage


@shared_task
def send_stock_status_report():
    """
    Generate and send daily stock report
    """
    # Get all stocks
    stocks = WarehouseStock.objects.select_related('product', 'warehouse').all()
    
    # Prepare report data
    report_data = {
        'stocks': stocks,
        'timestamp': timezone.now(),
        'critical_count': sum(1 for stock in stocks 
                            if stock.quantity <= stock.product.minimum_stock),
        'total_count': len(stocks)
    }
    
    # Generate HTML report
    html_content = render_to_string('stock_status_report.html', report_data)
    
    # Convert to PDF
    pdf_file = HTML(string=html_content).write_pdf()
    
    # Send to admin users
    admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
    email = EmailMessage(
        subject=f'Daily Stock Report - {timezone.now().strftime("%Y-%m-%d")}',
        body="Please find attached the daily stock status report.",
        from_email=settings.EMAIL_HOST_USER,
        to=list(admin_emails),
    )
    
    email.attach('stock_status_report.pdf', pdf_file, 'application/pdf')
    email.send()

    return "Stock Status Report Sent"
