from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import app
from extensions import db
from models import User, Election, Position, Candidate, Vote, College, EligibleStudent, VoterList
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from sqlalchemy import and_
import csv
from io import TextIOWrapper, StringIO
import PyPDF2
import tempfile
from app.forms import LoginForm

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    elections = Election.query.filter_by(is_active=True).all()
    return render_template('index.html', elections=elections)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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
            
            # Clean the student ID to just digits for comparison
            clean_student_id = ''.join(c for c in student_id if c.isdigit())
            
            # Split into lines and check each line
            for line in text.split('\n'):
                # Extract all digits from the line
                line_digits = ''.join(c for c in line if c.isdigit())
                if clean_student_id in line_digits:
                    return True
                    
        except Exception as e:
            print(f"Error processing PDF {voter_list.filename}: {str(e)}")
            
        finally:
            # Clean up: Make sure the temp file is deleted
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"Error deleting temporary file: {str(e)}")
    
    return False

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        student_id = request.form.get('student_id')
        college_id = request.form.get('college')
        
        # Check if user already exists
        if User.query.filter_by(username=student_id).first():
            flash('Student ID already registered')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        # Check if student is in the voter list
        if not check_student_in_pdf(student_id, college_id):
            flash('You are not eligible to register. Your student number was not found in the voter list.')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(
            username=student_id,
            email=email,
            student_id=student_id,
            college_id=college_id,
            role='voter'
        )
        user.set_password(student_id)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now login using your Student ID as both username and password.')
        return redirect(url_for('login'))
        
    colleges = College.query.order_by(College.name).all()
    return render_template('register.html', colleges=colleges)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        elections = Election.query.all()
        return render_template('dashboard/admin.html', elections=elections)
    else:
        active_elections = Election.query.filter_by(is_active=True).all()
        return render_template('dashboard/voter.html', elections=active_elections)

@app.route('/election/<int:election_id>')
@login_required
def election(election_id):
    election = Election.query.get_or_404(election_id)
    
    # Check if election is active
    if not election.is_active:
        flash('This election is no longer active.', 'warning')
        return redirect(url_for('index'))
    
    # Check if user has already voted
    existing_votes = Vote.query.filter_by(
        user_id=current_user.id,
        election_id=election_id
    ).all()
    
    if existing_votes:
        flash('You have already voted in this election.', 'warning')
        return redirect(url_for('voting_history'))
    
    positions = Position.query.filter_by(election_id=election_id).all()
    
    # Filter candidates for representative positions based on voter's college
    for position in positions:
        if position.title.lower() == 'representative':
            # For representative positions, only show candidates from voter's college
            position.candidates = [candidate for candidate in position.candidates 
                                if candidate.college_id == current_user.college_id]
        else:
            # For other positions, show all candidates
            position.candidates = position.candidates
    
    return render_template('election.html', 
                         election=election, 
                         positions=positions)

