from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import FreelancingIncome, get_supabase
from datetime import date
import calendar

freelancing_bp = Blueprint('freelancing', __name__, url_prefix='/freelancing')


def category_choices():
    return [
        ('photography', 'Photography'),
        ('one_off_job', 'One-Off Job'),
        ('consulting', 'Consulting'),
        ('side_project', 'Side Project'),
        ('cash_work', 'Cash Work'),
        ('other', 'Other')
    ]


def get_total_income():
    jobs = FreelancingIncome.query_all()
    return sum(float(getattr(j, 'amount', 0) or 0) for j in jobs)


def get_income_by_category():
    jobs = FreelancingIncome.query_all()
    income_by_cat = {}
    for job in jobs:
        cat = getattr(job, 'category', 'other')
        amount = float(getattr(job, 'amount', 0) or 0)
        income_by_cat[cat] = income_by_cat.get(cat, 0) + amount
    return income_by_cat


def get_monthly_income(months=6):
    client = get_supabase()
    result = client.table('freelance_jobs').select('*').order('date_completed', desc=True).execute()
    
    monthly_totals = {}
    for row in result.data:
        job_date = row.get('date_completed', '')
        if isinstance(job_date, str):
            try:
                d = date.fromisoformat(job_date.split('T')[0])
                key = (d.year, d.month)
                amount = float(row.get('amount', 0) or 0)
                monthly_totals[key] = monthly_totals.get(key, 0) + amount
            except:
                pass
    
    sorted_months = sorted(monthly_totals.keys(), reverse=True)[:months]
    sorted_months.reverse()
    
    return [(year, month, monthly_totals[(year, month)]) for year, month in sorted_months]


@freelancing_bp.route('/')
def index():
    jobs = FreelancingIncome.query_all(order_by='date_completed', order_desc=True)
    
    total_income = get_total_income()
    income_by_category = get_income_by_category()
    monthly_income = get_monthly_income(6)
    
    category_labels = dict(category_choices())
    
    chart_labels = []
    chart_data = []
    for year, month, amount in monthly_income:
        chart_labels.append(f"{calendar.month_abbr[month]} {year}")
        chart_data.append(amount)
    
    category_chart_labels = []
    category_chart_data = []
    for cat, amount in income_by_category.items():
        category_chart_labels.append(category_labels.get(cat, cat.title()))
        category_chart_data.append(amount)
    
    job_count = len(jobs)
    avg_job_value = total_income / job_count if job_count > 0 else 0
    
    return render_template('freelancing/index.html',
                           jobs=jobs,
                           total_income=total_income,
                           income_by_category=income_by_category,
                           category_labels=category_labels,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           category_chart_labels=category_chart_labels,
                           category_chart_data=category_chart_data,
                           job_count=job_count,
                           avg_job_value=avg_job_value)


@freelancing_bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other')
        amount = request.form.get('amount', 0)
        date_str = request.form.get('date')
        
        if not description:
            flash('Description is required', 'error')
            return render_template('freelancing/form.html', job=None, categories=category_choices())
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount', 'error')
            return render_template('freelancing/form.html', job=None, categories=category_choices())
        
        job_date = date.today()
        if date_str:
            try:
                job_date = date.fromisoformat(date_str)
            except ValueError:
                pass
        
        FreelancingIncome.insert({
            'description': description,
            'category': category,
            'amount': amount,
            'date_completed': job_date.isoformat()
        })
        
        flash('Freelance income added successfully!', 'success')
        return redirect(url_for('freelancing.index'))
    
    return render_template('freelancing/form.html', job=None, categories=category_choices())


@freelancing_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    job = FreelancingIncome.get_by_id(id)
    if not job:
        abort(404)
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other')
        
        try:
            amount = float(request.form.get('amount', 0))
        except ValueError:
            flash('Invalid amount', 'error')
            return render_template('freelancing/form.html', job=job, categories=category_choices())
        
        date_str = request.form.get('date')
        job_date = getattr(job, 'date_completed', date.today().isoformat())
        if date_str:
            try:
                job_date = date.fromisoformat(date_str).isoformat()
            except ValueError:
                pass
        
        if not description:
            flash('Description is required', 'error')
            return render_template('freelancing/form.html', job=job, categories=category_choices())
        
        FreelancingIncome.update_by_id(id, {
            'description': description,
            'category': category,
            'amount': amount,
            'date_completed': job_date
        })
        
        flash('Freelance income updated!', 'success')
        return redirect(url_for('freelancing.index'))
    
    return render_template('freelancing/form.html', job=job, categories=category_choices())


@freelancing_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    job = FreelancingIncome.get_by_id(id)
    if not job:
        abort(404)
    FreelancingIncome.delete_by_id(id)
    flash('Freelance income deleted', 'success')
    return redirect(url_for('freelancing.index'))
