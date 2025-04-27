from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify, session
from flask_login import login_required, current_user, login_user, logout_user
from extensions import db
from app.models import User, College, UserList, StudentNumber, PartyList, Platform, Candidate, Election, Vote, Position, VoterList, AuditLog
from app.decorators import admin_required
from .forms import LoginForm, CandidateForm, PositionForm, FlaskForm
from flask_wtf import FlaskForm
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import time
import io
import PyPDF2
import re
import secrets
from app.forms import ElectionForm

bp = Blueprint('main', __name__)

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@bp.route('/')
def index():
    elections = Election.query.filter_by(is_active=True).all()
    party_lists = PartyList.query.all()
    return render_template('index.html', elections=elections, party_lists=party_lists)

@bp.route('/election/<int:election_id>')
@login_required
def election(election_id):
    election = Election.query.get_or_404(election_id)
    
    # Check if user has already voted in this election
    existing_vote = Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash('You have already cast your vote in this election.', 'warning')
        return redirect(url_for('main.voting_history'))
    
    positions = Position.query.filter_by(election_id=election_id).all()
    candidates = {}
    
    for position in positions:
        # For representative positions, only show candidates from the same college
        if position.title.upper().strip() == 'REPRESENTATIVE':
            candidates[position.id] = Candidate.query.filter_by(
                position_id=position.id,
                college_id=current_user.college_id
            ).all()
        else:
            # For non-representative positions, show all candidates
            candidates[position.id] = Candidate.query.filter_by(position_id=position.id).all()
    
    return render_template('election.html', 
                         election=election,
                         positions=positions,
                         candidates=candidates)

@bp.route('/admin/party-lists', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_party_lists():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        image = request.files.get('image')
        
        party_list = PartyList(
            name=name,
            description=description,
            created_at=datetime.utcnow()
        )
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            # Create directory if it doesn't exist
            os.makedirs(os.path.join('app', 'static', 'party_images'), exist_ok=True)
            image.save(os.path.join('app', 'static', 'party_images', filename))
            party_list.image_path = filename
            
        db.session.add(party_list)
        db.session.commit()
        flash('Party List added successfully!', 'success')
        return redirect(url_for('main.manage_party_lists'))
        
    party_lists = PartyList.query.all()
    return render_template('admin/manage_party_lists.html', party_lists=party_lists)

@bp.route('/admin/party-lists/<int:id>/edit', methods=['POST'])
@login_required
def edit_party_list(id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))
        
    party_list = PartyList.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        image = request.files.get('image')
        
        party_list.name = name
        party_list.description = description
        
        if image and allowed_file(image.filename):
            # Delete old image if it exists
            if party_list.image_path:
                old_image_path = os.path.join('app', 'static', 'party_images', party_list.image_path)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Save new image
            filename = secure_filename(image.filename)
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            image.save(os.path.join('app', 'static', 'party_images', filename))
            party_list.image_path = filename
        
        try:
            db.session.commit()
            flash('Party List updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating party list. Please try again.', 'danger')
            
    return redirect(url_for('main.manage_party_lists'))

