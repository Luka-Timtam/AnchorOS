from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, OutreachTemplate

outreach_templates_bp = Blueprint('outreach_templates', __name__, url_prefix='/outreach-templates')

@outreach_templates_bp.route('/')
def index():
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    search = request.args.get('search', '')
    
    query = OutreachTemplate.query
    
    if category:
        query = query.filter(OutreachTemplate.category == category)
    if subcategory:
        query = query.filter(OutreachTemplate.subcategory == subcategory)
    if search:
        query = query.filter(
            (OutreachTemplate.name.ilike(f'%{search}%')) |
            (OutreachTemplate.content.ilike(f'%{search}%'))
        )
    
    templates = query.order_by(OutreachTemplate.is_favourite.desc(), OutreachTemplate.updated_at.desc()).all()
    
    email_templates = [t for t in templates if t.category == 'email']
    dm_templates = [t for t in templates if t.category == 'dm']
    call_templates = [t for t in templates if t.category == 'call']
    
    return render_template('outreach_templates/index.html',
                         templates=templates,
                         email_templates=email_templates,
                         dm_templates=dm_templates,
                         call_templates=call_templates,
                         categories=OutreachTemplate.category_choices(),
                         subcategories=OutreachTemplate.subcategory_choices(),
                         current_category=category,
                         current_subcategory=subcategory,
                         current_search=search)


@outreach_templates_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        template = OutreachTemplate(
            name=request.form['name'],
            category=request.form['category'],
            subcategory=request.form.get('subcategory', ''),
            content=request.form['content'],
            is_favourite=request.form.get('is_favourite') == 'on'
        )
        db.session.add(template)
        db.session.commit()
        flash('Template created successfully!', 'success')
        return redirect(url_for('outreach_templates.index'))
    
    return render_template('outreach_templates/form.html',
                         template=None,
                         categories=OutreachTemplate.category_choices(),
                         subcategories=OutreachTemplate.subcategory_choices())


@outreach_templates_bp.route('/<int:id>')
def view(id):
    template = OutreachTemplate.query.get_or_404(id)
    return render_template('outreach_templates/view.html', template=template)


@outreach_templates_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    template = OutreachTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        template.name = request.form['name']
        template.category = request.form['category']
        template.subcategory = request.form.get('subcategory', '')
        template.content = request.form['content']
        template.is_favourite = request.form.get('is_favourite') == 'on'
        db.session.commit()
        flash('Template updated successfully!', 'success')
        return redirect(url_for('outreach_templates.view', id=id))
    
    return render_template('outreach_templates/form.html',
                         template=template,
                         categories=OutreachTemplate.category_choices(),
                         subcategories=OutreachTemplate.subcategory_choices())


@outreach_templates_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    template = OutreachTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    flash('Template deleted successfully!', 'success')
    return redirect(url_for('outreach_templates.index'))


@outreach_templates_bp.route('/<int:id>/toggle-favourite', methods=['POST'])
def toggle_favourite(id):
    template = OutreachTemplate.query.get_or_404(id)
    template.is_favourite = not template.is_favourite
    db.session.commit()
    return jsonify({'success': True, 'is_favourite': template.is_favourite})
