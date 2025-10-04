"""
Analytics Dashboard Views
Displays AI performance metrics, time savings, and system health
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import ReconciliationMetrics, UserPerformance, PatternAnalytics, SystemHealth
from smart_learning.models import MatchPattern, TransactionMatchHistory, MatchFeedback
from company.models import Company, UserCompanyAccess


def get_user_active_company(request):
    """Get the user's active company using the same logic as CompanyContextMixin."""
    user = request.user
    if not user or not user.is_authenticated:
        return None
    
    # Try session first
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            company = Company.objects.get(
                id=company_id,
                user_access__user=user,
                is_active=True
            )
            return company
        except Company.DoesNotExist:
            pass
    
    # Fall back to user preferences
    try:
        preferences = user.company_preference
        if preferences.active_company and preferences.active_company.is_active:
            if UserCompanyAccess.objects.filter(
                user=user,
                company=preferences.active_company
            ).exists():
                request.session['active_company_id'] = preferences.active_company.id
                return preferences.active_company
    except:
        pass
    
    # Return first available company
    try:
        access = UserCompanyAccess.objects.filter(
            user=user,
            company__is_active=True
        ).select_related('company').first()
        if access:
            return access.company
    except:
        pass
    
    return None


@login_required
def analytics_dashboard(request):
    """
    Main analytics dashboard showing:
    - AI accuracy and performance
    - Time savings
    - Top performing patterns
    - User leaderboard
    - System health
    """
    company = get_user_active_company(request)
    
    if not company:
        messages.error(request, "No active company found. Please select a company first.")
        return redirect('/')
    
    # Date range filters
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # 📊 Overall Metrics (Last 30 Days)
    recent_metrics = ReconciliationMetrics.objects.filter(
        company=company,
        date__gte=last_30_days
    )
    
    overall_stats = recent_metrics.aggregate(
        total_transactions=Sum('total_transactions'),
        ai_matched=Sum('ai_matched'),
        rule_matched=Sum('rule_matched'),
        time_saved=Sum('total_time_saved'),
        avg_automation=Avg('automation_rate'),
        avg_accuracy=Avg('ai_accuracy')
    )
    
    # Calculate totals
    total_transactions = overall_stats['total_transactions'] or 0
    total_ai_matched = overall_stats['ai_matched'] or 0
    total_rule_matched = overall_stats['rule_matched'] or 0
    total_time_saved_hours = overall_stats['time_saved'] or 0
    avg_automation_rate = overall_stats['avg_automation'] or 0
    avg_ai_accuracy = overall_stats['avg_accuracy'] or 0
    
    # 📈 Daily Metrics for Charts (Last 7 Days)
    daily_metrics = ReconciliationMetrics.objects.filter(
        company=company,
        date__gte=last_7_days
    ).order_by('date')
    
    # Prepare chart data
    chart_dates = []
    chart_transactions = []
    chart_automation_rate = []
    chart_ai_accuracy = []
    
    for metric in daily_metrics:
        chart_dates.append(metric.date.strftime('%b %d'))
        chart_transactions.append(metric.total_transactions)
        chart_automation_rate.append(float(metric.automation_rate))
        chart_ai_accuracy.append(float(metric.ai_accuracy))
    
    # 🏆 Top Performing Patterns
    top_patterns = PatternAnalytics.objects.filter(
        pattern__company=company,
        pattern__is_active=True
    ).select_related('pattern').order_by('-acceptance_rate')[:10]
    
    # 👥 User Leaderboard (Last 30 Days)
    user_leaderboard = UserPerformance.objects.filter(
        company=company,
        date__gte=last_30_days
    ).values('user__username', 'user__first_name', 'user__last_name').annotate(
        total_reconciliations=Sum('transactions_processed'),
        total_ai_used=Sum('accepted_suggestions'),
        avg_time=Avg('avg_time_per_transaction')
    ).order_by('-total_reconciliations')[:10]
    
    # Format user leaderboard
    for user in user_leaderboard:
        full_name = f"{user.get('user__first_name', '')} {user.get('user__last_name', '')}".strip()
        user['display_name'] = full_name or user['user__username']
        # Calculate time saved (assume 5 min manual vs avg_time)
        time_saved_seconds = max(0, (300 - (user['avg_time'] or 0)) * (user['total_reconciliations'] or 0))
        user['time_saved_hours'] = round(time_saved_seconds / 3600, 1)
        user['ai_usage_rate'] = round(
            (user['total_ai_used'] or 0) / max(user['total_reconciliations'] or 1, 1) * 100, 
            1
        )
    
    # 🔧 System Health
    try:
        system_health = SystemHealth.objects.filter(company=company).latest('date')
    except SystemHealth.DoesNotExist:
        system_health = None
    
    # 📊 Pattern Performance Breakdown
    pattern_stats = MatchPattern.objects.filter(
        company=company,
        is_active=True
    ).aggregate(
        total_patterns=Count('id'),
        well_trained=Count('id', filter=Q(times_seen__gte=10)),
        needs_training=Count('id', filter=Q(times_seen__lt=10)),
        high_accuracy=Count('id', filter=Q(times_accepted__gt=0) & Q(accuracy_rate__gte=80.0))
    )
    
    # Calculate percentages for template
    total_patterns = pattern_stats['total_patterns'] or 1  # Avoid division by zero
    pattern_stats['well_trained_pct'] = (pattern_stats['well_trained'] or 0) * 100 / total_patterns
    pattern_stats['needs_training_pct'] = (pattern_stats['needs_training'] or 0) * 100 / total_patterns
    pattern_stats['high_accuracy_pct'] = (pattern_stats['high_accuracy'] or 0) * 100 / total_patterns
    
    # 🎯 Recent AI Feedback
    recent_feedback = MatchFeedback.objects.filter(
        company=company
    ).select_related('match_history', 'user').order_by('-created_at')[:20]
    
    # 📉 Trend Analysis
    # Compare last 7 days vs previous 7 days
    previous_7_days = last_7_days - timedelta(days=7)
    
    last_week_metrics = ReconciliationMetrics.objects.filter(
        company=company,
        date__gte=last_7_days,
        date__lt=today
    ).aggregate(
        avg_automation=Avg('automation_rate'),
        avg_accuracy=Avg('ai_accuracy')
    )
    
    previous_week_metrics = ReconciliationMetrics.objects.filter(
        company=company,
        date__gte=previous_7_days,
        date__lt=last_7_days
    ).aggregate(
        avg_automation=Avg('automation_rate'),
        avg_accuracy=Avg('ai_accuracy')
    )
    
    # Calculate trends
    automation_trend = 0
    accuracy_trend = 0
    
    if previous_week_metrics['avg_automation'] and last_week_metrics['avg_automation']:
        automation_trend = float(last_week_metrics['avg_automation'] - previous_week_metrics['avg_automation'])
    
    if previous_week_metrics['avg_accuracy'] and last_week_metrics['avg_accuracy']:
        accuracy_trend = float(last_week_metrics['avg_accuracy'] - previous_week_metrics['avg_accuracy'])
    
    context = {
        # Overall stats
        'total_transactions': total_transactions,
        'total_ai_matched': total_ai_matched,
        'total_rule_matched': total_rule_matched,
        'total_time_saved_hours': total_time_saved_hours,
        'avg_automation_rate': round(avg_automation_rate, 1),
        'avg_ai_accuracy': round(avg_ai_accuracy, 1),
        
        # Chart data
        'chart_dates': chart_dates,
        'chart_transactions': chart_transactions,
        'chart_automation_rate': chart_automation_rate,
        'chart_ai_accuracy': chart_ai_accuracy,
        
        # Top patterns
        'top_patterns': top_patterns,
        
        # User leaderboard
        'user_leaderboard': user_leaderboard,
        
        # System health
        'system_health': system_health,
        
        # Pattern stats
        'pattern_stats': pattern_stats,
        
        # Recent feedback
        'recent_feedback': recent_feedback,
        
        # Trends
        'automation_trend': round(automation_trend, 1),
        'accuracy_trend': round(accuracy_trend, 1),
        
        # Date ranges
        'date_range_start': last_30_days,
        'date_range_end': today,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
def pattern_detail(request, pattern_id):
    """
    Detailed view of a specific pattern's performance
    """
    company = get_user_active_company(request)
    
    if not company:
        messages.error(request, "No active company found. Please select a company first.")
        return redirect('/')
    
    try:
        pattern = MatchPattern.objects.get(id=pattern_id, company=company)
    except MatchPattern.DoesNotExist:
        from django.http import Http404
        raise Http404("Pattern not found")
    
    # Get pattern analytics
    try:
        analytics = PatternAnalytics.objects.get(pattern=pattern)
    except PatternAnalytics.DoesNotExist:
        analytics = None
    
    # Get match history
    match_history = TransactionMatchHistory.objects.filter(
        pattern=pattern
    ).order_by('-matched_at')[:50]
    
    # Get feedback
    feedback = MatchFeedback.objects.filter(
        pattern=pattern
    ).select_related('user').order_by('-created_at')[:30]
    
    context = {
        'pattern': pattern,
        'analytics': analytics,
        'match_history': match_history,
        'feedback': feedback,
    }
    
    return render(request, 'analytics/pattern_detail.html', context)


@login_required
def reset_ai_data(request):
    """
    Reset all AI learning data for the active company
    Requires confirmation via POST
    """
    company = get_user_active_company(request)
    
    if not company:
        messages.error(request, "No active company found.")
        return redirect('/')
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm') == 'yes'
        
        if confirm:
            try:
                # Delete all AI patterns
                patterns_deleted = MatchPattern.objects.filter(company=company).count()
                MatchPattern.objects.filter(company=company).delete()
                
                # Delete all match history
                history_deleted = TransactionMatchHistory.objects.filter(company=company).count()
                TransactionMatchHistory.objects.filter(company=company).delete()
                
                # Delete all feedback
                feedback_deleted = MatchFeedback.objects.filter(company=company).count()
                MatchFeedback.objects.filter(company=company).delete()
                
                # Delete analytics data
                PatternAnalytics.objects.filter(pattern__company=company).delete()
                ReconciliationMetrics.objects.filter(company=company).delete()
                UserPerformance.objects.filter(company=company).delete()
                SystemHealth.objects.filter(company=company).delete()
                
                messages.success(
                    request, 
                    f'✅ AI data reset successfully! Deleted: {patterns_deleted} patterns, '
                    f'{history_deleted} training records, {feedback_deleted} feedback entries.'
                )
            except Exception as e:
                messages.error(request, f'❌ Error resetting AI data: {str(e)}')
        else:
            messages.warning(request, 'AI reset cancelled.')
        
        return redirect('analytics:dashboard')
    
    # GET request - show confirmation page
    # Count what will be deleted
    patterns_count = MatchPattern.objects.filter(company=company).count()
    history_count = TransactionMatchHistory.objects.filter(company=company).count()
    feedback_count = MatchFeedback.objects.filter(company=company).count()
    
    context = {
        'company': company,
        'patterns_count': patterns_count,
        'history_count': history_count,
        'feedback_count': feedback_count,
    }
    
    return render(request, 'analytics/reset_ai_confirm.html', context)
