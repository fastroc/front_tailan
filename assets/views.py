from django.shortcuts import render
from django.utils import timezone


def assets_list(request):
    """Fixed assets list view"""
    tab = request.GET.get('tab', 'draft')
    
    # Sample data for showcase
    sample_assets = [
        {
            'id': 1,
            'name': 'Dell PowerEdge R740 Server',
            'description': 'Main production server',
            'number': 'FA-0001',
            'type_name': 'Computer Equipment',
            'purchase_price': 5499.00,
            'purchase_date': '2024-03-15',
            'status': 'registered',
            'status_badge': 'success',
            'book_value': 4399.20
        },
        {
            'id': 2,
            'name': 'MacBook Pro 16"',
            'description': 'Development laptop',
            'number': 'FA-0002',
            'type_name': 'Computer Equipment',
            'purchase_price': 2499.00,
            'purchase_date': '2024-06-20',
            'status': 'registered',
            'status_badge': 'success',
            'book_value': 2249.10
        },
        {
            'id': 3,
            'name': 'Office Furniture Set',
            'description': 'Desk and chairs for conference room',
            'number': 'FA-0003',
            'type_name': 'Office Equipment',
            'purchase_price': 1299.00,
            'purchase_date': '2024-01-10',
            'status': 'draft',
            'status_badge': 'warning',
            'book_value': 1299.00
        }
    ]
    
    # Filter by tab
    if tab == 'draft':
        assets = [a for a in sample_assets if a['status'] == 'draft']
    elif tab == 'registered':
        assets = [a for a in sample_assets if a['status'] == 'registered']
    elif tab == 'sold':
        assets = []  # No sold assets in sample
    else:
        assets = sample_assets
    
    context = {
        'assets': assets,
        'tab': tab,
        'counts': {
            'draft': len([a for a in sample_assets if a['status'] == 'draft']),
            'registered': len([a for a in sample_assets if a['status'] == 'registered']),
            'sold': 0
        },
        'last_depr_date': '31 Dec 2024'
    }
    
    return render(request, 'assets/list.html', context)


def new_asset(request):
    """New fixed asset form"""
    context = {
        'today': timezone.now().date(),
        'next_number': 'FA-0004',
        'asset_types': [
            {'id': 1, 'name': 'Computer Equipment'},
            {'id': 2, 'name': 'Office Equipment'},
            {'id': 3, 'name': 'Machinery'},
            {'id': 4, 'name': 'Vehicles'},
            {'id': 5, 'name': 'Buildings'},
        ],
        'dep_methods': [
            {'id': 1, 'name': 'Straight Line'},
            {'id': 2, 'name': 'Diminishing Value'},
            {'id': 3, 'name': 'Sum of Years Digits'},
        ],
        'avg_methods': [
            {'id': 1, 'name': 'Full Month'},
            {'id': 2, 'name': 'Actual Days'},
            {'id': 3, 'name': 'Half Month'},
        ]
    }
    
    return render(request, 'assets/new.html', context)


def asset_detail(request, asset_id):
    """Asset detail view - placeholder"""
    context = {
        'asset_id': asset_id,
        'message': 'Asset detail view placeholder'
    }
    return render(request, 'assets/detail.html', context)


def edit_asset(request, asset_id):
    """Edit asset view - placeholder"""
    return new_asset(request)  # Reuse new asset form for now


def asset_depreciation(request, asset_id):
    """Asset depreciation view - placeholder"""
    context = {
        'asset_id': asset_id,
        'message': 'Asset depreciation view placeholder'
    }
    return render(request, 'assets/depreciation.html', context)


def run_depreciation(request):
    """Run depreciation view - placeholder"""
    context = {
        'message': 'Run depreciation view placeholder'
    }
    return render(request, 'assets/run_depreciation.html', context)


def import_assets(request):
    """Import assets view - placeholder"""
    context = {
        'message': 'Import assets view placeholder'
    }
    return render(request, 'assets/import.html', context)


def export_assets(request):
    """Export assets view - placeholder"""
    context = {
        'message': 'Export assets view placeholder'
    }
    return render(request, 'assets/export.html', context)
