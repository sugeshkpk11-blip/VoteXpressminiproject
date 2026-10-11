# Online Voting System - Python Flask

## Requirements
- Python 3.10 or newer
- VS Code
- A web browser

## Run in VS Code

### Windows
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:
http://127.0.0.1:5000

## Default Admin
Username: admin
Password: admin123

Change the admin password and Flask secret key before using this beyond a classroom demo.

## Database
SQLite database `voting.db` is created automatically on first run.

## Project Modules
1. Voter Registration
2. Voter Authentication
3. Candidate Management
4. Vote Casting
5. Duplicate Vote Prevention
6. Result Calculation
7. Admin Dashboard
8. SQLite Database

This project is for educational/demo use. It is not suitable for conducting a real public election.


## Background image
The voting-themed background is included at `static/voting-background.jpg` and is applied across the website through `static/style.css`.
