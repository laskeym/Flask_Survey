import json

from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse

from flask_wtf import FlaskForm, RecaptchaField
from wtforms import validators
from wtforms import HiddenField, RadioField, PasswordField, BooleanField,\
    SubmitField
from wtforms.fields.html5 import EmailField

from flask_login import LoginManager, UserMixin
from flask_login import current_user, login_user, logout_user, login_required


"""
THINGS TO DO:
    (X) Flask-Login integration
    (X) Add Answers model
    (\) Add HTML/CSS
    ( ) Move to PostgreSQL
    ( ) Reorganize code
    ( ) CRUD admin portal creation of new surveys
        ( ) jQuery UI - Sortable
        ( ) Will probably need AJAX to send over li value items.  If the user
            decides to change the value order, python can just order the
            list by ascending value order and create id's for them.
    ( ) Bokeh to display answer statistics by user
"""


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'seekrets'
app.config['RECAPTCHA_PUBLIC_KEY'] = '6LeYIbsSAAAAACRPIllxA7wvXjIE411PfdB2gt2J'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6LeYIbsSAAAAAJezaIq3Ft_hSTo0YtyeFG-JgRtu'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class LoginForm(FlaskForm):
    email = EmailField('Email Address',
                       [validators.DataRequired(),
                        validators.Email()])
    password = PasswordField('Password',
                             [validators.DataRequired()])
    remember_me = BooleanField('Remember Me')
    captcha = RecaptchaField()
    submit = SubmitField('Sign In')


class AnswerForm(FlaskForm):
    page = HiddenField('page')
    survey_id = HiddenField('survey_id')
    question_id = HiddenField('question_id')
    answers = RadioField('Answers', choices=[])


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Integer, unique=True)
    password = db.Column(db.String())

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_title = db.Column(db.String(40), unique=True, nullable=False)

    def __repr__(self):
        return '<Survey %r>' % self.survey_title


class SurveyComplete(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, primary_key=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'),
                          nullable=False)
    question = db.Column(db.String(75), nullable=False)

    def __repr(self):
        return '<Question %r>' % self.question


class QuestionChoices(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'),
                            nullable=False)
    choice = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<QuestionChoices %r>' % self.choice


class Answers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        nullable=False)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'),
                          nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    answer = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return '<Answers %r>' % self.answer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_required
@app.route('/')
def home():
    surveys = Survey.query\
        .outerjoin(SurveyComplete,
                   and_(Survey.id == SurveyComplete.survey_id,
                        SurveyComplete.user_id == current_user.get_id()))\
        .filter(SurveyComplete.user_id == None).all()

    return render_template('home.html', surveys=surveys)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            return redirect(url_for('home'))
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@login_required
@app.route('/survey/<int:survey_id>')
def survey_home(survey_id):
    survey = Survey.query.get(survey_id)

    is_complete = SurveyComplete.query\
        .filter_by(user_id=current_user.get_id(),
                   survey_id=survey.id).first()

    if is_complete:
        url = url_for('home')
        flash('You have already completed this survey!')

        return redirect(url)

    return render_template('survey.html',
                           survey=survey)


@login_required
@app.route('/survey/<int:survey_id>/questions', methods=['GET', 'POST'])
def survey_question(survey_id):
    survey = Survey.query.get(survey_id)
    if survey is None:
        return '404 Page Not Found!'

    is_complete = SurveyComplete.query\
        .filter_by(user_id=current_user.get_id(),
                   survey_id=survey.id).first()

    if is_complete:
        url = url_for('home')
        flash('You have already completed this survey!')

        return redirect(url)

    survey_id = survey.id
    page = request.args.get('page', 1, type=int)
    questions = Question.query.filter_by(survey_id=survey_id)\
        .order_by(Question.id)\
        .paginate(page, 1, True)

    for question in questions.items:
        question_id = question.id

    choices = QuestionChoices.query\
        .join(Question, QuestionChoices.question_id == Question.id)\
        .filter(QuestionChoices.question_id == question_id).all()

    form = AnswerForm()
    errors = request.args.get('errors', None)
    if errors:
        errors = errors.replace("'", "\"")
        errors = json.loads(errors)
    form.page.data = page
    form.survey_id.data = survey_id
    form.question_id.data = question_id
    form.answers.choices = [(choice.choice, choice.choice)
                            for choice in choices]

    next_url = url_for('survey_question', survey_id=survey_id,
                       page=questions.next_num)\
        if questions.has_next else None
    prev_url = url_for('survey_question', survey_id=survey_id,
                       page=questions.prev_num)\
        if questions.has_prev else None

    return render_template('survey_question.html',
                           form=form,
                           survey=survey,
                           question=questions.items,
                           choices=choices,
                           errors=errors,
                           page=page,
                           next_url=next_url,
                           prev_url=prev_url)


@login_required
@app.route('/success')
def success():
    return render_template('success.html')


@login_required
@app.route('/submit', methods=["POST"])
def submit():
    if request.method == "POST":
        survey_id = int(request.form['survey_id'])
        last_question = Question.query\
            .filter_by(survey_id=survey_id).count()

        form = AnswerForm(request.form)
        page = int(form.page.data)

        choices = QuestionChoices.query\
            .join(Question, QuestionChoices.question_id == Question.id)\
            .filter(QuestionChoices.question_id == form.question_id.data).all()

        form.answers.choices = [(choice.choice, choice.choice)
                                for choice in choices]
        if form.validate():
            answer = Answers(user_id=current_user.get_id(),
                             survey_id=survey_id,
                             question_id=form.question_id.data,
                             answer=form.answers.data)

            answer_exists = Answers.query\
                .filter_by(user_id=current_user.get_id(),
                           survey_id=form.survey_id.data,
                           question_id=form.question_id.data)\
                .first()
            if answer_exists:
                answer_exists.answer = answer.answer
            else:
                db.session.add(answer)

            db.session.commit()
            if page == last_question:
                is_complete = SurveyComplete(user_id=current_user.get_id(),
                                             survey_id=survey_id)
                db.session.add(is_complete)
                db.session.commit()

                url = url_for('success')
                return redirect(url)

            url = url_for('survey_question', survey_id=survey_id, page=page+1)

            return redirect(url)

        url = url_for('survey_question', survey_id=survey_id,
                      page=page,
                      errors=form.errors)
        return redirect(url)
