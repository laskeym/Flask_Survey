import json

from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from wtforms import HiddenField, RadioField
from wtforms.widgets import HiddenInput


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'seekrets'
db = SQLAlchemy(app)


class AnswerForm(FlaskForm):
    page = HiddenField('page', default=1)
    survey_id = HiddenField('survey_id')
    question_id = HiddenField('question_id')
    answers = RadioField('Answers', choices=[])


class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_title = db.Column(db.String(40), unique=True, nullable=False)

    def __repr__(self):
        return '<Survey %r>' % self.survey_title


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


@app.route('/')
def home():
    surveys = Survey.query.all()

    return render_template('home.html', surveys=surveys)


@app.route('/survey/<int:survey_id>/questions', methods=['GET', 'POST'])
def survey_question(survey_id):
    survey = Survey.query.filter_by(id=survey_id).first()
    if survey is None:
        return '404 Page Not Found!'

    survey_id = survey_id
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
                           survey_id=survey_id,
                           choices=choices,
                           errors=errors,
                           page=page,
                           next_url=next_url,
                           prev_url=prev_url)


@app.route('/submit', methods=["POST"])
def submit():
    if request.method == "POST":
        survey_id = int(request.form['survey_id'])
        page = int(request.args.get('page', 1))
        form = AnswerForm(request.form)
        choices = QuestionChoices.query\
            .join(Question, QuestionChoices.question_id == Question.id)\
            .filter(QuestionChoices.question_id == form.question_id.data).all()

        form.answers.choices = [(choice.choice, choice.choice)
                                for choice in choices]
        if form.validate():
            url = url_for('survey_question', survey_id=survey_id, page=page+1)

            return redirect(url)

        url = url_for('survey_question', survey_id=survey_id,
                      page=page,
                      errors=form.errors)
        return redirect(url)
