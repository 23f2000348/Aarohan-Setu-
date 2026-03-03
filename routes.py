from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db
from models import User, Company, Student, JobPosition, Application

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main.route('/terms')
def terms():
    return render_template('terms.html')

@main.route('/support')
def support():
    return render_template('support.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.status == 'Rejected' or user.status == 'Blacklisted':
                 flash('Your account has been suspended or rejected. Please contact admin.', 'danger')
                 return redirect(url_for('main.login'))
            
            if user.role == 'company' and user.company_profile.approval_status != 'Approved':
                 flash('Your account is pending approval by the administrator.', 'warning')
                 return redirect(url_for('main.login'))

            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
            
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(username=username, password_hash=hashed_password, role=role, status='Active')
        db.session.add(user)
        db.session.flush()  # get user.id

        if role == 'student':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            contact_number = request.form.get('contact_number')
            cgpa = request.form.get('cgpa')
            resume_link = request.form.get('resume_link')
            
            student = Student(user_id=user.id, full_name=full_name, email=email,
                              contact_number=contact_number, cgpa=cgpa, resume_link=resume_link)
            db.session.add(student)
            
        elif role == 'company':
            name = request.form.get('name')
            hr_contact = request.form.get('hr_contact')
            website = request.form.get('website')
            description = request.form.get('description')
            
            company = Company(user_id=user.id, name=name, hr_contact=hr_contact,
                              website=website, description=description, approval_status='Pending')
            db.session.add(company)
            flash('Registration successful! Please wait for admin approval.', 'info')
        
        else:
             flash('Invalid role selected.', 'danger')
             return redirect(url_for('main.register'))

        db.session.commit()
        if role == 'student':
            flash('Registration successful! You may now login.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@main.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        curr_students_count = Student.query.count()
        curr_companies_count = Company.query.count()
        curr_drives_count = JobPosition.query.count()
        curr_apps_count = Application.query.count()
        pending_companies = Company.query.filter_by(approval_status='Pending').all()
        pending_drives = JobPosition.query.filter_by(status='Pending').all()
        
        return render_template('dashboard_admin.html',
                               student_count=curr_students_count,
                               company_count=curr_companies_count,
                               drive_count=curr_drives_count,
                               app_count=curr_apps_count,
                               pending_companies=pending_companies,
                               pending_drives=pending_drives)

    elif current_user.role == 'company':
        my_drives = JobPosition.query.filter_by(company_id=current_user.company_profile.id).all()
        return render_template('dashboard_company.html', drives=my_drives)

    elif current_user.role == 'student':
        available_drives = JobPosition.query.filter_by(status='Approved').all()
        my_applications = Application.query.filter_by(student_id=current_user.student_profile.id).all()
        applied_drive_ids = [app.job_position_id for app in my_applications]
        return render_template('dashboard_student.html',
                               available_drives=available_drives,
                               my_applications=my_applications,
                               applied_drive_ids=applied_drive_ids)
    else:
        return redirect(url_for('main.home'))

# ─────────────────────────────────────────────
# Student Profile Update
# ─────────────────────────────────────────────
@main.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    student = current_user.student_profile

    if request.method == 'POST':
        student.full_name      = request.form.get('full_name', student.full_name)
        student.email          = request.form.get('email', student.email)
        student.contact_number = request.form.get('contact_number', student.contact_number)
        cgpa_str               = request.form.get('cgpa', '')
        if cgpa_str:
            try:
                student.cgpa = float(cgpa_str)
            except ValueError:
                flash('Invalid CGPA value.', 'danger')
                return redirect(url_for('main.update_profile'))
        student.resume_link = request.form.get('resume_link', student.resume_link)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('update_profile.html', student=student)

# ─────────────────────────────────────────────
# Admin: View All Students / Companies
# ─────────────────────────────────────────────
@main.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    q = request.args.get('q', '').strip()
    if q:
        # Search by name, contact, or student ID (user_id)
        students = Student.query.filter(
            db.or_(
                Student.full_name.ilike(f'%{q}%'),
                Student.contact_number.ilike(f'%{q}%'),
                Student.email.ilike(f'%{q}%'),
                Student.user_id == (int(q) if q.isdigit() else -1)
            )
        ).all()
    else:
        students = Student.query.all()
    return render_template('admin_students.html', students=students, q=q)

@main.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    q = request.args.get('q', '').strip()
    if q:
        companies = Company.query.filter(Company.name.ilike(f'%{q}%')).all()
    else:
        companies = Company.query.all()
    return render_template('admin_companies.html', companies=companies, q=q)

# ─────────────────────────────────────────────
# Admin: View All Drives
# ─────────────────────────────────────────────
@main.route('/admin/drives')
@login_required
def admin_drives():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    drives = JobPosition.query.order_by(JobPosition.created_at.desc()).all()
    return render_template('admin_drives.html', drives=drives)

# ─────────────────────────────────────────────
# Admin: View All Applications
# ─────────────────────────────────────────────
@main.route('/admin/applications')
@login_required
def admin_all_applications():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    applications = Application.query.order_by(Application.application_date.desc()).all()
    return render_template('admin_applications.html', applications=applications)

# ─────────────────────────────────────────────
# Admin: Blacklist / Deactivate / Reactivate User
# ─────────────────────────────────────────────
@main.route('/admin/set_user_status/<int:user_id>/<string:status>')
@login_required
def set_user_status(user_id, status):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    if status not in ('Active', 'Blacklisted', 'Rejected'):
        flash('Invalid status.', 'danger')
        return redirect(url_for('main.dashboard'))
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot change status of admin account.', 'danger')
        return redirect(url_for('main.dashboard'))
    user.status = status
    db.session.commit()
    label = 'Blacklisted' if status == 'Blacklisted' else ('Deactivated' if status == 'Rejected' else 'Reactivated')
    flash(f'Account {label} successfully.', 'success')
    # Redirect back to referrer (students or companies page)
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('main.dashboard'))

# ─────────────────────────────────────────────
# Drive Approval / Rejection
# ─────────────────────────────────────────────
@main.route('/approve_drive/<int:drive_id>')
@login_required
def approve_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    drive = JobPosition.query.get_or_404(drive_id)
    drive.status = 'Approved'
    db.session.commit()
    flash(f'Placement Drive "{drive.title}" has been approved.', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/reject_drive/<int:drive_id>')
@login_required
def reject_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    drive = JobPosition.query.get_or_404(drive_id)
    drive.status = 'Rejected'
    db.session.commit()
    flash(f'Placement Drive "{drive.title}" has been rejected.', 'warning')
    return redirect(url_for('main.dashboard'))

# ─────────────────────────────────────────────
# Company Approval / Rejection
# ─────────────────────────────────────────────
@main.route('/approve_company/<int:company_id>')
@login_required
def approve_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'Approved'
    db.session.commit()
    flash(f'Company "{company.name}" has been approved.', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/reject_company/<int:company_id>')
@login_required
def reject_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'Rejected'
    db.session.commit()
    flash(f'Company "{company.name}" has been rejected.', 'warning')
    return redirect(url_for('main.dashboard'))

# ─────────────────────────────────────────────
# Create Drive (Company)
# ─────────────────────────────────────────────
@main.route('/create_drive', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    if current_user.company_profile.approval_status != 'Approved':
        flash('You need admin approval to create drives.', 'warning')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        title                = request.form.get('job_title')
        job_description      = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        salary_range         = request.form.get('salary_range', '')
        deadline_str         = request.form.get('deadline')
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Invalid date format. Please pick a valid deadline.', 'danger')
            return redirect(url_for('main.create_drive'))

        drive = JobPosition(
            company_id=current_user.company_profile.id,
            title=title,
            job_description=job_description,
            eligibility_criteria=eligibility_criteria,
            salary_range=salary_range,
            deadline=deadline,
            status='Pending'
        )
        
        db.session.add(drive)
        db.session.commit()
        flash('Placement Drive created successfully! Waiting for admin approval.', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('create_drive.html')

# ─────────────────────────────────────────────
# Apply for a Drive (Student)
# ─────────────────────────────────────────────
@main.route('/apply_drive/<int:drive_id>')
@login_required
def apply_drive(drive_id):
    if current_user.role != 'student':
        flash('Only students can apply.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    drive = JobPosition.query.get_or_404(drive_id)
    if drive.status != 'Approved':
        flash('This drive is not open for applications.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    existing_app = Application.query.filter_by(
        student_id=current_user.student_profile.id,
        job_position_id=drive_id
    ).first()
    if existing_app:
        flash('You have already applied for this drive.', 'info')
        return redirect(url_for('main.dashboard'))
    
    application = Application(
        student_id=current_user.student_profile.id,
        job_position_id=drive_id
    )
    db.session.add(application)
    db.session.commit()
    flash(f'Successfully applied for {drive.title} at {drive.company.name}!', 'success')
    return redirect(url_for('main.dashboard'))

# ─────────────────────────────────────────────
# View / Manage Applicants (Company)
# ─────────────────────────────────────────────
@main.route('/view_applicants/<int:drive_id>')
@login_required
def view_applicants(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))
     
    drive = JobPosition.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))
     
    return render_template('view_applicants.html', drive=drive)

@main.route('/update_application/<int:app_id>/<string:status>')
@login_required
def update_application(app_id, status):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    application = Application.query.get_or_404(app_id)
    if application.job_position.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if status in ['Shortlisted', 'Selected', 'Rejected']:
        application.status = status
        db.session.commit()
        flash(f'Application status updated to {status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
        
    return redirect(url_for('main.view_applicants', drive_id=application.job_position_id))

# ─────────────────────────────────────────────
# Edit / Delete / Close Drive  (Company)
# ─────────────────────────────────────────────
@main.route('/edit_drive/<int:drive_id>', methods=['GET', 'POST'])
@login_required
def edit_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    drive = JobPosition.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        drive.title                = request.form.get('job_title', drive.title)
        drive.job_description      = request.form.get('job_description', drive.job_description)
        drive.eligibility_criteria = request.form.get('eligibility_criteria', drive.eligibility_criteria)
        drive.salary_range         = request.form.get('salary_range', drive.salary_range)
        deadline_str               = request.form.get('deadline', '')
        if deadline_str:
            try:
                drive.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            except (ValueError, TypeError):
                flash('Invalid date format.', 'danger')
                return redirect(url_for('main.edit_drive', drive_id=drive_id))
        # After editing, reset to Pending for re-approval
        drive.status = 'Pending'
        db.session.commit()
        flash('Drive updated successfully! It will need re-approval from admin.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('edit_drive.html', drive=drive)


@main.route('/delete_drive/<int:drive_id>')
@login_required
def delete_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    drive = JobPosition.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    db.session.delete(drive)
    db.session.commit()
    flash(f'Drive "{drive.title}" has been deleted.', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/close_drive/<int:drive_id>')
@login_required
def close_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    drive = JobPosition.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    drive.status = 'Closed'
    db.session.commit()
    flash(f'Drive "{drive.title}" has been closed. No further applications will be accepted.', 'info')
    return redirect(url_for('main.dashboard'))


# ─────────────────────────────────────────────
# Student: Placement History
# ─────────────────────────────────────────────
@main.route('/my_history')
@login_required
def student_history():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    all_applications = Application.query.filter_by(
        student_id=current_user.student_profile.id
    ).order_by(Application.application_date.desc()).all()

    return render_template('student_history.html', applications=all_applications)


# ─────────────────────────────────────────────
# Admin: Historical Placement Data
# ─────────────────────────────────────────────
@main.route('/admin/placements')
@login_required
def admin_placements():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    selected_apps = Application.query.filter_by(status='Selected').order_by(
        Application.application_date.desc()
    ).all()
    return render_template('admin_placements.html', placements=selected_apps)