@bp.route('/admin/candidates/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_candidate():
    form = CandidateForm()
    
    # Populate form choices
    form.party_list.choices = [(p.id, p.name) for p in PartyList.query.all()]
    form.position_id.choices = [(p.id, f"{p.title} ({p.election.title})") for p in Position.query.all()]
    form.college_id.choices = [(c.id, c.name) for c in College.query.order_by(College.name).all()]
    
    if form.validate_on_submit():
        image_path = None
        if form.image.data:
            file = form.image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{int(time.time())}{ext}"
                
                # Create directory if it doesn't exist
                upload_dir = os.path.join('app', 'static', 'images', 'candidates')
                os.makedirs(upload_dir, exist_ok=True)
                
                file.save(os.path.join(upload_dir, filename))
                image_path = f"images/candidates/{filename}"

        try:
            # Get the position to check if it's a representative position
            position = Position.query.get(form.position_id.data)
            is_representative = position and position.title.upper().strip() == 'REPRESENTATIVE'
            
            candidate = Candidate(
                name=form.name.data,
                description=form.description.data,
                party_list_id=form.party_list.data,
                position_id=form.position_id.data,
                college_id=form.college_id.data if is_representative else None,
                image_path=image_path
            )
            db.session.add(candidate)
            db.session.commit()
            flash('Candidate added successfully!', 'success')
            return redirect(url_for('main.manage_candidates'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding candidate. Please try again.', 'danger')
            return redirect(url_for('main.add_candidate'))
            
    return render_template('admin/add_candidate.html', form=form)

@bp.route('/admin/candidates/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    form = CandidateForm(obj=candidate)
    
    # Populate form choices
    form.party_list.choices = [(p.id, p.name) for p in PartyList.query.all()]
    form.position_id.choices = [(p.id, f"{p.title} ({p.election.title})") for p in Position.query.all()]
    form.college_id.choices = [(c.id, c.name) for c in College.query.order_by(College.name).all()]
    
    if form.validate_on_submit():
        candidate.name = form.name.data
        candidate.description = form.description.data
        candidate.party_list_id = form.party_list.data
        candidate.position_id = form.position_id.data
        
        # Check if the position is representative
        position = Position.query.get(form.position_id.data)
        is_representative = position and position.title.upper().strip() == 'REPRESENTATIVE'
        candidate.college_id = form.college_id.data if is_representative else None
        
        if form.image.data:
            file = form.image.data
            if file and allowed_file(file.filename):
                if candidate.image_path:
                    old_image_path = os.path.join('app', 'static', candidate.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{int(time.time())}{ext}"
                file.save(os.path.join('app', 'static', 'images', 'candidates', filename))
                candidate.image_path = f"images/candidates/{filename}"
        
        db.session.commit()
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('main.manage_candidates'))
    
    return render_template('admin/edit_candidate.html', form=form, candidate=candidate)

@bp.route('/admin/candidates/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    
    try:
        if candidate.image_path:
            image_path = os.path.join('app', 'static', candidate.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(candidate)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/admin/party-lists/<int:party_id>/delete', methods=['POST'])
@login_required
def delete_party_list(party_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    party_list = PartyList.query.get_or_404(party_id)
    
    try:
        if party_list.image_path:
            image_path = os.path.join('app', 'static', 'party_images', party_list.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(party_list)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/admin/elections/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_election():
    form = ElectionForm()
    if form.validate_on_submit():
        election = Election(
            title=form.title.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_active=form.is_active.data
        )
        
        db.session.add(election)
        db.session.commit()
        flash('Election created successfully!', 'success')
        return redirect(url_for('main.manage_elections'))
        
    return render_template('admin/create_election.html', form=form)

@bp.route('/admin/elections')
@login_required
@admin_required
def manage_elections():
    elections = Election.query.all()
    return render_template('admin/manage_elections.html', elections=elections)

@bp.route('/admin/elections/<int:election_id>/results')
@login_required
@admin_required
def election_results(election_id):
    election = Election.query.get_or_404(election_id)
    positions = Position.query.filter_by(election_id=election_id).all()
    
    # Calculate results
    results = []
    total_votes = 0
    
    for position in positions:
        # Get all votes for this position
        position_votes = Vote.query.filter_by(position_id=position.id).count()
        abstain_votes = Vote.query.filter_by(position_id=position.id, is_abstain=True).count()
        
        candidates = Candidate.query.filter_by(position_id=position.id).all()
        position_results = []
        
        # Add candidate results
        for candidate in candidates:
            votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            position_results.append({
                'candidate': candidate,
                'votes': votes,
                'percentage': (votes / position_votes * 100) if position_votes > 0 else 0
            })
        
        # Add abstain results
        if abstain_votes > 0:
            position_results.append({
                'candidate': None,  # No candidate for abstain
                'votes': abstain_votes,
                'percentage': (abstain_votes / position_votes * 100) if position_votes > 0 else 0,
                'is_abstain': True
            })
        
        # Sort by votes in descending order
        position_results.sort(key=lambda x: x['votes'], reverse=True)
        
        results.append({
            'position': position,
            'candidates': position_results,
            'total_votes': position_votes
        })
        
        total_votes += position_votes
    
    return render_template('admin/election_results.html', 
                         election=election,
                         positions=results,
                         total_votes=total_votes)

@bp.route('/admin/elections/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_election(id):
    election = Election.query.get_or_404(id)
    
    if request.method == 'POST':
        election.title = request.form.get('title')
        election.description = request.form.get('description')
        election.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        election.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        election.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Election updated successfully!', 'success')
        return redirect(url_for('main.manage_elections'))
        
    return render_template('admin/edit_election.html', election=election)

@bp.route('/admin/elections/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_election(id):
    election = Election.query.get_or_404(id)
    
    try:
        # Delete all votes first
        Vote.query.filter_by(election_id=id).delete()
        
        # Delete all audit logs for this election
        AuditLog.query.filter_by(election_id=id).delete()
        
        # Delete all candidates associated with positions in this election
        for position in election.positions:
            Candidate.query.filter_by(position_id=position.id).delete()
        
        # Delete all positions
        Position.query.filter_by(election_id=id).delete()
        
        # Finally delete the election
        db.session.delete(election)
        db.session.commit()
        flash('Election deleted successfully.', 'success')
        return redirect(url_for('main.manage_elections'))
    except Exception as e:
        db.session.rollback()
        flash('Error deleting election: ' + str(e), 'danger')
        return redirect(url_for('main.manage_elections'))

@bp.route('/admin/candidates')
@login_required
@admin_required
def manage_candidates():
    candidates = Candidate.query.all()
    party_lists = PartyList.query.all()
    elections = Election.query.all()
    positions = Position.query.all()
    
    # Get filter parameters
    selected_election_id = request.args.get('election_id', type=int)
    selected_position_id = request.args.get('position_id', type=int)
    
    # Apply filters if provided
    if selected_election_id:
        candidates = [c for c in candidates if c.position.election_id == selected_election_id]
    if selected_position_id:
        candidates = [c for c in candidates if c.position_id == selected_position_id]
    
    return render_template('admin/manage_candidates.html', 
                         candidates=candidates,
                         party_lists=party_lists,
                         elections=elections,
                         positions=positions,
                         selected_election_id=selected_election_id,
                         selected_position_id=selected_position_id)

@bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    colleges = College.query.all()
    return render_template('admin/manage_users.html', users=users, colleges=colleges)

@bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    colleges = College.query.order_by(College.name).all()
    
    # Prevent editing role of default admin
    if user.is_default_admin and current_user.id != user.id:
        flash('The default admin account cannot be modified by other users.', 'danger')
        return redirect(url_for('main.manage_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        student_id = request.form.get('student_id')
        college_id = request.form.get('college_id')
        role = request.form.get('role')
        new_password = request.form.get('password')
        
        # Prevent changing role of default admin
        if user.is_default_admin and role != 'admin':
            flash('Cannot change the role of the default admin account.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
        
        # Validate college selection
        if not college_id:
            flash('College selection is required.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
            
        # Check if username exists (excluding current user)
        existing_user = User.query.filter(
            User.username == username,
            User.id != user_id
        ).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
            
        # Check if email exists (excluding current user)
        existing_user = User.query.filter(
            User.email == email,
            User.id != user_id
        ).first()
        if existing_user:
            flash('Email already exists.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
            
        # Check if student ID exists (excluding current user)
        existing_user = User.query.filter(
            User.student_id == student_id,
            User.id != user_id
        ).first()
        if existing_user:
            flash('Student ID already exists.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
        
        try:
            user.username = username
            user.email = email
            user.student_id = student_id
            user.college_id = college_id
            if not user.is_default_admin:  # Only allow role change for non-default admin
                user.role = role
            
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('main.manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating user. Please try again.', 'danger')
            return render_template('admin/edit_user.html', user=user, colleges=colleges)
        
    return render_template('admin/edit_user.html', user=user, colleges=colleges)

@bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        # Get the user to delete
        user_to_delete = User.query.get_or_404(user_id)

        # Get the admin email from config
        admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@uvote.com')

        # Don't allow deleting the default admin
        if user_to_delete.email == admin_email:
            flash('Cannot delete the default admin account.', 'error')
            return redirect(url_for('main.manage_users'))

        # Don't allow deleting yourself
        if user_to_delete.id == current_user.id:
            flash('Cannot delete your own account.', 'error')
            return redirect(url_for('main.manage_users'))

        # Delete associated votes and audit logs first
        try:
            # Start a transaction
            db.session.begin_nested()
            
            # Delete associated votes
            Vote.query.filter_by(user_id=user_id).delete()
            
            # Delete associated audit logs
            AuditLog.query.filter_by(user_id=user_id).delete()
            
            # Delete the user
            db.session.delete(user_to_delete)
            
            # Commit the transaction
            db.session.commit()
            
            flash('User deleted successfully.', 'success')
            return redirect(url_for('main.manage_users'))

        except Exception as e:
            # Roll back the transaction
            db.session.rollback()
            current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
            flash('Error deleting user. Please try again.', 'error')
            return redirect(url_for('main.manage_users'))

    except Exception as e:
        current_app.logger.error(f"Error in delete_user route: {str(e)}")
        flash('Error processing request. Please try again.', 'error')
        return redirect(url_for('main.manage_users'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Clear any existing flash messages
    session.pop('_flashes', None)
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by email first, then by username as fallback
        user = User.query.filter_by(email=form.username.data).first()
        if not user:
            user = User.query.filter_by(username=form.username.data).first()
            
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        flash('Invalid username/email or password', 'danger')
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        elections = Election.query.all()
        candidates = Candidate.query.all()
        users = User.query.all()
        
        stats = {
            'total_elections': len(elections),
            'active_elections': len([e for e in elections if e.is_active]),
            'total_candidates': len(candidates),
            'total_voters': len([u for u in users if u.role == 'voter'])
        }
        
        return render_template('dashboard/admin.html', elections=elections, stats=stats)
    else:
        active_elections = Election.query.filter_by(is_active=True).all()
        return render_template('dashboard/voter.html', elections=active_elections)

@bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    elections = Election.query.all()
    candidates = Candidate.query.all()
    users = User.query.all()
    party_lists = PartyList.query.all()
    
    stats = {
        'total_elections': len(elections),
        'active_elections': len([e for e in elections if e.is_active]),
        'total_candidates': len(candidates),
        'total_users': len(users),
        'total_voters': len([u for u in users if u.role == 'voter']),
        'total_admins': len([u for u in users if u.role == 'admin']),
        'total_party_lists': len(party_lists)
    }
    
    return render_template('dashboard/admin.html', 
                         elections=elections,
                         candidates=candidates,
                         users=users,
                         party_lists=party_lists,
                         stats=stats)

@bp.route('/admin/user-lists/upload', methods=['POST'])
@login_required
@admin_required
def upload_user_list():
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('main.manage_user_lists'))
    
    file = request.files['file']
    college_id = request.form.get('college_id')
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('main.manage_user_lists'))
    
    if not college_id:
        flash('College is required', 'danger')
        return redirect(url_for('main.manage_user_lists'))
    
    if file and allowed_file(file.filename, {'pdf'}):
        try:
            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'user_lists')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Verify PDF content
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                if len(pdf_reader.pages) == 0:
                    os.remove(file_path)
                    flash('The uploaded PDF file appears to be empty or corrupted.', 'danger')
                    return redirect(url_for('main.manage_user_lists'))
                
                # Extract and log first page content for verification
                first_page = pdf_reader.pages[0].extract_text()
                current_app.logger.info(f"First page content of uploaded PDF: {first_page[:500]}...")
            
            # Create UserList record
            user_list = UserList(
                filename=filename,
                file_path=file_path,
                college_id=college_id
            )
            
            db.session.add(user_list)
            db.session.commit()
            flash('Enrollment list uploaded successfully!', 'success')
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            current_app.logger.error(f"Error uploading enrollment list: {str(e)}")
            flash(f'Error uploading enrollment list: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Only PDF files are allowed.', 'danger')
    
    return redirect(url_for('main.manage_user_lists'))

@bp.route('/admin/user-lists/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user_list(id):
    user_list = UserList.query.get_or_404(id)
    
    # Delete the file
    if os.path.exists(user_list.file_path):
        os.remove(user_list.file_path)
    
    db.session.delete(user_list)
    db.session.commit()
    
    flash('User list deleted successfully', 'success')
    return redirect(url_for('main.manage_user_lists'))

@bp.route('/admin/user-lists/<int:id>/download')
@login_required
@admin_required
def download_user_list(id):
    user_list = UserList.query.get_or_404(id)
    return send_file(user_list.file_path, as_attachment=True)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Create registration form
    form = FlaskForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email').strip().lower()  # Convert email to lowercase
        student_id = request.form.get('student_id').strip()
        college_id = request.form.get('college_id')
        
        current_app.logger.info(f"Registration attempt - Student ID: {student_id}, College ID: {college_id}")
        
        # Input validation
        if not student_id:
            flash('Student ID is required', 'danger')
            return redirect(url_for('main.register'))
            
        if not email:
            flash('Email is required', 'danger')
            return redirect(url_for('main.register'))
            
        if not college_id:
            flash('Please select your college', 'danger')
            return redirect(url_for('main.register'))
        
        # Check if user already exists (case-insensitive email check)
        existing_user = User.query.filter(db.func.lower(User.email) == email).first()
        if existing_user:
            flash('Email already exists', 'danger')
            return redirect(url_for('main.register'))
        
        if User.query.filter_by(student_id=student_id).first():
            flash('Student ID already exists', 'danger')
            return redirect(url_for('main.register'))
        
        # Verify student number against enrollment list
        college = College.query.get(college_id)
        if not college:
            flash('Invalid college selected', 'danger')
            return redirect(url_for('main.register'))
        
        # Get the most recent enrollment list for the selected college
        user_list = UserList.query.filter_by(college_id=college_id).order_by(UserList.id.desc()).first()
        
        if not user_list:
            flash('No enrollment list found for this college. Please contact the administrator.', 'danger')
            return redirect(url_for('main.register'))
        
        # Check if student number exists in the enrollment list
        student_found = False
        try:
            current_app.logger.info(f"Checking enrollment list: {user_list.filename}")
            with open(user_list.file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Extract all text from the PDF
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    full_text += page_text
                    current_app.logger.info(f"Page {page_num + 1} content: {page_text[:200]}...")
                
                # Log the full text for debugging
                current_app.logger.info(f"Full PDF text: {full_text[:1000]}...")
                
                # Split into lines and look for the student ID
                lines = full_text.split('\n')
                current_app.logger.info(f"Total lines in PDF: {len(lines)}")
                
                for line_num, line in enumerate(lines):
                    # Clean the line
                    cleaned_line = line.strip()
                    if not cleaned_line:
                        continue
                        
                    # Log each non-empty line for debugging
                    current_app.logger.info(f"Line {line_num + 1}: {cleaned_line}")
                    
                    # Try different ways to find the student ID
                    # 1. Direct match
                    if student_id == cleaned_line:
                        student_found = True
                        current_app.logger.info(f"Found exact match in line {line_num + 1}")
                        break
                        
                    # 2. Check if student ID is a word in the line
                    words = cleaned_line.split()
                    if student_id in words:
                        student_found = True
                        current_app.logger.info(f"Found student ID in words of line {line_num + 1}")
                        break
                        
                    # 3. Check if student ID is part of the line (for cases where it might be part of a longer string)
                    if student_id in cleaned_line:
                        student_found = True
                        current_app.logger.info(f"Found student ID as substring in line {line_num + 1}")
                        break
                
                if not student_found:
                    current_app.logger.warning(f"Student ID {student_id} not found in enrollment list")
                    flash('Your Student ID was not found in the enrollment list. Please verify your Student ID or contact the administrator.', 'danger')
                    return redirect(url_for('main.register'))
                
        except Exception as e:
            current_app.logger.error(f"Error processing enrollment list: {str(e)}")
            flash('Error verifying student ID. Please contact the administrator.', 'danger')
            return redirect(url_for('main.register'))
        
        # If student ID is found, create the user
        try:
            user = User(
                username=student_id,  # Set username to student_id instead of email
                email=email,
                student_id=student_id,
                college_id=college_id,
                role='voter'
            )
            user.set_password(student_id)
            
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f"Successfully registered user with Student ID: {student_id}")
            flash('Registration successful! You can now login using your Student ID as both username and password.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            flash('Error during registration. Please try again.', 'danger')
            return redirect(url_for('main.register'))
    
    # GET request - show registration form
    colleges = College.query.all()
    return render_template('register.html', colleges=colleges, form=form)

@bp.route('/admin/positions')
@login_required
@admin_required
def manage_positions():
    positions = Position.query.all()
    elections = Election.query.all()
    form = PositionForm()
    form.election_id.choices = [(e.id, e.title) for e in elections]
    return render_template('admin/manage_positions.html', 
                         positions=positions,
                         elections=elections,
                         form=form)

@bp.route('/admin/positions/add', methods=['POST'])
@login_required
@admin_required
def add_position():
    form = PositionForm()
    elections = Election.query.all()
    form.election_id.choices = [(e.id, e.title) for e in elections]
    
    if form.validate_on_submit():
        try:
            position = Position(
                title=form.title.data,
                description=form.description.data,
                election_id=form.election_id.data
            )
            
            db.session.add(position)
            db.session.commit()
            flash('Position added successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding position. Please try again.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('main.manage_positions'))

@bp.route('/admin/positions/<int:position_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_position(position_id):
    form = PositionForm()
    elections = Election.query.all()
    form.election_id.choices = [(e.id, e.title) for e in elections]
    
    if form.validate_on_submit():
        position = Position.query.get_or_404(position_id)
        try:
            position.title = form.title.data
            position.description = form.description.data
            position.election_id = form.election_id.data
            
            db.session.commit()
            flash('Position updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating position. Please try again.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('main.manage_positions'))

@bp.route('/admin/positions/<int:position_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_position(position_id):
    position = Position.query.get_or_404(position_id)
    try:
        # Delete all associated candidates first
        Candidate.query.filter_by(position_id=position_id).delete()
        db.session.delete(position)
        db.session.commit()
        # If the request is AJAX (fetch), return JSON
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        # Otherwise, redirect (for form POST or direct access)
        return redirect(url_for('main.manage_positions'))
    except Exception as e:
        db.session.rollback()
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('main.manage_positions'))

@bp.route('/admin/colleges')
@login_required
@admin_required
def manage_colleges():
    colleges = College.query.order_by(College.id.desc()).all()
    return render_template('admin/manage_colleges.html', colleges=colleges)

@bp.route('/admin/colleges/add', methods=['POST'])
@login_required
@admin_required
def add_college():
    name = request.form.get('name')
    
    if not name:
        flash('Name is required.', 'danger')
        return redirect(url_for('main.manage_colleges'))
    
    college = College(name=name)
    db.session.add(college)
    db.session.commit()
    
    flash('College added successfully.', 'success')
    return redirect(url_for('main.manage_colleges'))

@bp.route('/admin/colleges/<int:college_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_college(college_id):
    college = College.query.get_or_404(college_id)
    
    name = request.form.get('name')
    
    if not name:
        flash('Name is required.', 'danger')
        return redirect(url_for('main.manage_colleges'))
    
    college.name = name
    
    db.session.commit()
    flash('College updated successfully.', 'success')
    return redirect(url_for('main.manage_colleges'))

@bp.route('/admin/colleges/<int:college_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_college(college_id):
    try:
        # Validate CSRF token
        try:
            validate_csrf(request.form.get('csrf_token'))
        except ValidationError:
            return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 400
            
        college = College.query.get_or_404(college_id)
        
        # Check for related records
        if db.session.query(User).filter_by(college_id=college_id).count() > 0:
            return jsonify({
                'success': False,
                'message': 'Cannot delete college that has associated users. Please remove or reassign all users first.'
            }), 400
            
        if db.session.query(Candidate).filter_by(college_id=college_id).count() > 0:
            return jsonify({
                'success': False,
                'message': 'Cannot delete college that has associated candidates. Please remove or reassign all candidates first.'
            }), 400
            
        if db.session.query(UserList).filter_by(college_id=college_id).count() > 0:
            return jsonify({
                'success': False,
                'message': 'Cannot delete college that has associated user lists. Please delete the user lists first.'
            }), 400
        
        try:
            db.session.delete(college)
            db.session.commit()
            return jsonify({'success': True, 'message': 'College deleted successfully'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error deleting college {college_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Database error occurred while deleting college.'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in delete_college route: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred.'
        }), 500

@bp.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('main.manage_users'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('main.manage_users'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('User added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding user. Please try again.', 'danger')
            
    return redirect(url_for('main.manage_users'))

@bp.route('/admin/user-lists', methods=['GET'])
@login_required
@admin_required
def manage_user_lists():
    user_lists = UserList.query.all()
    colleges = College.query.all()
    return render_template('admin/manage_user_lists.html', user_lists=user_lists, colleges=colleges)

@bp.route('/voting-history')
@login_required
def voting_history():
    voting_history = {}
    
    # Get all elections
    elections = Election.query.all()
    
    for election in elections:
        # Get all votes for this election by the current user
        votes = Vote.query.filter_by(
            user_id=current_user.id,
            election_id=election.id
        ).options(
            db.joinedload(Vote.candidate).joinedload(Candidate.party_list),
            db.joinedload(Vote.position)
        ).all()
        
        if votes:
            voting_history[election.id] = {
                'election': election,
                'votes': votes
            }
    
    return render_template('voting_history.html', voting_history=voting_history)

@bp.route('/election/<int:election_id>/confirm-vote', methods=['POST', 'GET'])
@login_required
def confirm_vote(election_id):
    election = Election.query.options(db.joinedload(Election.positions)).get_or_404(election_id)
    
    # Check if election is active
    if not election.is_active:
        flash('This election is not active.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

    # Check for existing votes with detailed message
    existing_vote = Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash('You have already cast your vote in this election. Each user can only vote once.', 'warning')
        return redirect(url_for('main.voting_history'))

    if request.method == 'POST':
        # Clear any existing session data for this election
        session_keys = [
            f'vote_selections_{election_id}',
            f'vote_confirmation_code_{election_id}'
        ]
        for key in session_keys:
            session.pop(key, None)
            
        # Collect votes from form
        selections = {}
        for position in election.positions:
            vote_value = request.form.get(f'vote_{position.id}')
            if not vote_value:
                flash(f'Please select a candidate or abstain for {position.title}.', 'danger')
                return redirect(url_for('main.election', election_id=election_id))
            selections[str(position.id)] = vote_value
            
        # Double-check for duplicate votes before proceeding
        if Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first():
            flash('You have already cast your vote in this election. Each user can only vote once.', 'warning')
            return redirect(url_for('main.voting_history'))
            
        # Generate a random 6-digit confirmation code
        confirmation_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store selections and confirmation code in session
        session[f'vote_selections_{election_id}'] = selections
        session[f'vote_confirmation_code_{election_id}'] = confirmation_code
        
        # Create audit log for vote confirmation attempt
        audit_log = AuditLog(
            user_id=current_user.id,
            election_id=election_id,
            action='VOTE_CONFIRMATION_STARTED',
            details='Vote confirmation process initiated',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return render_template(
            'confirm_vote.html',
            election=election,
            selections=selections,
            confirmation_code=confirmation_code
        )
    else:
        # GET: Show confirmation page if selections exist
        selections = session.get(f'vote_selections_{election_id}')
        if not selections:
            flash('No selections to confirm.', 'danger')
            return redirect(url_for('main.election', election_id=election_id))
        return render_template('confirm_vote.html', election=election, selections=selections)

@bp.route('/election/<int:election_id>/cast-vote', methods=['POST'])
@login_required
def cast_vote(election_id):
    election = Election.query.options(db.joinedload(Election.positions)).get_or_404(election_id)
    
    # Check if election is active
    if not election.is_active:
        flash('This election is not active.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

    # Check for existing votes with detailed message
    existing_vote = Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash('You have already cast your vote in this election. Each user can only vote once.', 'warning')
        return redirect(url_for('main.voting_history'))

    # Verify the confirmation code
    session_key = f'vote_confirmation_code_{election_id}'
    submitted_code = request.form.get('confirmation_code')
    stored_code = session.get(session_key)
    
    if not submitted_code or not stored_code or submitted_code != stored_code:
        flash('Invalid confirmation code. Please try again.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

    # Use selections from session if available
    selections_key = f'vote_selections_{election_id}'
    selections = session.get(selections_key)
    if not selections:
        flash('No vote selections found. Please review and confirm your votes.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

    try:
        # Final check for duplicate votes before committing
        if Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first():
            flash('You have already cast your vote in this election. Each user can only vote once.', 'warning')
            return redirect(url_for('main.voting_history'))

        # Get all candidates for this election's positions in a single query
        position_candidates = {}
        candidates = Candidate.query.join(Position).filter(Position.election_id == election_id).all()
        for candidate in candidates:
            if candidate.position_id not in position_candidates:
                position_candidates[candidate.position_id] = {}
            position_candidates[candidate.position_id][candidate.id] = candidate

        # Process votes
        votes_to_add = []
        audit_details = []
        
        for position in election.positions:
            vote_value = selections.get(str(position.id))
            if not vote_value:
                flash(f'Please select a candidate or abstain for {position.title}.', 'danger')
                return redirect(url_for('main.election', election_id=election_id))

            vote = Vote(
                user_id=current_user.id,
                election_id=election_id,
                position_id=position.id
            )

            if vote_value == 'abstain':
                vote.is_abstain = True
                vote.candidate_id = None
                audit_details.append(f"Abstained for position: {position.title}")
            else:
                try:
                    candidate_id = int(vote_value)
                    candidate = position_candidates.get(position.id, {}).get(candidate_id)
                    if not candidate:
                        flash(f'Invalid candidate selected for {position.title}.', 'danger')
                        return redirect(url_for('main.election', election_id=election_id))
                    if position.title.upper().strip() == 'REPRESENTATIVE':
                        if candidate.college_id != current_user.college_id:
                            flash('You can only vote for representatives from your college.', 'danger')
                            return redirect(url_for('main.election', election_id=election_id))
                    vote.candidate_id = candidate_id
                    vote.is_abstain = False
                    audit_details.append(f"Voted for {candidate.name} in position: {position.title}")
                except ValueError:
                    flash(f'Invalid vote value for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
            votes_to_add.append(vote)

        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            election_id=election_id,
            action='CAST_VOTE',
            details='\n'.join(audit_details),
            ip_address=request.remote_addr
        )

        # Save everything to database
        db.session.bulk_save_objects(votes_to_add)
        db.session.add(audit_log)
        db.session.commit()

        # Clear session data
        session.pop(selections_key, None)
        session.pop(session_key, None)
        
        flash('Your vote has been cast successfully!', 'success')
        return redirect(url_for('main.voting_history'))

    except Exception as e:
        db.session.rollback()
        # Log the error
        error_audit = AuditLog(
            user_id=current_user.id,
            election_id=election_id,
            action='VOTE_ERROR',
            details=str(e),
            ip_address=request.remote_addr
        )
        try:
            db.session.add(error_audit)
            db.session.commit()
        except:
            pass  # If we can't log the error, continue with the error response
            
        flash(f'An error occurred while casting your vote. Please try again.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

@bp.route('/admin/candidate/<int:candidate_id>/update-party-list', methods=['POST'])
@login_required
def update_candidate_party_list(candidate_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    candidate = Candidate.query.get_or_404(candidate_id)
    
    try:
        data = request.get_json()
        party_list_id = data.get('party_list_id')
        
        if party_list_id:
            party_list = PartyList.query.get(party_list_id)
            if not party_list:
                return jsonify({'success': False, 'message': 'Party list not found'}), 404
            candidate.party_list_id = party_list_id
        else:
            candidate.party_list_id = None
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Party list updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/admin/elections/<int:election_id>/reset', methods=['POST'])
@login_required
@admin_required
def reset_election_results(election_id):
    election = Election.query.get_or_404(election_id)
    
    try:
        # Create audit log for reset attempt
        audit_log = AuditLog(
            user_id=current_user.id,
            election_id=election_id,
            action='RESET_ELECTION',
            details=f'Election results reset by admin: {current_user.username}',
            ip_address=request.remote_addr
        )
        
        # Delete all votes for this election
        Vote.query.filter_by(election_id=election_id).delete()
        
        # Add the audit log
        db.session.add(audit_log)
        db.session.commit()
        
        flash('Election results have been reset successfully.', 'success')
        return redirect(url_for('main.election_results', election_id=election_id))
    except Exception as e:
        db.session.rollback()
        flash('Error resetting election results: ' + str(e), 'danger')
        return redirect(url_for('main.election_results', election_id=election_id))

# Add this function to create default admin during app initialization
def init_default_admin():
    # Create a default college if none exists
    default_college = College.query.first()
    if not default_college:
        default_college = College(name='Administration')
        db.session.add(default_college)
        db.session.commit()
    
    # Create default admin user
    User.create_default_admin(default_college.id) 