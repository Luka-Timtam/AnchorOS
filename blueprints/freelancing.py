from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, FreelanceJob
from datetime import date
from sqlalchemy import func
import calendar

freelancing_bp = Blueprint('freelancing', __name__, url_prefix='/freelancing')


@freelancing_bp.route('/')
def index():
    jobs = FreelanceJob.query.order_by(FreelanceJob.date_completed.desc()).all()
    
    total_income = FreelanceJob.get_total_income()
    income_by_category = FreelanceJob.get_income_by_category()
    monthly_income = FreelanceJob.get_monthly_income(6)
    
    category_labels = dict(FreelanceJob.category_choices())
    
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
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other')
        amount = request.form.get('amount', 0)
        date_completed_str = request.form.get('date_completed')
        client_name = request.form.get('client_name', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('freelancing/form.html', job=None, categories=FreelanceJob.category_choices())
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount', 'error')
            return render_template('freelancing/form.html', job=None, categories=FreelanceJob.category_choices())
        
        date_completed = date.today()
        if date_completed_str:
            try:
                date_completed = date.fromisoformat(date_completed_str)
            except ValueError:
                pass
        
        job = FreelanceJob(  # type: ignore[call-arg]
            title=title,
            description=description,
            category=category,
            amount=amount,
            date_completed=date_completed,
            client_name=client_name,
            notes=notes
        )
        db.session.add(job)
        db.session.commit()
        
        flash('Freelance job added successfully!', 'success')
        return redirect(url_for('freelancing.index'))
    
    return render_template('freelancing/form.html', job=None, categories=FreelanceJob.category_choices())


@freelancing_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    job = FreelanceJob.query.get_or_404(id)
    
    if request.method == 'POST':
        job.title = request.form.get('title', '').strip()
        job.description = request.form.get('description', '').strip()
        job.category = request.form.get('category', 'other')
        job.client_name = request.form.get('client_name', '').strip()
        job.notes = request.form.get('notes', '').strip()
        
        try:
            job.amount = float(request.form.get('amount', 0))
        except ValueError:
            flash('Invalid amount', 'error')
            return render_template('freelancing/form.html', job=job, categories=FreelanceJob.category_choices())
        
        date_completed_str = request.form.get('date_completed')
        if date_completed_str:
            try:
                job.date_completed = date.fromisoformat(date_completed_str)
            except ValueError:
                pass
        
        if not job.title:
            flash('Title is required', 'error')
            return render_template('freelancing/form.html', job=job, categories=FreelanceJob.category_choices())
        
        db.session.commit()
        flash('Freelance job updated!', 'success')
        return redirect(url_for('freelancing.index'))
    
    return render_template('freelancing/form.html', job=job, categories=FreelanceJob.category_choices())


@freelancing_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    job = FreelanceJob.query.get_or_404(id)
    db.session.delete(job)
    db.session.commit()
    flash('Freelance job deleted', 'success')
    return redirect(url_for('freelancing.index'))
