from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime


# User Loader

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# User (base auth table for all roles)

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(10), nullable=False)   # 'admin' | 'company' | 'student'
    status        = db.Column(db.String(20), default='Active', nullable=False)
                                                                # 'Active' | 'Rejected' | 'Blacklisted'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    admin_profile   = db.relationship('Admin',   backref='user', uselist=False, lazy=True,
                                      cascade='all, delete-orphan')
    company_profile = db.relationship('Company', backref='user', uselist=False, lazy=True,
                                      cascade='all, delete-orphan')
    student_profile = db.relationship('Student', backref='user', uselist=False, lazy=True,
                                      cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User '{self.username}' role='{self.role}'>"


class Admin(db.Model):
    __tablename__ = 'admin'

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    email   = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f"<Admin user_id={self.user_id}>"



# Company

class Company(db.Model):
    __tablename__ = 'company'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    name            = db.Column(db.String(150), nullable=False)
    hr_contact      = db.Column(db.String(100), nullable=False)
    website         = db.Column(db.String(150), nullable=True)
    description     = db.Column(db.Text, nullable=True)
    approval_status = db.Column(db.String(20), default='Pending', nullable=False)
                                # 'Pending' | 'Approved' | 'Rejected'
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    job_positions = db.relationship('JobPosition', backref='company', lazy=True,
                                    cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Company '{self.name}' status='{self.approval_status}'>"



# Student / Job Seeker

class Student(db.Model):
    __tablename__ = 'student'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    full_name      = db.Column(db.String(150), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    contact_number = db.Column(db.String(20), nullable=True)
    cgpa           = db.Column(db.Float, nullable=True)
    resume_link    = db.Column(db.String(300), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    applications = db.relationship('Application', backref='student', lazy=True,
                                   cascade='all, delete-orphan')
    placements   = db.relationship('Placement',   backref='student', lazy=True)

    def __repr__(self):
        return f"<Student '{self.full_name}'>"



# Job Position (posted by Company)

class JobPosition(db.Model):
    __tablename__ = 'job_position'

    id                   = db.Column(db.Integer, primary_key=True)
    company_id           = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    title                = db.Column(db.String(150), nullable=False)
    job_description      = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=True)
    salary_range         = db.Column(db.String(100), nullable=True)
    deadline             = db.Column(db.DateTime, nullable=False)
    status               = db.Column(db.String(20), default='Pending', nullable=False 
    created_at           = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    applications = db.relationship('Application', backref='job_position', lazy=True,
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f"<JobPosition '{self.title}' status='{self.status}'>"



# Application  (Student → JobPosition)

class Application(db.Model):
    __tablename__ = 'application'

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    job_position_id  = db.Column(db.Integer, db.ForeignKey('job_position.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status           = db.Column(db.String(20), default='Applied', nullable=False)



    placement = db.relationship('Placement', backref='application', uselist=False, lazy=True,
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Application student={self.student_id} job={self.job_position_id} status='{self.status}'>"



# Placement  (final result when student is Selected)

class Placement(db.Model):
    __tablename__ = 'placement'

    id                = db.Column(db.Integer, primary_key=True)
    application_id    = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False, unique=True)
    student_id        = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    company_id        = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_position_id   = db.Column(db.Integer, db.ForeignKey('job_position.id'), nullable=False)
    offer_date        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    package_lpa       = db.Column(db.Float, nullable=True)
    offer_letter_url  = db.Column(db.String(300), nullable=True)

    # Back-references to Company and JobPosition
    company      = db.relationship('Company',     foreign_keys=[company_id],      lazy=True)
    job_position = db.relationship('JobPosition', foreign_keys=[job_position_id], lazy=True)

    def __repr__(self):
        return f"<Placement student={self.student_id} company={self.company_id} package={self.package_lpa}>"
