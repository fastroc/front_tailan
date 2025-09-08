from django.shortcuts import render
from django.http import JsonResponse

def company_list(request):
    """
    DEMO VIEW - Show company dashboard template for frontend approval
    """
    # Mock data for template showcase
    mock_companies = [
        {
            'id': '12345678-1234-5678-9012-123456789abc',
            'name': 'Acme Corporation',
            'logo': None,
            'business_type': 'Corporation',
            'industry': 'Technology',
            'role': 'owner',
            'is_active': True,
            'stats': {
                'transactions': 1234,
                'balance': 45678,
                'pending': 5,
                'team_members': 8
            }
        },
        {
            'id': '87654321-4321-8765-2109-abcdef123456', 
            'name': 'Green Solutions Ltd',
            'logo': None,
            'business_type': 'Limited Company',
            'industry': 'Environmental',
            'role': 'admin',
            'is_active': False,
            'stats': {
                'transactions': 856,
                'balance': 32100,
                'pending': 2,
                'team_members': 3
            }
        }
    ]
    
    context = {
        'companies': mock_companies,
        'active_company': mock_companies[0] if mock_companies else None,
        'total_companies': len(mock_companies),
        'can_create': True,
    }
    return render(request, 'company/company_list.html', context)


def company_create(request):
    """
    DEMO VIEW - Show company creation wizard for frontend approval
    """
    # Mock form for template showcase
    mock_form = type('MockForm', (), {
        'name': type('Field', (), {'id_for_label': 'id_name', 'label': 'Company Name', 'help_text': 'Enter your company name'})(),
        'legal_name': type('Field', (), {'id_for_label': 'id_legal_name', 'label': 'Legal Name', 'help_text': 'Official registered name'})(),
        'business_type': type('Field', (), {'id_for_label': 'id_business_type', 'label': 'Business Type'})(),
        'industry': type('Field', (), {'id_for_label': 'id_industry', 'label': 'Industry'})(),
        'logo': type('Field', (), {'id_for_label': 'id_logo', 'label': 'Company Logo', 'help_text': 'Upload your company logo'})(),
        'email': type('Field', (), {'id_for_label': 'id_email', 'label': 'Email Address'})(),
        'phone': type('Field', (), {'id_for_label': 'id_phone', 'label': 'Phone Number'})(),
        'website': type('Field', (), {'id_for_label': 'id_website', 'label': 'Website'})(),
        'address_line_1': type('Field', (), {'id_for_label': 'id_address_line_1', 'label': 'Address Line 1'})(),
        'address_line_2': type('Field', (), {'id_for_label': 'id_address_line_2', 'label': 'Address Line 2'})(),
        'city': type('Field', (), {'id_for_label': 'id_city', 'label': 'City'})(),
        'state_province': type('Field', (), {'id_for_label': 'id_state_province', 'label': 'State/Province'})(),
        'postal_code': type('Field', (), {'id_for_label': 'id_postal_code', 'label': 'Postal Code'})(),
        'country': type('Field', (), {'id_for_label': 'id_country', 'label': 'Country'})(),
        'base_currency': type('Field', (), {'id_for_label': 'id_base_currency', 'label': 'Base Currency', 'help_text': 'Primary currency for accounting'})(),
        'financial_year_start': type('Field', (), {'id_for_label': 'id_financial_year_start', 'label': 'Financial Year Start', 'help_text': 'When does your financial year start?'})(),
        'registration_number': type('Field', (), {'id_for_label': 'id_registration_number', 'label': 'Registration Number'})(),
        'tax_id': type('Field', (), {'id_for_label': 'id_tax_id', 'label': 'Tax ID'})(),
        'errors': {}
    })()
    
    context = {
        'form': mock_form,
    }
    return render(request, 'company/company_create.html', context)


