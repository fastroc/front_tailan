"""
Enhanced Template Error Detection Middleware
Detects and reports silent template failures automatically
"""

import logging
from django.conf import settings
from django.http import HttpResponse
from django.template import TemplateSyntaxError, TemplateDoesNotExist

logger = logging.getLogger("template_errors")


class SilentTemplateErrorDetectionMiddleware:
    """Middleware to detect and handle silent template failures"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only check in DEBUG mode
        if not getattr(settings, "DEBUG", False):
            return response

        # Check for empty responses that might be silent template failures
        if (
            hasattr(response, "content")
            and response.status_code == 200
            and len(response.content) == 0
            and "text/html" in response.get("Content-Type", "")
        ):

            logger.error(
                f"SILENT TEMPLATE FAILURE: Empty HTML response for {request.path}"
            )

            # Return error page in DEBUG mode
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Silent Template Failure Detected</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
                    .error-container {{ background: #fff; padding: 30px; border-radius: 8px; border-left: 5px solid #dc3545; }}
                    .error-title {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                    .error-info {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                    .debug-info {{ background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                    code {{ background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-title">🚨 Silent Template Failure Detected</div>
                    
                    <div class="error-info">
                        <strong>Problem:</strong> The template rendered 0 characters (completely blank).<br>
                        <strong>URL:</strong> {request.path}<br>
                        <strong>Method:</strong> {request.method}
                    </div>
                    
                    <div class="debug-info">
                        <strong>Common Causes:</strong><br>
                        • Empty template file<br>
                        • Template syntax errors that Django ignores<br>
                        • Missing template inheritance<br>
                        • Broken template extends/includes<br>
                        • Missing template variables causing silent failure
                    </div>
                    
                    <div class="debug-info">
                        <strong>Your Template Error Detection Settings:</strong><br>
                        • Debug Mode: {getattr(settings, 'DEBUG', False)}<br>
                        • Missing Variable Indicator: {getattr(settings, 'TEMPLATES', [{}])[0].get('OPTIONS', {}).get('string_if_invalid', 'Default')}<br>
                        • Template Debug: {getattr(settings, 'TEMPLATES', [{}])[0].get('OPTIONS', {}).get('debug', False)}
                    </div>
                    
                    <p><strong>This error detection prevented a blank page!</strong></p>
                    <p><a href="javascript:history.back()">← Go Back</a></p>
                </div>
            </body>
            </html>
            """

            return HttpResponse(error_html, status=500)

        return response
