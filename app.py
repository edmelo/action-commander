
from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'taskmanagersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_CHANGES'] = False
db = SQLAlchemy(app)

# Definição dos modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.title}>'

# Criar banco de dados se não existir
with app.app_context():
    db.create_all()

# Rotas
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Verificar se o usuário já existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Este email já está registrado. Por favor, faça login.', 'error')
            return redirect(url_for('login'))
        
        # Criar novo usuário
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registro realizado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Ocorreu um erro. Tente novamente.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f'Bem-vindo, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login falhou. Verifique seu email e senha.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar o dashboard.', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.date_created.desc()).all()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        flash('Por favor, faça login para adicionar tarefas.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date_str = request.form.get('due_date', '')
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Formato de data inválido. Use YYYY-MM-DD.', 'error')
                return redirect(url_for('add_task'))
        
        new_task = Task(
            title=title, 
            description=description, 
            due_date=due_date,
            user_id=session['user_id']
        )
        
        try:
            db.session.add(new_task)
            db.session.commit()
            flash('Tarefa adicionada com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        except:
            flash('Ocorreu um erro ao adicionar a tarefa.', 'error')
    
    return render_template('add_task.html')

@app.route('/edit_task/<int:id>', methods=['GET', 'POST'])
def edit_task(id):
    if 'user_id' not in session:
        flash('Por favor, faça login para editar tarefas.', 'error')
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(id)
    
    # Verificar se a tarefa pertence ao usuário atual
    if task.user_id != session['user_id']:
        flash('Você não tem permissão para editar esta tarefa.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        due_date_str = request.form.get('due_date', '')
        
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Formato de data inválido. Use YYYY-MM-DD.', 'error')
                return redirect(url_for('edit_task', id=id))
        else:
            task.due_date = None
        
        try:
            db.session.commit()
            flash('Tarefa atualizada com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        except:
            flash('Ocorreu um erro ao atualizar a tarefa.', 'error')
    
    # Formato da data para o input HTML
    due_date = ''
    if task.due_date:
        due_date = task.due_date.strftime('%Y-%m-%d')
    
    return render_template('edit_task.html', task=task, due_date=due_date)

@app.route('/delete_task/<int:id>')
def delete_task(id):
    if 'user_id' not in session:
        flash('Por favor, faça login para excluir tarefas.', 'error')
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(id)
    
    # Verificar se a tarefa pertence ao usuário atual
    if task.user_id != session['user_id']:
        flash('Você não tem permissão para excluir esta tarefa.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(task)
        db.session.commit()
        flash('Tarefa excluída com sucesso!', 'success')
    except:
        flash('Ocorreu um erro ao excluir a tarefa.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:id>')
def complete_task(id):
    if 'user_id' not in session:
        flash('Por favor, faça login para marcar tarefas como concluídas.', 'error')
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(id)
    
    # Verificar se a tarefa pertence ao usuário atual
    if task.user_id != session['user_id']:
        flash('Você não tem permissão para alterar esta tarefa.', 'error')
        return redirect(url_for('dashboard'))
    
    # Alternar o status de conclusão
    task.completed = not task.completed
    
    try:
        db.session.commit()
        status = 'concluída' if task.completed else 'pendente'
        flash(f'Tarefa marcada como {status}!', 'success')
    except:
        flash('Ocorreu um erro ao alterar o status da tarefa.', 'error')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