def company_detail(request, company_id):
    """
    DEMO VIEW - Show company detail page for frontend approval
    """
    mock_company = {
        'id': company_id,  # Use the UUID from URL
        'name': 'Acme Corporation',
        'legal_name': 'Acme Corporation Ltd.',
        'logo': None,
        'business_type': 'corporation',
        'industry': 'technology', 
        'email': 'info@acme.com',
        'phone': '+1-555-0123',
        'website': 'https://acme.com',
        'address_line_1': '123 Business Street',
        'address_line_2': 'Suite 100',
        'city': 'New York',
        'state_province': 'NY',
        'postal_code': '10001',
        'country': 'United States',
        'base_currency': 'USD',
        'financial_year_start': '2025-01-01',
        'financial_year_end': '2025-12-31',
        'registration_number': 'REG123456',
        'tax_id': 'TAX789012',
        'created_at': '2025-01-15',
        'get_business_type_display': lambda: 'Corporation',
        'get_industry_display': lambda: 'Technology',
    }
    
    mock_users = [
        {
            'user': type('User', (), {
                'get_full_name': lambda: 'John Smith',
                'username': 'john.smith',
                'email': 'john@acme.com'
            })(),
            'get_role_display': lambda: 'Owner',
            'is_active': True,
            'created_at': '2025-01-15'
        },
        {
            'user': type('User', (), {
                'get_full_name': lambda: 'Jane Doe', 
                'username': 'jane.doe',
                'email': 'jane@acme.com'
            })(),
            'get_role_display': lambda: 'Admin',
            'is_active': True,
            'created_at': '2025-02-01'
        }
    ]
    
    context = {
        'company': type('Company', (), mock_company)(),
        'user_role': 'owner',
        'active_company': type('Company', (), mock_company)(),
        'company_users': mock_users,
        'can_edit': True,
    }
    return render(request, 'company/company_detail.html', context)


def company_settings(request, company_id):
    """
    DEMO VIEW - Show company settings page for frontend approval  
    """
    mock_company = {
        'id': company_id,  # Use the UUID from URL
        'name': 'Acme Corporation',
        'logo': None,
    }
    
    # Same mock form as company_create
    mock_form = type('MockForm', (), {
        'name': type('Field', (), {'id_for_label': 'id_name', 'label': 'Company Name', 'help_text': 'Enter your company name'})(),
        'legal_name': type('Field', (), {'id_for_label': 'id_legal_name', 'label': 'Legal Name', 'help_text': 'Official registered name'})(),
        'business_type': type('Field', (), {'id_for_label': 'id_business_type', 'label': 'Business Type'})(),
        'industry': type('Field', (), {'id_for_label': 'id_industry', 'label': 'Industry'})(),
        'logo': type('Field', (), {'id_for_label': 'id_logo', 'label': 'Company Logo', 'help_text': 'Upload your company logo'})(),
        'email': type('Field', (), {'id_for_label': 'id_email', 'label': 'Email Address'})(),
        'phone': type('Field', (), {'id_for_label': 'id_phone', 'label': 'Phone Number'})(),
        'website': type('Field', (), {'id_for_label': 'id_website', 'label': 'Website'})(),
        'address_line_1': type('Field', (), {'id_for_label': 'id_address_line_1', 'label': 'Address Line 1'})(),
        'address_line_2': type('Field', (), {'id_for_label': 'id_address_line_2', 'label': 'Address Line 2'})(),
        'city': type('Field', (), {'id_for_label': 'id_city', 'label': 'City'})(),
        'state_province': type('Field', (), {'id_for_label': 'id_state_province', 'label': 'State/Province'})(),
        'postal_code': type('Field', (), {'id_for_label': 'id_postal_code', 'label': 'Postal Code'})(),
        'country': type('Field', (), {'id_for_label': 'id_country', 'label': 'Country'})(),
        'base_currency': type('Field', (), {'id_for_label': 'id_base_currency', 'label': 'Base Currency', 'help_text': 'Primary currency for accounting'})(),
        'financial_year_start': type('Field', (), {'id_for_label': 'id_financial_year_start', 'label': 'Financial Year Start', 'help_text': 'When does your financial year start?'})(),
        'registration_number': type('Field', (), {'id_for_label': 'id_registration_number', 'label': 'Registration Number'})(),
        'tax_id': type('Field', (), {'id_for_label': 'id_tax_id', 'label': 'Tax ID'})(),
        'errors': {}
    })()
    
    mock_users = [
        {
            'user': type('User', (), {
                'get_full_name': lambda: 'John Smith',
                'username': 'john.smith', 
                'email': 'john@acme.com',
                'first_name': 'John'
            })(),
            'get_role_display': lambda: 'Owner',
            'is_active': True,
            'created_at': '2025-01-15'
        }
    ]
    
    context = {
        'company': type('Company', (), mock_company)(),
        'form': mock_form,
        'company_users': mock_users,
    }
    return render(request, 'company/company_settings.html', context)


def company_switch(request, company_id):
    """
    DEMO VIEW - Mock company switching (just returns success)
    """
    return JsonResponse({'success': True, 'message': 'Company switched successfully'})
