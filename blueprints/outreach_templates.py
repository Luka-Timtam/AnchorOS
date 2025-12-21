from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db_supabase import get_supabase
from datetime import datetime

outreach_templates_bp = Blueprint('outreach_templates', __name__, url_prefix='/outreach-templates')

def category_choices():
    return ['email', 'dm', 'call']

def subcategory_choices():
    return ['initial_outreach', 'follow_up', 'closing', 'proposal', 'check_in', 'referral']

@outreach_templates_bp.route('/')
def index():
    client = get_supabase()
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    search = request.args.get('search', '')
    
    query = client.table('outreach_templates').select('*')
    
    if category:
        query = query.eq('category', category)
    if subcategory:
        query = query.eq('subcategory', subcategory)
    if search:
        query = query.or_(f'name.ilike.%{search}%,content.ilike.%{search}%')
    
    result = query.order('is_favourite', desc=True).order('updated_at', desc=True).execute()
    templates = result.data
    
    email_templates = [t for t in templates if t.get('category') == 'email']
    dm_templates = [t for t in templates if t.get('category') == 'dm']
    call_templates = [t for t in templates if t.get('category') == 'call']
    
    return render_template('outreach_templates/index.html',
                         templates=templates,
                         email_templates=email_templates,
                         dm_templates=dm_templates,
                         call_templates=call_templates,
                         categories=category_choices(),
                         subcategories=subcategory_choices(),
                         current_category=category,
                         current_subcategory=subcategory,
                         current_search=search)


@outreach_templates_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        client = get_supabase()
        now = datetime.utcnow().isoformat()
        template_data = {
            'name': request.form['name'],
            'category': request.form['category'],
            'subcategory': request.form.get('subcategory', ''),
            'content': request.form['content'],
            'is_favourite': request.form.get('is_favourite') == 'on',
            'created_at': now,
            'updated_at': now
        }
        client.table('outreach_templates').insert(template_data).execute()
        flash('Template created successfully!', 'success')
        return redirect(url_for('outreach_templates.index'))
    
    return render_template('outreach_templates/form.html',
                         template=None,
                         categories=category_choices(),
                         subcategories=subcategory_choices())


@outreach_templates_bp.route('/<int:id>')
def view(id):
    client = get_supabase()
    result = client.table('outreach_templates').select('*').eq('id', id).execute()
    if not result.data:
        flash('Template not found.', 'error')
        return redirect(url_for('outreach_templates.index'))
    template = result.data[0]
    return render_template('outreach_templates/view.html', template=template)


@outreach_templates_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    client = get_supabase()
    result = client.table('outreach_templates').select('*').eq('id', id).execute()
    if not result.data:
        flash('Template not found.', 'error')
        return redirect(url_for('outreach_templates.index'))
    template = result.data[0]
    
    if request.method == 'POST':
        update_data = {
            'name': request.form['name'],
            'category': request.form['category'],
            'subcategory': request.form.get('subcategory', ''),
            'content': request.form['content'],
            'is_favourite': request.form.get('is_favourite') == 'on',
            'updated_at': datetime.utcnow().isoformat()
        }
        client.table('outreach_templates').update(update_data).eq('id', id).execute()
        flash('Template updated successfully!', 'success')
        return redirect(url_for('outreach_templates.view', id=id))
    
    return render_template('outreach_templates/form.html',
                         template=template,
                         categories=category_choices(),
                         subcategories=subcategory_choices())


@outreach_templates_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    client = get_supabase()
    client.table('outreach_templates').delete().eq('id', id).execute()
    flash('Template deleted successfully!', 'success')
    return redirect(url_for('outreach_templates.index'))


@outreach_templates_bp.route('/<int:id>/toggle-favourite', methods=['POST'])
def toggle_favourite(id):
    client = get_supabase()
    result = client.table('outreach_templates').select('is_favourite').eq('id', id).execute()
    if not result.data:
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    
    current_fav = result.data[0].get('is_favourite', False)
    new_fav = not current_fav
    
    client.table('outreach_templates').update({
        'is_favourite': new_fav,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', id).execute()
    
    return jsonify({'success': True, 'is_favourite': new_fav})
