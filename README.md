# Professional Accounting System

A comprehensive Django-based accounting system with multi-tenant support, designed for professional accounting workflows.

## Features

### ✅ Core Modules
- **Multi-Company Management**: Phase 2 company setup and management
- **Chart of Accounts (COA)**: Complete account management with hierarchical structure
- **Bank Reconciliation**: CSV upload and transaction processing
- **Journal Entries**: Professional double-entry bookkeeping
- **Fixed Assets**: Asset management and depreciation tracking
- **Financial Reports**: Comprehensive reporting system

### ✅ Recent Improvements (September 2025)
- **Template Architecture**: Reliable, fast-loading templates
- **Modular Design**: Clean separation of concerns
- **Error Handling**: Graceful degradation and user-friendly messages
- **Professional UI**: Bootstrap-based responsive design
- **All Blank Page Issues Fixed**: COA, Reconciliation, and other modules working perfectly

## Technology Stack

- **Backend**: Django 5.2.6
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Python**: 3.13+

## Quick Start

### Prerequisites
- Python 3.13+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/fastroc/front_tailan.git
   cd front_tailan
   ```

2. **Create virtual environment**
   ```bash
   python -m venv django_env
   # Windows
   django_env\\Scripts\\activate
   # macOS/Linux
   source django_env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Application Structure

```
├── myproject/              # Main Django project
├── company/               # Multi-company management
├── coa/                   # Chart of Accounts
├── reconciliation/        # Bank reconciliation
├── journal/              # Journal entries
├── assets/               # Fixed assets
├── reports/              # Financial reports
├── users/                # User management
├── core/                 # Core utilities
├── api/                  # API endpoints
└── templates/            # Global templates
```

## Key URLs

- **Dashboard**: `/`
- **Company Setup**: `/company/create/`
- **Chart of Accounts**: `/coa/`
- **Create Account**: `/coa/account/create/`
- **Reconciliation**: `/reconciliation/`
- **Journal Entries**: `/journal/`
- **Fixed Assets**: `/assets/`
- **Reports**: `/reports/`

## Database Schema

### Core Models
- **Company**: Multi-tenant company management
- **Account**: Chart of accounts with hierarchical structure
- **TaxRate**: Tax rate management
- **UploadedFile**: Bank statement file management
- **BankTransaction**: Individual transaction records
- **JournalEntry**: Double-entry bookkeeping

## Development Status

### ✅ Completed Features
- [x] Multi-company Phase 2 implementation
- [x] Chart of Accounts with CRUD operations
- [x] Bank reconciliation CSV processing
- [x] Template system optimization
- [x] Professional UI/UX design
- [x] Error handling and validation
- [x] Modular architecture

### 🚧 In Progress
- [ ] Advanced reporting features
- [ ] API expansion
- [ ] Advanced search and filtering

### 📋 Planned Features
- [ ] Multi-currency support
- [ ] Advanced workflow automation
- [ ] Mobile responsive enhancements
- [ ] Integration APIs

## Development Workflow

1. Always activate the virtual environment before working
2. Create Django apps: `python manage.py startapp appname`
3. Make migrations after model changes: `python manage.py makemigrations`
4. Apply migrations: `python manage.py migrate`
5. Collect static files for production: `python manage.py collectstatic`

## Useful Commands

- `python manage.py shell` - Open Django shell
- `python manage.py dbshell` - Open database shell
- `python manage.py test` - Run tests
- `python manage.py check` - Check for issues

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

## Contact

- **Repository**: https://github.com/fastroc/front_tailan
- **Issues**: https://github.com/fastroc/front_tailan/issues

## Changelog

### v2.0.0 (September 2025)
- ✅ Complete template system overhaul
- ✅ Fixed all blank page issues (COA, Reconciliation)
- ✅ Improved Chart of Accounts functionality
- ✅ Enhanced bank reconciliation system
- ✅ Professional UI improvements
- ✅ Modular architecture implementation

### v1.0.0 (Initial Release)
- ✅ Core accounting functionality
- ✅ Multi-company support
- ✅ Basic reporting system

---

**Built with ❤️ using Django**
