# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based university timetable generator application with integrated Rasa chatbot functionality. The system helps students create optimized class schedules based on various constraints and preferences.

## Tech Stack

- **Backend**: Django 5.1.6 (Python)
- **Database**: MySQL
- **AI/ML**: Rasa 3.6.21 (chatbot), TensorFlow, OpenAI API integration
- **Real-time**: Socket.IO for chat functionality
- **Environment**: Python virtual environment (venv310)

## Key Commands

### Development Server
```bash
# Activate virtual environment
source venv310/bin/activate

# Run Django development server
python manage.py runserver

# Run database migrations
python manage.py makemigrations
python manage.py migrate
```

### Rasa Chatbot
```bash
# Run Rasa server and action server
./run_rasa.sh

# Retrain Rasa model
./retrain_rasa.sh
```

### Testing
```bash
# Run specific test files (examples)
python test_timetable_api.py
python test_graduation_system.py
python test_advanced_features.py
```

## Architecture

### Django Apps
- **config**: Main Django configuration and settings
- **home**: Core application with views for authentication, dashboard, timetable generation, chat, and reviews
- **data_manager**: Handles university data models (Universities, Colleges, Departments, Majors, Courses, etc.)
- **onboarding**: User onboarding flow

### Key Models (data_manager/models.py)
- University → College → Department → Major hierarchy
- Course: Contains course information including schedules, credits, and requirements
- UserCourse: Tracks user's course selections and completions
- GraduationRequirement: Defines graduation requirements by department/major
- Building: Campus building information for distance calculations

### Timetable Generation
The system uses OR-Tools (Google's optimization library) to generate optimal timetables based on:
- Course schedule conflicts
- Building distances between consecutive classes
- Credit requirements
- User preferences from surveys

### Chat System
- Real-time chat using Socket.IO (home/socketio_server.py)
- Messages stored in ChatMessage model
- Supports course-specific chat rooms

### Rasa Integration
- Located in /rasa directory
- Provides conversational AI for student assistance
- Custom actions defined for timetable-related queries
- Runs on ports 5005 (main) and 5055 (actions)

## Environment Variables
Required in .env file:
- KAKAO_API_KEY: For Kakao map integration
- OPENAI_API_KEY: For AI features
- Database credentials (if not using default)

## Important Files
- config/settings.py: Django settings and configuration
- home/views/timetable_views.py: Core timetable generation logic
- data_manager/models.py: Database schema definitions
- rasa/: Chatbot training data and configuration