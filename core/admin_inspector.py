"""
Admin Database Structure Inspector
Creates a comprehensive view of all database models and relationships
"""
from django.contrib import admin
from django.apps import apps
from django.http import JsonResponse, HttpResponse
from django.conf import settings

class DatabaseStructureInspector:
    """Inspector for database structure visualization"""
    
    @staticmethod
    def get_all_models_info():
        """Get comprehensive information about all models"""
        models_info = {}
        
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('django.'):
                continue
                
            app_models = []
            
            for model in app_config.get_models():
                model_info = {
                    'name': model.__name__,
                    'table_name': model._meta.db_table,
                    'fields': [],
                    'relationships': [],
                    'admin_registered': admin.site.is_registered(model)
                }
                
                # Get field information
                for field in model._meta.fields:
                    field_info = {
                        'name': field.name,
                        'type': field.get_internal_type(),
                        'null': field.null,
                        'blank': field.blank,
                        'max_length': getattr(field, 'max_length', None)
                    }
                    
                    if field.get_internal_type() == 'ForeignKey':
                        field_info['related_model'] = field.related_model.__name__
                        model_info['relationships'].append({
                            'type': 'ForeignKey',
                            'field': field.name,
                            'to': field.related_model.__name__
                        })
                    
                    model_info['fields'].append(field_info)
                
                # Get reverse relationships
                for rel in model._meta.related_objects:
                    if hasattr(rel, 'related_model'):
                        model_info['relationships'].append({
                            'type': 'Reverse',
                            'from': rel.related_model.__name__,
                            'field': rel.name
                        })
                
                app_models.append(model_info)
            
            if app_models:
                models_info[app_config.name] = {
                    'app_name': app_config.name,
                    'models_count': len(app_models),
                    'models': app_models
                }
        
        return models_info

def database_structure_view(request):
    """View to display database structure"""
    if not getattr(settings, 'DEBUG', False):
        return JsonResponse({'error': 'Only available in DEBUG mode'}, status=403)
    
    inspector = DatabaseStructureInspector()
    models_info = inspector.get_all_models_info()
    
    if request.GET.get('format') == 'json':
        return JsonResponse(models_info, indent=2)
    
    context = {
        'models_info': models_info,
        'total_apps': len(models_info),
        'total_models': sum(app['models_count'] for app in models_info.values()),
        'debug_mode': settings.DEBUG
    }
    
    # Simple HTML template as string (no separate template file needed)
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Database Structure Inspector</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .app-section { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .model-box { background: #f5f5f5; margin: 10px 0; padding: 10px; border-radius: 3px; }
            .field-list { margin-left: 20px; }
            .field-item { margin: 2px 0; font-family: monospace; }
            .relationship { color: #007cba; }
            .admin-registered { color: green; font-weight: bold; }
            .admin-not-registered { color: red; }
            .stats { background: #e6f3ff; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>🏢 Database Structure Inspector</h1>
        
        <div class="stats">
            <strong>📊 Statistics:</strong>
            Total Apps: {{ total_apps }} | 
            Total Models: {{ total_models }} | 
            Debug Mode: {{ debug_mode }}
        </div>
        
        {% for app_name, app_info in models_info.items %}
        <div class="app-section">
            <h2>📦 {{ app_name }} ({{ app_info.models_count }} models)</h2>
            
            {% for model in app_info.models %}
            <div class="model-box">
                <h3>📋 {{ model.name }}</h3>
                <p><strong>Table:</strong> {{ model.table_name }}</p>
                <p><strong>Admin:</strong> 
                    {% if model.admin_registered %}
                        <span class="admin-registered">✅ Registered</span>
                    {% else %}
                        <span class="admin-not-registered">❌ Not Registered</span>
                    {% endif %}
                </p>
                
                <h4>📝 Fields ({{ model.fields|length }}):</h4>
                <div class="field-list">
                    {% for field in model.fields %}
                    <div class="field-item">
                        {{ field.name }}: {{ field.type }}
                        {% if field.max_length %}({{ field.max_length }}){% endif %}
                        {% if field.null %} [NULL]{% endif %}
                        {% if field.related_model %} → {{ field.related_model }}{% endif %}
                    </div>
                    {% endfor %}
                </div>
                
                {% if model.relationships %}
                <h4>🔗 Relationships ({{ model.relationships|length }}):</h4>
                <div class="field-list">
                    {% for rel in model.relationships %}
                    <div class="field-item relationship">
                        {{ rel.type }}: {{ rel.field }} 
                        {% if rel.to %}→ {{ rel.to }}{% endif %}
                        {% if rel.from %}← {{ rel.from }}{% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div style="margin-top: 30px; padding: 15px; background: #f0f0f0; border-radius: 5px;">
            <h3>🔧 Development Tools:</h3>
            <ul>
                <li><a href="/admin/">🏠 Django Admin Interface</a></li>
                <li><a href="?format=json">📄 JSON Export</a></li>
                <li><strong>Management Commands:</strong>
                    <ul>
                        <li><code>python manage.py setup_admin</code> - Auto-register all models</li>
                    </ul>
                </li>
            </ul>
        </div>
    </body>
    </html>
    '''
    
    from django.template import Template, Context
    template = Template(html_template)
    html_content = template.render(Context(context))
    
    return HttpResponse(html_content)
