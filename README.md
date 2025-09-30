# Bank Reconciliation System

A Django-based bank reconciliation and loan management system.

## Features

- Bank Account Management
- Transaction Reconciliation (Simple Mode)
- Loan Management (Core, Customers, Payments, Schedules)
- Chart of Accounts
- Asset Management
- Financial Rules Engine
- Loan-GL Reconciliation Bridge

## Setup

1. Install requirements:
   ```
   pip install -r requirements.txt
   ```

2. Run migrations:
   ```
   python manage.py migrate
   ```

3. Create superuser:
   ```
   python manage.py createsuperuser
   ```

4. Run development server:
   ```
   python manage.py runserver
   ```

## Usage

Access the reconciliation interface at `/reconciliation/` for simple bank transaction matching.
