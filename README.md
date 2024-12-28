# Warehouse Inventory Management System

## Introduction

This Warehouse Inventory Management System is a Django-based application that allows admins to manage products, stock transactions, and receive critical stock alerts. Staff members can also add stock transactions. The system uses Celery for background task processing and WeasyPrint for generating PDF reports.

## Features

- Admins can add products, manage stock, and view reports.
- Staff can add stock transactions (in/out).
- Critical Stock Alert System to notify when stock levels fall below the minimum level.
- Background task processing with Celery.
- PDF report generation with WeasyPrint.

## Installation

### Prerequisites

- Python 3.x
- Django 3.x or higher
- Redis (for Celery)
- WeasyPrint dependencies

### Configure Database (PostgreSQL)

    ```bash
    psql -U postgres
    CREATE DATABASE inventory_db;
    ```

### Step-by-Step Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/warehouse_inventory.git
    cd warehouse_inventory
    ```

2. **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment:**

    - On Windows:

        ```cmd
        .\venv\Scripts\activate
        ```

    - On macOS/Linux:

        ```bash
        source venv/bin/activate
        ```

4. **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

5. **Install WeasyPrint dependencies:**

    - On Windows:
        - Download and install the GTK+ runtime from [GTK for Windows Runtime Environment Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
        - Add the GTK+ `bin` directory to your system PATH.

    - On macOS:

        ```bash
        brew install pango cairo gdk-pixbuf libffi
        ```

    - On Linux (Debian/Ubuntu):

        ```bash
        sudo apt-get install libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev libcairo2
        ```

6. **Apply database migrations:**

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

7. **Create a superuser:**

    ```bash
    python manage.py createsuperuser
    ```

8. **Run the development server:**

    ```bash
    python manage.py runserver
    ```

## Background Task Processing with Celery

1. **Start Redis server (if using Redis):**

    ```bash
    redis-server
    ```

2. **Start Celery worker:**

    ```bash
    celery -A warehouse_inventory worker --pool=solo --loglevel=info
    ```

3. **Start Celery beat scheduler:**

    ```bash
    celery -A warehouse_inventory beat --loglevel=info
    ```

## Usage

1. **Access the admin panel:**
    - Navigate to [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
    - Log in with the superuser credentials.

2. **Add Users and Assign Roles:**
    - Create Admin and Staff users and assign them to their respective roles on admin panel or use python shell

     ```bash
    python manage.py shell
    ```
    - from inventory.models import User
    - user = User.objects.create_user(username="testuser", password="testpass", role="staff" email="testuser@example.com")

3. **Product Management:**
    - Admins can add, update, and delete products.

4. **Stock Transactions:**
    - Admins and Staff can add stock transactions (in/out).

## API Endpoints

- POST /api/token/ - Get JWT token
- POST /api/token/refresh/ - Refresh JWT token
- /api/products/ - Product management (CRUD)
- /api/stock-transactions/ - Stock transactions

## Testing

Run tests with:
```bash
python manage.py test
```

## Scheduled Tasks

The daily stock report is generated automatically at 23:00. Make sure to configure Celery and Redis/RabbitMQ for task processing.

## Troubleshooting

If you encounter any issues, please refer to the following:

- **SMTP Connection Issues:** Ensure your SMTP server details are correct and the server is running.
- **WeasyPrint Errors:** Verify that all dependencies are correctly installed and available in your PATH.
- **Celery Connection Issues:** Ensure that the broker (Redis/RabbitMQ) is running and accessible.

---

For any questions or additional support, please feel free to contact [haonatararomi@gmail.com].
# Warehouse-Inventory
This Warehouse Inventory Management System is a Django-based application that allows admins to manage products, stock transactions, and receive critical stock alerts. Staff members can also add stock transactions. The system uses Celery for background task processing and WeasyPrint for generating PDF reports.