@app.route('/election/<int:election_id>/confirm', methods=['GET', 'POST'])
@login_required
def confirm_vote(election_id):
    election = Election.query.get_or_404(election_id)
    
    # Check if user has already voted
    existing_votes = Vote.query.filter_by(
        user_id=current_user.id,
        election_id=election_id
    ).all()
    
    if existing_votes:
        flash('You have already voted in this election.', 'warning')
        return redirect(url_for('election', election_id=election_id))
    
    if request.method == 'POST':
        candidate_ids = request.form.getlist('candidate_ids')
        
        if not candidate_ids:
            flash('Please select at least one candidate.', 'error')
            return redirect(url_for('election', election_id=election_id))
        
        # Create votes
        try:
            for candidate_id in candidate_ids:
                vote = Vote(
                    user_id=current_user.id,
                    candidate_id=candidate_id,
                    election_id=election_id
                )
                db.session.add(vote)
            
            db.session.commit()
            flash('Your votes have been recorded successfully!', 'success')
            return redirect(url_for('voting_history'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording votes: {str(e)}', 'error')
            return redirect(url_for('election', election_id=election_id))
    
    # Get selected candidates from session
    selected_candidates = request.args.getlist('candidates')
    candidates = Candidate.query.filter(Candidate.id.in_(selected_candidates)).all()
    
    # Group candidates by position
    candidates_by_position = {}
    for candidate in candidates:
        if candidate.position_id not in candidates_by_position:
            candidates_by_position[candidate.position_id] = []
        candidates_by_position[candidate.position_id].append(candidate)
    
    return render_template('confirm_vote.html',
                         election=election,
                         candidates_by_position=candidates_by_position)

@app.route('/voting-history')
@login_required
def voting_history():
    # Get all elections the user has voted in
    elections = db.session.query(Election).join(Vote).filter(
        Vote.user_id == current_user.id
    ).distinct().all()
    
    # Get votes for each election
    voting_history = {}
    for election in elections:
        votes = Vote.query.filter_by(
            user_id=current_user.id,
            election_id=election.id
        ).all()
        
        # Group votes by position
        votes_by_position = {}
        for vote in votes:
            position = vote.candidate.position
            if position.id not in votes_by_position:
                votes_by_position[position.id] = {
                    'position': position,
                    'candidate': vote.candidate
                }
        
        if votes_by_position:  # Only add to history if there are votes
            voting_history[election.id] = {
                'election': election,
                'votes': votes_by_position
            }
    
    return render_template('voting_history.html', voting_history=voting_history)

# Admin routes
@app.route('/admin/election/create', methods=['GET', 'POST'])
@login_required
def create_election():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
        
        election = Election(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(election)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
        
    return render_template('admin/create_election.html')

@app.route('/admin/position/create', methods=['GET', 'POST'])
@login_required
def create_position():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        election_id = request.form.get('election_id')
        
        position = Position(
            title=title,
            description=description,
            election_id=election_id
        )
        
        db.session.add(position)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
        
    # Get active and recent elections (within last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    elections = Election.query.filter(
        (Election.is_active == True) | 
        (Election.end_date >= thirty_days_ago)
    ).order_by(Election.end_date.desc()).all()
    
    return render_template('admin/create_position.html', elections=elections)

@app.route('/admin/candidate/create', methods=['GET', 'POST'])
@login_required
def create_candidate():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        position_id = request.form.get('position_id')
        party_list = request.form.get('party_list')
        college_id = request.form.get('college_id')
        
        if not name or not position_id:
            flash('Name and position are required', 'error')
            return redirect(url_for('create_candidate'))
        
        # Check if position is representative
        position = Position.query.get(position_id)
        if position.title.lower() == 'representative' and not college_id:
            flash('College is required for representative positions', 'error')
            return redirect(url_for('create_candidate'))
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF', 'error')
                    return redirect(url_for('create_candidate'))
                
                try:
                    filename = secure_filename(file.filename)
                    # Add timestamp to filename to avoid collisions
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    image_path = filename
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')
                    return redirect(url_for('create_candidate'))
        
        try:
            candidate = Candidate(
                name=name,
                description=description,
                position_id=position_id,
                image_path=image_path,
                party_list=party_list,
                college_id=college_id if position.title.lower() == 'representative' else None
            )
            
            db.session.add(candidate)
            db.session.commit()
            flash('Candidate created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating candidate: {str(e)}', 'error')
            return redirect(url_for('create_candidate'))
    
    # Get active and recent elections (within last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    elections = Election.query.filter(
        (Election.is_active == True) | 
        (Election.end_date >= thirty_days_ago)
    ).order_by(Election.end_date.desc()).all()
    
    # Get all positions and colleges
    positions = Position.query.all()
    colleges = College.query.all()
    
    return render_template('admin/create_candidate.html', 
                         elections=elections,
                         positions=positions,
                         colleges=colleges)

@app.route('/candidate_images/<filename>')
def serve_candidate_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/election/<int:election_id>/results')
@login_required
def election_results(election_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    election = Election.query.get_or_404(election_id)
    positions = Position.query.filter_by(election_id=election_id).all()
    
    # Get results for each position
    results = {}
    total_voters = User.query.filter_by(role='voter').count()
    
    for position in positions:
        candidates = Candidate.query.filter_by(position_id=position.id).all()
        position_results = []
        
        for candidate in candidates:
            vote_count = Vote.query.filter_by(
                candidate_id=candidate.id,
                election_id=election_id
            ).count()
            
            # Calculate percentage
            percentage = (vote_count / total_voters * 100) if total_voters > 0 else 0
            
            position_results.append({
                'candidate': candidate,
                'vote_count': vote_count,
                'percentage': round(percentage, 2)
            })
        
        # Sort by vote count (descending)
        position_results.sort(key=lambda x: x['vote_count'], reverse=True)
        results[position.id] = position_results
    
    return render_template('admin/election_results.html',
                         election=election,
                         positions=positions,
                         results=results,
                         total_voters=total_voters)

@app.route('/admin/election/<int:election_id>/delete', methods=['POST'])
@login_required
def delete_election(election_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    election = Election.query.get_or_404(election_id)
    
    try:
        # First delete all votes associated with this election
        Vote.query.filter_by(election_id=election_id).delete()
        
        # Then delete all candidates for each position in this election
        for position in election.positions:
            # Delete votes for candidates in this position
            for candidate in position.candidates:
                Vote.query.filter_by(candidate_id=candidate.id).delete()
            # Delete candidates
            Candidate.query.filter_by(position_id=position.id).delete()
            
        # Now delete all positions
        Position.query.filter_by(election_id=election_id).delete()
        
        # Finally delete the election
        db.session.delete(election)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/users/import', methods=['GET', 'POST'])
@login_required
def import_users():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    colleges = College.query.all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('import_users'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('import_users'))
        
        college_id = request.form.get('college_id')
        if not college_id:
            flash('Please select a college', 'error')
            return redirect(url_for('import_users'))
        
        # Check if college exists
        college = College.query.get(college_id)
        if not college:
            flash('Selected college does not exist', 'error')
            return redirect(url_for('import_users'))
        
        try:
            # Store the PDF file
            voter_list = VoterList(
                filename=secure_filename(file.filename),
                data=file.read(),
                college_id=college_id
            )
            db.session.add(voter_list)
            db.session.commit()
            
            flash('Voter list uploaded successfully!', 'success')
            return redirect(url_for('import_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading file: {str(e)}', 'error')
            return redirect(url_for('import_users'))
    
    # Get existing voter lists
    voter_lists = VoterList.query.all()
    return render_template('admin/import_users.html', colleges=colleges, voter_lists=voter_lists)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the last admin
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        return jsonify({'success': False, 'message': 'Cannot delete the last admin user'}), 400
    
    try:
        # Delete all votes by this user
        Vote.query.filter_by(user_id=user_id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/election/<int:election_id>/reset', methods=['POST'])
@login_required
def reset_election_results(election_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    election = Election.query.get_or_404(election_id)
    
    try:
        # Delete all votes for this election
        Vote.query.filter_by(election_id=election_id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Election results reset successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/candidates')
@login_required
def manage_candidates():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    # Get filter parameters
    election_id = request.args.get('election_id', type=int)
    position_id = request.args.get('position_id', type=int)
    
    # Get all elections and positions for the filter dropdowns
    elections = Election.query.all()
    positions = Position.query.all()
    
    # Build the query
    query = Candidate.query.join(Position).join(Election)
    
    if election_id:
        query = query.filter(Election.id == election_id)
    if position_id:
        query = query.filter(Position.id == position_id)
        
    candidates = query.all()
    
    return render_template('admin/manage_candidates.html',
                         candidates=candidates,
                         elections=elections,
                         positions=positions,
                         selected_election_id=election_id,
                         selected_position_id=position_id)

@app.route('/admin/candidate/<int:candidate_id>/update-party-list', methods=['POST'])
@login_required
def update_candidate_party_list(candidate_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    candidate = Candidate.query.get_or_404(candidate_id)
    
    try:
        data = request.get_json()
        candidate.party_list = data.get('party_list')
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Party list updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/candidate/<int:candidate_id>/delete', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    candidate = Candidate.query.get_or_404(candidate_id)
    
    try:
        # Delete candidate's image if exists
        if candidate.image_path:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], candidate.image_path))
            except OSError:
                pass  # Ignore if file doesn't exist
                
        # Delete the candidate
        db.session.delete(candidate)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/candidate/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_candidate(candidate_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if request.method == 'POST':
        try:
            candidate.name = request.form.get('name')
            candidate.description = request.form.get('description')
            candidate.party_list = request.form.get('party_list')
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if not allowed_file(file.filename):
                        flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF', 'error')
                        return redirect(url_for('edit_candidate', candidate_id=candidate_id))
                    
                    try:
                        # Delete old image if exists
                        if candidate.image_path:
                            try:
                                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], candidate.image_path))
                            except OSError:
                                pass
                        
                        filename = secure_filename(file.filename)
                        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        candidate.image_path = filename
                    except Exception as e:
                        flash(f'Error uploading image: {str(e)}', 'error')
                        return redirect(url_for('edit_candidate', candidate_id=candidate_id))
            
            db.session.commit()
            flash('Candidate updated successfully!', 'success')
            return redirect(url_for('manage_candidates'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating candidate: {str(e)}', 'error')
            return redirect(url_for('edit_candidate', candidate_id=candidate_id))
    
    positions = Position.query.all()
    return render_template('admin/edit_candidate.html',
                         candidate=candidate,
                         positions=positions)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    elections = Election.query.all()
    positions = Position.query.all()
    candidates = Candidate.query.all()
    users = User.query.all()
    colleges = College.query.all()
    
    return render_template('dashboard/admin.html', 
                         elections=elections,
                         positions=positions,
                         candidates=candidates,
                         users=users,
                         colleges=colleges)

@app.route('/admin/colleges')
@login_required
def manage_colleges():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    colleges = College.query.all()
    return render_template('admin/manage_colleges.html', colleges=colleges)

@app.route('/admin/college/add', methods=['POST'])
@login_required
def add_college():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('College name is required.', 'danger')
        return redirect(url_for('manage_colleges'))
    
    college = College(name=name, description=description)
    db.session.add(college)
    db.session.commit()
    
    flash('College added successfully.', 'success')
    return redirect(url_for('manage_colleges'))

@app.route('/admin/college/<int:college_id>/edit', methods=['POST'])
@login_required
def edit_college(college_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    college = College.query.get_or_404(college_id)
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('College name is required.', 'danger')
        return redirect(url_for('manage_colleges'))
    
    college.name = name
    college.description = description
    db.session.commit()
    
    flash('College updated successfully.', 'success')
    return redirect(url_for('manage_colleges'))

@app.route('/admin/college/<int:college_id>/delete', methods=['POST'])
@login_required
def delete_college(college_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    college = College.query.get_or_404(college_id)
    
    # Check if there are any users or candidates associated with this college
    if college.users or college.candidates:
        return jsonify({
            'success': False,
            'message': 'Cannot delete college. There are users or candidates associated with it.'
        }), 400
    
    try:
        db.session.delete(college)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting college: {str(e)}'
        }), 500

@app.route('/admin/users/remove-all', methods=['POST'])
@login_required
def remove_all_users():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    try:
        # Delete all votes from non-admin users
        non_admin_users = User.query.filter(User.role != 'admin').all()
        for user in non_admin_users:
            Vote.query.filter_by(user_id=user.id).delete()
        
        # Delete all non-admin users
        User.query.filter(User.role != 'admin').delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All non-admin users have been removed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error removing users: {str(e)}'
        }), 500

@app.route('/admin/voters', methods=['GET'])
@login_required
def manage_voters():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    colleges = College.query.all()
    return render_template('admin/manage_voters.html', colleges=colleges)

@app.route('/admin/voters/upload', methods=['POST'])
@login_required
def upload_voter_list():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('manage_voters'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('manage_voters'))
    
    college_id = request.form.get('college_id')
    if not college_id:
        flash('Please select a college', 'error')
        return redirect(url_for('manage_voters'))
    
    # Check if college exists
    college = College.query.get(college_id)
    if not college:
        flash('Selected college does not exist', 'error')
        return redirect(url_for('manage_voters'))
    
    # Process the PDF file
    try:
        data = process_pdf_file(file)
        success_count = 0
        errors = []
        
        for record in data:
            try:
                # Check if student already exists in eligible students
                existing = EligibleStudent.query.filter(
                    EligibleStudent.student_id == record['Code']
                ).first()
                
                if existing:
                    errors.append(f"Student with ID '{record['Code']}' already exists")
                    continue
                
                # Create new eligible student
                student = EligibleStudent(
                    student_id=record['Code'],
                    last_name='Student',
                    first_name=str(record['Code']),
                    email=f"{record['Code']}@student.cspc.edu.ph",
                    college_id=college_id,
                    is_registered=False
                )
                
                db.session.add(student)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Error adding student with ID '{record['Code']}': {str(e)}")
        
        if success_count > 0:
            db.session.commit()
        
        results = {
            'success': success_count > 0,
            'message': f'Successfully imported {success_count} students.' + (f' {len(errors)} errors occurred.' if errors else ''),
            'errors': errors
        }
        
        return render_template('admin/manage_voters.html', 
                             colleges=College.query.all(),
                             results=results)
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('manage_voters'))

@app.route('/admin/voters/clear/<int:college_id>', methods=['GET'])
@login_required
def clear_voter_list(college_id):
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete all unregistered eligible students for the college
        EligibleStudent.query.filter_by(
            college_id=college_id,
            is_registered=False
        ).delete()
        
        db.session.commit()
        flash('Successfully cleared unregistered students from the list.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing list: {str(e)}', 'error')
    
    return redirect(url_for('manage_voters'))

@app.route('/admin/clear-eligible-students/<int:college_id>', methods=['POST'])
@login_required
def clear_eligible_students(college_id):
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete all unregistered eligible students for the college
        EligibleStudent.query.filter_by(
            college_id=college_id,
            is_registered=False
        ).delete()
        
        db.session.commit()
        flash('Successfully cleared unregistered students from the list.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing list: {str(e)}', 'error')
    
    return redirect(url_for('import_users'))

@app.route('/admin/remove-student-list/<int:college_id>', methods=['POST'])
@login_required
def remove_student_list(college_id):
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Get the college
        college = College.query.get_or_404(college_id)
        
        # Count registered users
        registered_count = EligibleStudent.query.filter_by(
            college_id=college_id,
            is_registered=True
        ).count()
        
        if registered_count > 0:
            # If there are registered users, show warning
            flash(f'Cannot remove list: {registered_count} students have already registered. Remove registered users first.', 'warning')
            return redirect(url_for('import_users'))
        
        # Delete all eligible students for the college
        EligibleStudent.query.filter_by(college_id=college_id).delete()
        
        db.session.commit()
        flash(f'Successfully removed all student records for {college.name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing list: {str(e)}', 'error')
    
    return redirect(url_for('import_users')) 