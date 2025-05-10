from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from models import db, User, Question, Score
import os
import requests
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'laipiopa99'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = None
    today = datetime.now().date()
    if request.method == 'POST':
        city = request.form['city']
        API_KEY = os.getenv("WEATHER_KEY")
        BASE_URL = "http://api.openweathermap.org/data/2.5/forecast"
        
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        try:
            response = requests.get(BASE_URL, params=params)
            
            if response.status_code == 200:
                data = response.json()
                weather_data = {
                    'city': city,
                    'country': data['city']['country'],
                    'forecasts': []
                }
                
                yesterday = today - timedelta(days=1)
                tomorrow = today + timedelta(days=1)
                
                days = [yesterday, today, tomorrow]
                found_days = set()
                
                for item in data['list']:
                    date = datetime.fromtimestamp(item['dt']).date()
                    if date in days and date not in found_days:
                        found_days.add(date)
                        weather_data['forecasts'].append({
                            'date': date.strftime("%Y-%m-%d"),
                            'temp': round(item['main']['temp'], 2),
                            'feels_like': round(item['main']['feels_like'], 2),
                            'humidity': item['main']['humidity'],
                            'wind_speed': item['wind']['speed'],
                            'pressure': item['main']['pressure'],
                            'description': item['weather'][0]['description'],
                            'icon': item['weather'][0]['icon']
                        })
                
                weather_data['forecasts'].sort(key=lambda x: x['date'])
                
        except Exception as e:
            print(f"Error fetching weather data: {e}")

    if current_user.is_authenticated:
        scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.date.desc()).limit(5)
        return render_template('index.html', scores=scores, weather_data=weather_data, today=today.strftime("%Y-%m-%d"))
    return render_template('index.html', weather_data=weather_data, today=today.strftime("%Y-%m-%d"))


@app.route('/quiz')
@login_required
def quiz():
    rankings = db.session.query(
        User.username,
        db.func.max(Score.score).label('highest_score'),
        db.func.avg(Score.score).label('average_score'),
        db.func.count(Score.id).label('attempts')
    ).join(Score).group_by(User.id).order_by(db.desc('highest_score')).all()
    
    questions = Question.query.all()
    return render_template('quiz.html', questions=questions, rankings=rankings)


@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    score = 0
    questions = Question.query.all()
    
    for question in questions:
        answered = request.form.get(str(question.id))
        if answered and int(answered) == question.correct_answer:
            score += 1
    
    new_score = Score(
        score=score,
        date=datetime.now(),
        user_id=current_user.id
    )
    db.session.add(new_score)
    db.session.commit()
    
    return render_template('result.html', score=score, total=len(questions))

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('instance/quiz.db'):
        init_db()
    app.run(debug=True)