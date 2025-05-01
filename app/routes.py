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
import csv
from io import StringIO
from functools import wraps
import tempfile

bp = Blueprint('main', __name__)

def prevent_voting_after_completion(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user has already voted in this election
        election_id = kwargs.get('election_id')
        if election_id and f'voted_election_{election_id}' in session:
            flash('You have already completed voting in this election. You cannot modify your votes.', 'warning')
            return redirect(url_for('main.voting_complete', election_id=election_id))
        return f(*args, **kwargs)
    return decorated_function

def mark_voting_complete(election_id):
    """Mark that the user has completed voting in the specified election."""
    session[f'voted_election_{election_id}'] = True
    session.modified = True

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@bp.route('/')
def index():
    # Get elections that have candidates
    elections = Election.query.join(Position).join(Candidate).distinct().order_by(Election.start_date.desc()).all()
    # Only include party lists that have at least one candidate
    party_lists = [p for p in PartyList.query.all() if p.candidates]
    return render_template('index.html', elections=elections, party_lists=party_lists)

@bp.route('/election/<int:election_id>')
@login_required
@prevent_voting_after_completion
def election(election_id):
    election = Election.query.get_or_404(election_id)

    # Check if user has already voted in this election
    existing_vote = Vote.query.filter_by(user_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash('You have already cast your vote in this election.', 'warning')
        return redirect(url_for('main.voting_history'))

    # Get all positions for this election
    positions = Position.query.filter_by(election_id=election_id).all()
    filtered_positions = []
    candidates = {}

    for position in positions:
        # For representative positions, only show candidates from the same college
        if 'REPRESENTATIVE' in position.title.upper().strip():
            # Only get candidates from the user's college
            position_candidates = Candidate.query.filter_by(
                position_id=position.id,
                college_id=current_user.college_id
            ).all()
            # Only add the position if there are candidates from the user's college
            if position_candidates:
                candidates[position.id] = position_candidates
                filtered_positions.append(position)
        else:
            # For non-representative positions, show all candidates
            position_candidates = Candidate.query.filter_by(position_id=position.id).all()
            candidates[position.id] = position_candidates
            filtered_positions.append(position)

    return render_template('election.html',
                         election=election,
                         positions=filtered_positions,
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
        # Get the position to check if it's a representative position
        position = Position.query.get(form.position_id.data)
        is_representative = position and 'REPRESENTATIVE' in position.title.upper().strip()

        # Validate college_id for representative positions
        if is_representative:
            if not form.college_id.data:
                flash('College is required for representative positions.', 'danger')
                return redirect(url_for('main.add_candidate'))
            # Verify the college exists
            college = College.query.get(form.college_id.data)
            if not college:
                flash('Invalid college selected.', 'danger')
                return redirect(url_for('main.add_candidate'))

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
        # Get the position to check if it's a representative position
        position = Position.query.get(form.position_id.data)
        is_representative = position and 'REPRESENTATIVE' in position.title.upper().strip()

        # Validate college_id for representative positions
        if is_representative:
            if not form.college_id.data:
                flash('College is required for representative positions.', 'danger')
                return redirect(url_for('main.edit_candidate', id=id))
            # Verify the college exists
            college = College.query.get(form.college_id.data)
            if not college:
                flash('Invalid college selected.', 'danger')
                return redirect(url_for('main.edit_candidate', id=id))

        candidate.name = form.name.data
        candidate.description = form.description.data
        candidate.party_list_id = form.party_list.data
        candidate.position_id = form.position_id.data
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

        try:
            db.session.commit()
            flash('Candidate updated successfully!', 'success')
            return redirect(url_for('main.manage_candidates'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating candidate. Please try again.', 'danger')
            return redirect(url_for('main.edit_candidate', id=id))

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
        # Convert date to datetime with start of day for start_date and end of day for end_date
        start_datetime = datetime.combine(form.start_date.data, datetime.min.time())
        end_datetime = datetime.combine(form.end_date.data, datetime.max.time())
        
        election = Election(
            title=form.title.data,
            description=form.description.data,
            start_date=start_datetime,
            end_date=end_datetime,
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
    total_registered = User.query.filter_by(role='voter').count()

    for position in positions:
        # Get all votes for this position
        position_votes = Vote.query.filter_by(position_id=position.id).count()
        abstain_votes = Vote.query.filter_by(position_id=position.id, is_abstain=True).count()

        candidates = Candidate.query.filter_by(position_id=position.id).all()
        position_results = []
        is_representative = 'REPRESENTATIVE' in position.title.upper()

        # Add candidate results
        for candidate in candidates:
            votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            
            # Calculate percentage based on total registered voters
            percentage = (votes / total_registered * 100) if total_registered > 0 else 0

            result = {
                'candidate': candidate,
                'votes': votes,
                'percentage': percentage
            }

            # Add college-specific calculations for representative positions
            if is_representative and candidate.college:
                # Get total voters in the candidate's college
                total_college_voters = User.query.filter_by(
                    role='voter',
                    college_id=candidate.college_id
                ).count()

                # Get votes from the candidate's college
                college_votes = Vote.query.join(User).filter(
                    Vote.candidate_id == candidate.id,
                    User.college_id == candidate.college_id
                ).count()

                # Calculate college percentage
                college_percentage = (college_votes / total_college_voters * 100) if total_college_voters > 0 else 0

                result.update({
                    'college_votes': college_votes,
                    'total_college_voters': total_college_voters,
                    'college_percentage': college_percentage
                })

            position_results.append(result)

        # Add abstain results
        if abstain_votes > 0:
            percentage = (abstain_votes / total_registered * 100) if total_registered > 0 else 0
            
            position_results.append({
                'candidate': None,  # No candidate for abstain
                'votes': abstain_votes,
                'percentage': percentage,
                'is_abstain': True
            })

        # Sort by votes in descending order
        position_results.sort(key=lambda x: x['votes'], reverse=True)

        results.append({
            'position': position,
            'candidates': position_results,
            'total_votes': position_votes,
            'is_representative': is_representative
        })

        total_votes += position_votes

    return render_template('admin/election_results.html',
                         election=election,
                         positions=results,
                         total_votes=total_votes,
                         total_registered=total_registered)

@bp.route('/admin/elections/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_election(id):
    election = Election.query.get_or_404(id)

    if request.method == 'POST':
        election.title = request.form.get('title')
        election.description = request.form.get('description')
        # Parse dates and set start of day for start_date and end of day for end_date
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        election.start_date = datetime.combine(start_date, datetime.min.time())
        election.end_date = datetime.combine(end_date, datetime.max.time())
        election.is_active = request.form.get('is_active') == 'on'

        db.session.commit()
        flash('Election updated successfully!', 'success')
        return redirect(url_for('main.manage_elections'))

    return render_template('admin/edit_election.html', election=election)

@bp.route('/admin/elections/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_election(id):
    try:
        # Validate CSRF token
        try:
            validate_csrf(request.form.get('csrf_token'))
        except ValidationError:
            flash('Invalid CSRF token', 'danger')
            return redirect(url_for('main.manage_elections'))

        election = Election.query.get_or_404(id)

        try:
            # Start a transaction
            db.session.begin_nested()

            # First delete all votes
            Vote.query.filter_by(election_id=id).delete()

            # Delete all candidates associated with positions in this election
            for position in election.positions:
                Candidate.query.filter_by(position_id=position.id).delete()

            # Delete all positions
            Position.query.filter_by(election_id=id).delete()

            # Delete all audit logs for this election
            AuditLog.query.filter_by(election_id=id).delete()

            # Finally delete the election
            db.session.delete(election)

            # Create final audit log for deletion
            final_audit = AuditLog(
                user_id=current_user.id,
                action='DELETE_ELECTION',
                details=f'Election "{election.title}" deleted by admin: {current_user.username}',
                ip_address=request.remote_addr
            )
            db.session.add(final_audit)

            # Commit all changes
            db.session.commit()

            flash('Election deleted successfully.', 'success')
            return redirect(url_for('main.manage_elections'))
        except Exception as e:
            db.session.rollback()
            flash('Error deleting election: ' + str(e), 'danger')
            return redirect(url_for('main.manage_elections'))

    except Exception as e:
        flash('An unexpected error occurred.', 'danger')
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

def process_pdf_file(file):
    """Process a PDF file containing student information in a tabular format."""
    temp_file = None
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        file.save(temp_file.name)
        temp_file.close()

        # Read the PDF
        with open(temp_file.name, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            data = []
            
            # Process each page
            for page in pdf_reader.pages:
                text = page.extract_text()
                lines = text.split('\n')
                
                # Find header row and Code column index
                header_found = False
                code_column_index = -1
                
                for line in lines:
                    columns = line.split()
                    for i, col in enumerate(columns):
                        if col.upper() == 'CODE':
                            code_column_index = i
                            header_found = True
                            break
                    if header_found:
                        break
                
                if header_found and code_column_index >= 0:
                    # Process data rows
                    for line in lines:
                        columns = line.split()
                        if len(columns) > code_column_index:
                            code_value = columns[code_column_index].strip()
                            # Skip header row and empty values
                            if code_value != 'Code' and code_value:
                                data.append({'Code': code_value})

        return data

    except Exception as e:
        current_app.logger.error(f"Error processing PDF file: {str(e)}")
        raise e

    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                current_app.logger.error(f"Error deleting temporary file: {str(e)}")

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
            # Process the PDF file and extract student numbers
            student_data = process_pdf_file(file)
            
            if not student_data:
                flash('No valid student numbers found in the PDF file.', 'danger')
                return redirect(url_for('main.manage_user_lists'))

            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"

            # Use the USER_LISTS directory from config
            upload_dir = current_app.config['USER_LISTS']
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

            # Create UserList record
            user_list = UserList(
                filename=filename,
                file_path=file_path,
                college_id=college_id
            )

            db.session.add(user_list)
            
            # Create StudentNumber records for each student
            for student in student_data:
                student_number = StudentNumber(
                    student_id=student['Code'],
                    user_list=user_list
                )
                db.session.add(student_number)

            db.session.commit()
            flash(f'Enrollment list uploaded successfully! {len(student_data)} student numbers processed.', 'success')

        except Exception as e:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            current_app.logger.error(f"Error uploading enrollment list: {str(e)}")
            flash(f'Error uploading enrollment list: {str(e)}', 'danger')
            db.session.rollback()
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

    # Get the directory containing the file
    file_dir = os.path.dirname(user_list.file_path)

    # Ensure the directory exists
    if not os.path.exists(file_dir):
        os.makedirs(file_dir, exist_ok=True)

    # Check if file exists
    if not os.path.exists(user_list.file_path):
        flash('File not found on server.', 'danger')
        return redirect(url_for('main.manage_user_lists'))

    try:
        return send_file(
            user_list.file_path,
            as_attachment=True,
            download_name=user_list.filename
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading file: {str(e)}")
        flash('Error downloading file. Please try again.', 'danger')
        return redirect(url_for('main.manage_user_lists'))

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

        # Validate email domain
        if not email.endswith('@my.cspc.edu.ph'):
            flash('Only my.cspc.edu.ph email addresses are allowed', 'danger')
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

            # Log in the user automatically
            login_user(user)
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('main.index'))

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
            # Group votes by position for representative positions
            votes_by_position = {}
            for vote in votes:
                position_id = vote.position_id
                if position_id not in votes_by_position:
                    votes_by_position[position_id] = []
                votes_by_position[position_id].append(vote)

            voting_history[election.id] = {
                'election': election,
                'votes': votes,
                'votes_by_position': votes_by_position
            }

    return render_template('voting_history.html', voting_history=voting_history)

@bp.route('/election/<int:election_id>/confirm-vote', methods=['POST', 'GET'])
@login_required
@prevent_voting_after_completion
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
        votes = {}  # Dictionary to store position titles and their selections
        
        # Get all candidates in a single query to avoid multiple database hits
        candidates_dict = {}
        candidates = Candidate.query.filter(
            Candidate.position_id.in_([p.id for p in election.positions])
        ).options(
            db.joinedload(Candidate.college),
            db.joinedload(Candidate.party_list)
        ).all()
        for candidate in candidates:
            candidates_dict[candidate.id] = candidate

        for position in election.positions:
            if 'REPRESENTATIVE' in position.title.upper().strip():
                # For representative positions, get list of selected candidates
                vote_values = request.form.getlist(f'vote_{position.id}')
                if not vote_values:
                    flash(f'Please select at least one representative for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
                
                # Check if number of selections is valid (min 1, max 2)
                if len(vote_values) > 2:
                    flash(f'You can only select up to 2 representatives for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
                if len(vote_values) < 1:
                    flash(f'Please select at least one representative for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
                
                selections_list = []
                for vote_value in vote_values:
                    if vote_value == 'abstain':
                        selections_list.append('abstain')
                    else:
                        try:
                            candidate_id = int(vote_value)
                            candidate = candidates_dict.get(candidate_id)
                            if candidate:
                                selections_list.append(candidate)
                            else:
                                flash(f'Invalid candidate selected for {position.title}.', 'danger')
                                return redirect(url_for('main.election', election_id=election_id))
                        except ValueError:
                            flash(f'Invalid vote value for {position.title}.', 'danger')
                            return redirect(url_for('main.election', election_id=election_id))
                
                selections[str(position.id)] = vote_values
                votes[position.title] = selections_list
            else:
                # For other positions, get single selection
                vote_value = request.form.get(f'vote_{position.id}')
                if not vote_value:
                    flash(f'Please select a candidate or abstain for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
                
                # Convert vote value to actual candidate or 'abstain'
                if vote_value == 'abstain':
                    selection = 'abstain'
                else:
                    try:
                        candidate_id = int(vote_value)
                        candidate = candidates_dict.get(candidate_id)
                        if candidate:
                            selection = candidate
                        else:
                            flash(f'Invalid candidate selected for {position.title}.', 'danger')
                            return redirect(url_for('main.election', election_id=election_id))
                    except ValueError:
                        flash(f'Invalid vote value for {position.title}.', 'danger')
                        return redirect(url_for('main.election', election_id=election_id))
                
                selections[str(position.id)] = vote_value
                votes[position.title] = selection

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
            votes=votes,
            confirmation_code=confirmation_code
        )
    else:
        # GET: Show confirmation page if selections exist
        selections = session.get(f'vote_selections_{election_id}')
        if not selections:
            flash('No selections to confirm.', 'danger')
            return redirect(url_for('main.election', election_id=election_id))
        
        # Convert stored selections back to votes dictionary
        votes = {}
        candidates_dict = {}
        candidates = Candidate.query.filter(
            Candidate.position_id.in_([p.id for p in election.positions])
        ).options(
            db.joinedload(Candidate.college),
            db.joinedload(Candidate.party_list)
        ).all()
        for candidate in candidates:
            candidates_dict[candidate.id] = candidate

        for position in election.positions:
            position_selections = selections.get(str(position.id))
            if 'REPRESENTATIVE' in position.title.upper().strip():
                # Handle multiple selections for representatives
                selections_list = []
                for vote_value in (position_selections if isinstance(position_selections, list) else [position_selections]):
                    if vote_value == 'abstain':
                        selections_list.append('abstain')
                    else:
                        try:
                            candidate_id = int(vote_value)
                            candidate = candidates_dict.get(candidate_id)
                            if candidate:
                                selections_list.append(candidate)
                        except (ValueError, TypeError):
                            continue
                votes[position.title] = selections_list
            else:
                # Handle single selection for other positions
                if position_selections == 'abstain':
                    votes[position.title] = 'abstain'
                else:
                    try:
                        candidate_id = int(position_selections)
                        candidate = candidates_dict.get(candidate_id)
                        if candidate:
                            votes[position.title] = candidate
                    except (ValueError, TypeError):
                        continue

        return render_template('confirm_vote.html',
                             election=election,
                             votes=votes)

@bp.route('/election/<int:election_id>/cast-vote', methods=['POST'])
@login_required
@prevent_voting_after_completion
def cast_vote(election_id):
    # Validate CSRF token
    try:
        validate_csrf(request.form.get('csrf_token'))
    except ValidationError:
        flash('Invalid CSRF token. Please try again.', 'danger')
        return redirect(url_for('main.election', election_id=election_id))

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
    submitted_code = request.form.get('verification_code')
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
            position_id_str = str(position.id)
            is_representative = 'REPRESENTATIVE' in position.title.upper().strip()

            if is_representative:
                # Handle multiple selections for representative positions
                vote_values = selections.get(position_id_str, [])
                if not vote_values:
                    flash(f'Please select at least one representative for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))

                # Check if number of selections is valid (min 1, max 2)
                if len(vote_values) > 2:
                    flash(f'You can only select up to 2 representatives for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))
                if len(vote_values) < 1:
                    flash(f'Please select at least one representative for {position.title}.', 'danger')
                    return redirect(url_for('main.election', election_id=election_id))

                # Process each selection for representatives
                for vote_value in vote_values:
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

                            # Validate college for representative
                            if candidate.college_id != current_user.college_id:
                                flash(f'You can only vote for representatives from your college ({current_user.college.name}).', 'danger')
                                return redirect(url_for('main.election', election_id=election_id))

                            vote.candidate_id = candidate_id
                            vote.is_abstain = False
                            audit_details.append(f"Voted for {candidate.name} in position: {position.title}")
                        except ValueError:
                            flash(f'Invalid vote value for {position.title}.', 'danger')
                            return redirect(url_for('main.election', election_id=election_id))
                    votes_to_add.append(vote)
            else:
                # Handle single selection for other positions
                vote_value = selections.get(position_id_str)
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

        # After successfully processing votes, mark user as having voted
        current_user.has_voted = True
        db.session.commit()
        
        flash('Your votes have been successfully recorded!', 'success')
        return redirect(url_for('main.voting_complete'))

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

@bp.route('/admin/elections/<int:election_id>/export', methods=['GET'])
@login_required
@admin_required
def export_election_results(election_id):
    election = Election.query.get_or_404(election_id)
    positions = Position.query.filter_by(election_id=election_id).all()

    # Create a string buffer to write CSV data
    si = StringIO()
    writer = csv.writer(si)
    
    # Write headers
    writer.writerow(['Election:', election.title])
    writer.writerow(['Date Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow([]) # Empty row for spacing
    writer.writerow(['Position', 'Candidate', 'Party List', 'College', 'Votes', 'Percentage'])

    # Calculate and write results
    for position in positions:
        position_votes = Vote.query.filter_by(position_id=position.id).count()
        abstain_votes = Vote.query.filter_by(position_id=position.id, is_abstain=True).count()
        
        # Get all candidates and their votes
        candidates = Candidate.query.filter_by(position_id=position.id).all()
        results = []
        
        for candidate in candidates:
            votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            
            # Calculate percentage based on position type
            if 'REPRESENTATIVE' in position.title.upper():
                total_voters = User.query.filter_by(role='voter').count()
                percentage = (votes / (total_voters * 2) * 100) if total_voters > 0 else 0
            else:
                percentage = (votes / position_votes * 100) if position_votes > 0 else 0
            
            # Write candidate row
            writer.writerow([
                position.title,
                candidate.name,
                candidate.party_list.name if candidate.party_list else 'Independent',
                candidate.college.name if candidate.college else 'N/A',
                votes,
                f"{percentage:.2f}%"
            ])
            
        # Add abstain votes if any
        if abstain_votes > 0:
            if 'REPRESENTATIVE' in position.title.upper():
                total_voters = User.query.filter_by(role='voter').count()
                percentage = (abstain_votes / (total_voters * 2) * 100) if total_voters > 0 else 0
            else:
                percentage = (abstain_votes / position_votes * 100) if position_votes > 0 else 0
                
            writer.writerow([
                position.title,
                'ABSTAIN',
                'N/A',
                'N/A',
                abstain_votes,
                f"{percentage:.2f}%"
            ])
            
        # Add empty row between positions
        writer.writerow([])

    # Create the response
    output = si.getvalue()
    si.close()
    
    # Generate filename
    filename = f"{election.title.replace(' ', '_')}_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Create the response with CSV mimetype
    response = current_app.response_class(
        output,
        mimetype='text/csv',
        headers={
            "Content-Disposition": f"attachment;filename={filename}",
            "Content-Type": "text/csv"
        }
    )
    
    return response

@bp.route('/admin/elections/<int:election_id>/results/json')
@login_required
@admin_required
def election_results_json(election_id):
    election = Election.query.get_or_404(election_id)
    positions = Position.query.filter_by(election_id=election_id).all()

    # Calculate results
    results = {
        'total_votes': 0,
        'total_registered': User.query.filter_by(role='voter').count(),
        'positions': []
    }

    for position in positions:
        # Get all votes for this position
        position_votes = Vote.query.filter_by(position_id=position.id).count()
        abstain_votes = Vote.query.filter_by(position_id=position.id, is_abstain=True).count()

        candidates = Candidate.query.filter_by(position_id=position.id).all()
        position_results = {
            'position_id': position.id,
            'position_title': position.title,
            'total_votes': position_votes,
            'candidates': []
        }

        # Add candidate results
        for candidate in candidates:
            votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            
            # Calculate percentage based on total registered voters
            percentage = (votes / results['total_registered'] * 100) if results['total_registered'] > 0 else 0

            position_results['candidates'].append({
                'candidate_id': candidate.id,
                'candidate_name': candidate.name,
                'votes': votes,
                'percentage': round(percentage, 1)
            })

        # Add abstain results
        if abstain_votes > 0:
            percentage = (abstain_votes / results['total_registered'] * 100) if results['total_registered'] > 0 else 0
            
            position_results['candidates'].append({
                'candidate_id': None,
                'candidate_name': 'Abstain',
                'votes': abstain_votes,
                'percentage': round(percentage, 1),
                'is_abstain': True
            })

        # Sort by votes in descending order
        position_results['candidates'].sort(key=lambda x: x['votes'], reverse=True)
        
        results['positions'].append(position_results)
        results['total_votes'] += position_votes

    return jsonify(results)

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

from flask import url_for, jsonify

@bp.route('/party-list/<int:party_id>/candidates/json')
def party_list_candidates_json(party_id):
    party = PartyList.query.get_or_404(party_id)
    candidates = Candidate.query.filter_by(party_list_id=party_id).all()
    return jsonify([
        {
            'name': c.name,
            'position': c.position.title if c.position else '',
            'image_url': url_for('static', filename=c.image_path) if c.image_path else None,
            'description': c.description or ''
        }
        for c in candidates
    ])

@bp.route('/voting_complete')
@login_required
def voting_complete():
    # Check if user has any votes in the database
    has_votes = Vote.query.filter_by(user_id=current_user.id).first() is not None
    if not has_votes:
        return redirect(url_for('main.index'))
    return render_template('voting_complete.html')

def check_student_in_pdf(student_id, college_id):
    """Check if a student ID exists in any of the uploaded PDFs for the given college."""
    voter_lists = VoterList.query.filter_by(college_id=college_id).all()
    
    for voter_list in voter_lists:
        temp_file = None
        try:
            # Create a temporary file with a unique name
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(voter_list.data)
            temp_file.close()  # Close the file before reading
            
            # Read the PDF
            with open(temp_file.name, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ''
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text += page.extract_text()

                # Split into lines and process
                lines = text.split('\n')
                header_found = False
                code_column_index = -1

                # Find the header row and get the Code column index
                for line in lines:
                    columns = line.split()
                    for i, col in enumerate(columns):
                        if col.upper() == 'CODE':
                            code_column_index = i
                            header_found = True
                            break
                    if header_found:
                        break

                # If we found the Code column, process the data rows
                if header_found and code_column_index >= 0:
                    for line in lines:
                        columns = line.split()
                        if len(columns) > code_column_index:
                            code_value = columns[code_column_index].strip()
                            if code_value == student_id:
                                return True

                # Fallback: If header not found, try the old method
                if not header_found:
                    # Clean the student ID to just digits for comparison
                    clean_student_id = ''.join(c for c in student_id if c.isdigit())
                    
                    # Split into lines and check each line
                    for line in text.split('\n'):
                        # Extract all digits from the line
                        line_digits = ''.join(c for c in line if c.isdigit())
                        if clean_student_id in line_digits:
                            return True
                    
        except Exception as e:
            current_app.logger.error(f"Error processing PDF {voter_list.filename}: {str(e)}")
            
        finally:
            # Clean up: Make sure the temp file is deleted
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    current_app.logger.error(f"Error deleting temporary file: {str(e)}")
    
    return False

