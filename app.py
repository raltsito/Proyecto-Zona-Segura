from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
import requests
from requests.exceptions import JSONDecodeError
import logging
from flask import current_app
import time
from requests.exceptions import RequestException
import urllib.parse
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos de Base de Datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SafeZone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Crear tablas (ejecutar solo una vez)
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
            
        return 'Credenciales inválidas'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            return 'Usuario ya existe'
            
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    zones = SafeZone.query.all()
    return render_template('dashboard.html', zones=zones)

@app.route('/add-zone', methods=['GET', 'POST'])
@login_required
def add_zone():
    if request.method == 'POST':
        new_zone = SafeZone(
            name=request.form['name'],
            latitude=request.form['latitude'],
            longitude=request.form['longitude'],
            description=request.form['description'],
            user_id=current_user.id
        )
        db.session.add(new_zone)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_zone.html')

@app.route('/routes')
@login_required
def routes():
    return render_template('routes.html')

def fetch_with_retries(url, retries=3, timeout=10, backoff_factor=2):
    for attempt in range(1, retries+1):
        try:
            return requests.get(url, timeout=timeout)
        except RequestException as e:
            if attempt == retries:
                raise
            sleep_time = backoff_factor ** (attempt - 1)
            time.sleep(sleep_time)

ORS_API_KEY = '5b3ce3597851110001cf6248491af9c730e74f599a3190748672deb8'

@app.route('/get_safe_route', methods=['POST'])
def get_safe_route():
    data = request.get_json()
    coords = [
        [data['start_lon'], data['start_lat']],
        [data['end_lon'],   data['end_lat']]
    ]
    body = {
        "coordinates": coords,
        "instructions": False
    }
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }

    resp = requests.post(
        'https://api.openrouteservice.org/v2/directions/driving-car',
        json=body, headers=headers, timeout=10
    )
    if not resp.ok:
        current_app.logger.error(f"ORS status {resp.status_code}: {resp.text}")
        return jsonify({
            'route': None,
            'safe_zones': [],
            'error': f"Error de ruteo ({resp.status_code})"
        }), 502

    ors_data = resp.json()

    if 'features' in ors_data and isinstance(ors_data['features'], list) and ors_data['features']:
        geom = ors_data['features'][0].get('geometry')
    elif 'routes' in ors_data and isinstance(ors_data['routes'], list) and ors_data['routes']:
        geom = ors_data['routes'][0].get('geometry')
    else:
        current_app.logger.error(f"Respuesta inesperada de ORS: {ors_data}")
        return jsonify({
            'route': None,
            'safe_zones': [],
            'error': 'Respuesta inesperada de ruteo'
        }), 502

    if not geom:
        current_app.logger.error(f"No se encontró geometría en la respuesta: {ors_data}")
        return jsonify({
            'route': None,
            'safe_zones': [],
            'error': 'No hay geometría en la ruta'
        }), 502

    safe_zones = SafeZone.query.filter(
        SafeZone.latitude.between(data['start_lat']-0.05, data['start_lat']+0.05),
        SafeZone.longitude.between(data['start_lon']-0.05, data['start_lon']+0.05)
    ).all()

    return jsonify({
        'route': { 'routes': [{ 'geometry': geom }] },
        'safe_zones': [
            {'lat': z.latitude, 'lon': z.longitude, 'name': z.name}
            for z in safe_zones
        ]
    })

@app.route('/report-incident', methods=['GET', 'POST'])
def report_incident():
    if request.method == 'POST':
        incident_type = request.form['type']
        address = request.form['address']
        description = request.form.get('description', '')

        new_incident = Incident(
            type=incident_type,
            address=address,
            description=description
        )
        
        db.session.add(new_incident)
        db.session.commit()
        
        flash('¡Reporte guardado con éxito!', 'success')
        return redirect(url_for('report_incident'))

    incidents = Incident.query.order_by(Incident.created_at.desc()).all()
    return render_template('report.html', incidents=incidents)



if __name__ == '__main__':
    app.run(debug=True)