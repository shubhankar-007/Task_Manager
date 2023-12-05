import click
import logging
from flask import Flask
from flask_pymongo import PyMongo
from bson import ObjectId

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/task_manager'
mongo = PyMongo(app)

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

@click.group()
def cli():
    pass

@cli.command("init_db")
def init_db():
    """Initialize the database with sample data."""
    sample_users = [
        {'username': 'admin', 'password': 'adminpass'},
        {'username': 'user1', 'password': 'user1pass'},
    ]

    sample_tasks = [
        {'_id': 1, 'title': 'Task 1', 'description': 'Description 1', 'status': 'Pending'},
        {'_id': 2, 'title': 'Task 2', 'description': 'Description 2', 'status': 'Completed'},
    ]

    with app.app_context():
        mongo.db.users.drop()
        mongo.db.tasks.drop()

        for user_data in sample_users:
            mongo.db.users.insert_one(user_data)

        for task_data in sample_tasks:
            mongo.db.tasks.insert_one(task_data)

    print('Initialized the database with sample data.')
    logging.info('Database initialized with sample data.')

@cli.command("register")
@click.option('--username', prompt='Enter your username', help='The username for registration.')
@click.option('--password', prompt='Enter your password', hide_input=True, help='The password for registration.')
def register(username, password):
    """Register a new user."""
    existing_user = mongo.db.users.find_one({'username': username})
    if existing_user:
        print('Username already exists. Please choose a different username.')
        logging.warning(f'Attempt to register with existing username: {username}')
        return

    user_data = {'username': username, 'password': password}
    mongo.db.users.insert_one(user_data)

    print('Registration successful.')
    logging.info(f'Registration successful for user: {username}')

@cli.command("login")
@click.option('--username', prompt='Enter your username', help='The username for login.')
@click.option('--password', prompt='Enter your password', hide_input=True, help='The password for login.')
def login(username, password):
    """Login to the application."""
    user = mongo.db.users.find_one({'username': username, 'password': password})
    if user:
        print('Login successful.')

        # Display notifications for pending tasks
        pending_tasks_data = mongo.db.tasks.find({'user_id': user['_id'], 'status': {'$regex': '^pending$', '$options': 'i'}})
        pending_tasks = [{'title': task['title'], 'description': task['description']} for task in pending_tasks_data]

        num_pending_tasks = len(pending_tasks)
        print(f'Number of pending tasks: {num_pending_tasks}')

        if num_pending_tasks > 0:
            print('Pending tasks:')
            for task in pending_tasks:
                print(f"- Title: {task['title']}, Description: {task['description']}")
        else:
            print('No pending tasks.')

        logging.info(f'User logged in successfully: {username}')
        logging.info(f'Number of pending tasks for {username}: {num_pending_tasks}')
    else:
        print('Invalid username or password.')
        logging.warning(f'Failed login attempt for username: {username}')


@cli.command("logout")
def logout():
    """Logout from the application."""
    print('Logout successful.')

@cli.command("get_tasks")
def get_tasks():
    """Get all tasks."""
    tasks_data = mongo.db.tasks.find()
    tasks = [{'_id': task['_id'], 'title': task['title'], 'description': task['description'], 'status': task['status']} for task in tasks_data]
    print(f'Tasks: {tasks}' if tasks else 'No tasks found.')

@cli.command("create_task")
@click.option('--title', prompt='Title', help='Task title')
@click.option('--description', prompt='Description', help='Task description')
@click.option('--status', prompt='Status', help='Task status')
@click.option('--username', prompt='Assign to username', help='Username to whom the task is assigned')
def create_task(title, description, status, username):
    """Create a new task."""
    user = mongo.db.users.find_one({'username': username})
    if not user:
        print(f'User with username "{username}" not found.')
        return

    task_id = int(mongo.db.tasks.find().sort('_id', -1).limit(1)[0]['_id']) + 1
    task_data = {'_id': task_id, 'title': title, 'description': description, 'status': status, 'user_id': user['_id']}
    mongo.db.tasks.insert_one(task_data)
    print('Task created successfully.')


@cli.command("update_task")
@click.argument('task_id', type=int)
@click.option('--title', prompt='Title', help='update Task title')
@click.option('--description', prompt='Description', help='update Task description')
@click.option('--status', prompt='Status', help='update Task status')
def update_task(task_id, title, description, status):
    """Update an existing task."""
    task = mongo.db.tasks.find_one({'_id': task_id})
    if not task:
        print('Task not found.')
        return

    update_fields = {}
    if title:
        update_fields['title'] = title
    if description:
        update_fields['description'] = description
    if status:
        update_fields['status'] = status

    mongo.db.tasks.update_one({'_id': task_id}, {'$set': update_fields})
    print('Task updated successfully.')

@cli.command("delete_task")
@click.argument('task_id', type=int)
def delete_task(task_id):
    """Delete an existing task."""
    task = mongo.db.tasks.find_one({'_id': task_id})
    if not task:
        print('Task not found.')
        return

    mongo.db.tasks.delete_one({'_id': task_id})
    print('Task deleted successfully.')

if __name__ == '__main__':
    cli()
