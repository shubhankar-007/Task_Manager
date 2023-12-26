import click
import logging
from flask import Flask, session
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from bson import ObjectId
from threading import Thread
import re
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/task_manager'
mongo = PyMongo(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_id, user_data['username'])
    return None

def init_db():

    if mongo.db.users.count_documents({}) == 0:
        sample_users = [
            {'username': 'admin', 'password': 'adminpass'},
            {'username': 'user1', 'password': 'user1pass'},
        ]

        sample_tasks = [
            {'_id': 1, 'title': 'Task 1', 'description': 'Description 1', 'status': 'Pending'},
            {'_id': 2, 'title': 'Task 2', 'description': 'Description 2', 'status': 'Completed'},
        ]

        for user_data in sample_users:
            mongo.db.users.insert_one(user_data)

        for task_data in sample_tasks:
            mongo.db.tasks.insert_one(task_data)

        click.echo('Initialized the database with sample data.')
        logging.info('Database initialized with sample data.')
    else:
        click.echo('Database already contains data. Skipping initialization.')


def login(username, password):
    user = mongo.db.users.find_one({'username': username, 'password': password})
    if user:
        mongo.db.sessions.update_one(
            {'user_id': user['_id']},
            {'$set': {'status': 1}},
            upsert=True
        )
        print('Login successful.')

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
        return True
    else:
        print('Invalid username or password.')
        logging.warning(f'Failed login attempt for username: {username}')
        return False



def register():
    username = input("Enter your desired username: ")
    password = input("Enter your desired password: ")

    existing_user = mongo.db.users.find_one({'username': username})
    if existing_user:
        print('Username already exists. Please choose a different username.')
        logging.warning(f'Attempt to register with existing username: {username}')
        return

    user_data = {'username': username, 'password': password}
    mongo.db.users.insert_one(user_data)

    print('Registration successful.')
    logging.info(f'Registration successful for user: {username}')




def logout(username):
    user = mongo.db.users.find_one({'username': username})
    if user:
        mongo.db.sessions.update_one(
            {'user_id': user['_id']},
            {'$set': {'status': 0}},
            upsert=True
        )
        print('Logout successful.')
        logging.info(f'User logged out successfully: {username}')
    else:
        print('User not found.')


def get_tasks(user_login_status):
    print("Available options for filtering:")
    print("1. Filter by Assigning User")
    print("2. Filter by Status")
    print("3. Filter by Due Date (Past due tasks first)")
    print("4. Show all tasks")

    filter_option = input("\nEnter your choice (1/2/3/4): ")

    filter_criteria = {}

    if filter_option == '1':
        assigning_username = user_login_status.get('username')
        if not assigning_username:
            print("You need to be logged in to filter by assigning user.")
            return
        filter_criteria['assigning_username'] = assigning_username

    elif filter_option == '2':
        filter_status_input = input('Enter task status to filter (leave empty for all): ')
        filter_status = re.compile(filter_status_input, re.IGNORECASE) if filter_status_input else None
        if filter_status:
            filter_criteria['status'] = {'$regex': filter_status}

    elif filter_option == '3':
        filter_criteria['due_date'] = {'$lte': str(datetime.now())}
    elif filter_option != '4':
        print("Invalid choice. Showing all tasks.")

    # Ask for sorting only when needed
    if filter_option not in {'3', '4'}:
        sort_option = input('Enter field to sort by (leave empty for default): ')
        tasks_data = mongo.db.tasks.find(filter_criteria).sort(sort_option) if sort_option else mongo.db.tasks.find(filter_criteria)
    else:
        tasks_data = mongo.db.tasks.find(filter_criteria)

    tasks = [{'_id': task['_id'], 'title': task['title'], 'description': task['description'], 'status': task['status'], 'due_date':task['due_date']} for task in tasks_data]
    print(f'Tasks: {tasks}' if tasks else 'No tasks found.')


def create_task(user_login_status):
    title = input('Enter task title: ')
    description = input('Enter task description: ')
    status = input('Enter task status: ')
    due_date = input('Enter due date (YYYY-MM-DD): ')
    if 'username' not in user_login_status:
        print("You need to log in before creating a task.")
        return

    assigned_username = input('Assign to username (leave empty for self): ')
    assigning_username = user_login_status['username']

    if not assigned_username:
        assigned_username = assigning_username

    task_id = int(mongo.db.tasks.find().sort('_id', -1).limit(1)[0]['_id']) + 1
    task_data = {
        '_id': task_id,
        'title': title,
        'description': description,
        'status': status,
        'due_date': due_date,
        'assigned_username': assigned_username,
        'assigning_username': assigning_username
    }

    mongo.db.tasks.insert_one(task_data)
    print('Task created successfully.')

def update_task():
    task_id = int(input('Enter task ID to update: '))
    status = input('Enter new task status: ')

    task = mongo.db.tasks.find_one({'_id': task_id})
    if not task:
        print('Task not found.')
        return

    update_fields = {'status': status}
    mongo.db.tasks.update_one({'_id': task_id}, {'$set': update_fields})
    print('Task updated successfully.')

def delete_task():
    task_id = int(input('Enter task ID to delete: '))

    task = mongo.db.tasks.find_one({'_id': task_id})
    if not task:
        print('Task not found.')
        return

    mongo.db.tasks.delete_one({'_id': task_id})
    print('Task deleted successfully.')

def run_app():
    with app.app_context():
        click.echo("Initializing the database with sample data...")
        init_db()
        click.echo("Database initialization complete.\n")

        user_login_status = {}

        while True:
            if 'username' in user_login_status:
                username = user_login_status['username']
                click.echo(f"\nLogged in as {username}.")
                click.echo("Available commands:")
                click.echo("1. logout")
                click.echo("2. get_tasks")
                click.echo("3. create_task")
                click.echo("4. update_task")
                click.echo("5. delete_task")
            else:
                click.echo("\nAvailable commands:")
                click.echo("1. login")
                click.echo("2. register")

            click.echo("6. exit")
            command = input("\nEnter command: ")

            if command == 'login':
                if 'username' not in user_login_status:
                    while True:
                        username = input("Enter your username: ")
                        password = input("Enter your password: ")
                        if login(username, password):
                            user_login_status['username'] = username
                            break
                        else:
                            retry = input("Invalid credentials. Retry? (yes/no): ")
                            if retry.lower() != 'yes':
                                break
                else:
                    click.echo("You are already logged in.")
            elif command == 'logout':
                if 'username' in user_login_status:
                    logout(user_login_status['username'])
                    user_login_status.pop('username')
                else:
                    click.echo("You are not logged in.")
            elif command == 'get_tasks':
                get_tasks(user_login_status)
            elif command == 'create_task':
                    create_task(user_login_status)
            elif command == 'update_task':
                update_task()
            elif command == 'delete_task':
                delete_task()
            elif command == 'register':
                if 'username' not in user_login_status:
                    register()
                else:
                    click.echo("You cannot register while logged in.")
            elif command == 'exit':
                break
            else:
                click.echo("Invalid command. Please try again.")

if __name__ == '__main__':
    run_app()