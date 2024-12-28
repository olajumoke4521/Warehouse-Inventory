from celery import shared_task
from datetime import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import Product
from django.contrib.auth import get_user_model
from django.conf import settings  


@shared_task
def send_stock_status_report():
    """
    Sends the stock status report to admin users via email.
    """
    products = Product.objects.all()
    
    context = {
        'products': products,
        'report_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Render the HTML template
    html_string = render_to_string('stock_status_report.html', context)
    
    # Convert HTML to PDF
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    

    # Fetch all admin users
    User = get_user_model()
    admin_emails = User.objects.filter(role='admin').values_list('email', flat=True)

    # Send email with the PDF attachment
    email = EmailMessage(
        subject="Daily Stock Status Report",
        body="Please find attached the daily stock status report.\n\nNote: Products highlighted in light red indicate critical stock levels.",
        from_email=settings.EMAIL_HOST_USER,
        to=list(admin_emails),
    )
    
    email.attach('stock_status_report.pdf', pdf_file, 'application/pdf')
    email.send()

    return "Stock Status Report Sent"
