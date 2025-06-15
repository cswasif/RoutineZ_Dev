# RoutineZ - Smart Course Routine Generator

<p align="center">
   <img src="assets/logo.png" alt="RoutineZ Logo" width="300" height="300"/>
</p>

<div align="center">
  <h3>🎓 The Smartest Way to Create Your University Schedule</h3>
  <p><strong>Live Demo:</strong> <a href="https://routinez.vercel.app">https://routinez.vercel.app</a></p>
</div>

## 🌟 Why RoutineZ?

RoutineZ is not just another course scheduler - it's your intelligent companion for creating the perfect university routine. Here's why students love it:

### 🤖 AI-Powered Scheduling
- **Smart Conflict Detection**: Automatically identifies and prevents class, lab, and exam conflicts
- **Personalized Recommendations**: Gets smarter with each use, suggesting better schedules based on your preferences
- **Real-time Feedback**: Provides instant analysis of your schedule quality with AI-powered insights

### 🎯 Student-Centric Features
- **Commute Optimization**: Choose schedules that match your commuting preferences (Live Far/Near)
- **Time Slot Flexibility**: Select preferred time slots for a better work-life balance
- **Faculty Selection**: Pick your favorite faculty members for each course
- **Exam Schedule Management**: View and manage mid-term and final exam schedules easily

### 💪 Powerful Benefits
- **Save Time**: Generate perfect routines in seconds, not hours
- **Avoid Conflicts**: Never worry about overlapping classes or exam dates
- **Better Planning**: Get a clear view of your semester schedule
- **Smart Gaps**: Optimize breaks between classes based on your preferences
- **Mobile Friendly**: Access your schedule anywhere, anytime

## 🚀 Getting Started

1. Visit [RoutineZ](https://routinez.vercel.app)
2. Select your courses
3. Choose preferred faculty and sections
4. Set your time preferences
5. Let AI generate your perfect routine!

## 🛠️ Technical Features

### Real-time Data Integration
RoutineZ uses the powerful [ConnAPI](https://connectlive-nine.vercel.app) to provide:
- Live course availability
- Up-to-date faculty information
- Real-time section data
- Accurate exam schedules

### Real-time Data Fetching Mechanism
Every interaction with RoutineZ guarantees the most current data:
- **Zero Caching**: No data is cached on the server - every request fetches fresh data
- **Direct API Integration**: Live connection to ConnAPI for real-time updates
- **Automatic Refresh**: Fresh data is fetched for:
  - Course listings
  - Section availability
  - Seat status
  - Exam schedules
  - Routine generation
- **Reliability Features**:
  - Multiple retry attempts on API calls
  - Connection status monitoring
  - Error handling and recovery
  - Timeout protection (30-second window)

### Advanced Algorithms
- **Smart Conflict Resolution**: Multi-layered conflict detection for classes, labs, and exams
- **Optimization Engine**: Considers multiple factors for the best possible schedule
- **AI Analysis**: Gemini AI integration for schedule quality assessment

### API Capabilities
The underlying API provides:
- Course information retrieval
- Section and faculty data
- Schedule validation
- Exam conflict checking
- AI-powered routine analysis

## 📱 Features Overview

### Core Features
- **Course Selection**: Easy-to-use interface for selecting multiple courses
- **Faculty Filtering**: Filter sections by preferred faculty members
- **Time Preferences**: Set preferred class times and days
- **Conflict Prevention**: Automatic detection of schedule conflicts
- **Exam Management**: View and manage examination schedules

### Smart Features
- **AI Feedback**: Get intelligent feedback on your routine
- **Schedule Rating**: AI-powered scoring of your schedule quality
- **Optimization Tips**: Receive suggestions for improving your routine
- **Commute Analysis**: Smart recommendations based on your location

### User Experience
- **Intuitive Interface**: Clean and easy-to-use design
- **Real-time Updates**: Instant feedback on schedule changes
- **Mobile Responsive**: Works perfectly on all devices
- **Fast Performance**: Quick routine generation and updates

## 🔧 Technical Stack

- **Frontend**: React.js with modern UI components
- **Backend**: Python Flask API with advanced scheduling algorithms
- **AI Integration**: Google Gemini AI for intelligent analysis
- **Data Source**: Real-time integration with ConnAPI
- **Hosting**: Vercel for optimal performance

## 📈 Why Choose RoutineZ?

1. **Time Efficiency**: Save hours of manual schedule planning
2. **Error Prevention**: Eliminate human error in schedule creation
3. **Smart Optimization**: Get the best possible schedule for your needs
4. **Real-time Data**: Always work with the latest course information - every single interaction fetches fresh data directly from BracU Connect
5. **AI-Powered**: Benefit from intelligent schedule analysis
6. **User-Friendly**: Easy to use for all students
7. **Mobile Ready**: Access your schedule anywhere

## 🤝 Support

For any questions or support:
- Visit our [live demo](https://routinez.vercel.app)
- Check the API status at [ConnAPI](https://connectlive-nine.vercel.app)
- Contact the development team through the application

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
Made with ❤️ for students by <a href="https://github.com/cswasif">Wasif Faisal</a>
</p>

## **Overview of the App**

RoutineZ is designed to simplify the course registration process by:
* Automatically generating conflict-free class schedules
* Checking for exam time conflicts
* Providing real-time seat availability information
* Offering AI-powered schedule optimization
* Supporting flexible time and day preferences

The app combines a powerful backend API with an intuitive frontend interface to make course planning effortless.

## **How the App Works**

1. **Course Selection**: Browse and select your desired courses from the available offerings
2. **Preference Setting**: Choose your preferred:
   * Days of the week
   * Time slots
   * Faculty members (optional)
   * Commute preferences (for AI optimization)
3. **Routine Generation**: The app will generate a conflict-free schedule based on your selections
4. **AI Optimization**: Optionally use AI to optimize your schedule for better time management

## **Key Features**

### **1. Course Management**

* View all available courses with seat availability
* Get detailed course information including sections and faculty
* Real-time updates of seat status
* Filter courses by various criteria

### **2. Schedule Generation**

* Automatic conflict detection for class times
* Exam schedule conflict checking
* Multiple schedule options when available
* Manual and AI-powered generation modes

### **3. AI Assistant**

* Get intelligent answers about your schedule
* Receive optimization suggestions
* Analyze potential conflicts
* Get commute-optimized schedules

## **API Endpoints**

### **Course Information**

#### **Get All Courses**
```http
GET /api/courses
```
Returns a list of all available courses with their codes, names, and seat availability.

#### **Get Course Details**
```http
GET /api/course_details?course={courseCode}
```
Returns detailed information about a specific course, including:
* Available sections
* Faculty members
* Seat availability
* Exam schedules

### **Routine Generation**

#### **Generate Routine**
```http
POST /api/routine
```
Generate a course routine based on preferences:

```json
{
  "courses": [
    {
      "course": "CSE101",
      "faculty": ["John Doe"],
      "sections": {
        "John Doe": "A"
      }
    }
  ],
  "days": ["SUNDAY", "TUESDAY"],
  "times": ["8:00 AM-9:20 AM", "9:30 AM-10:50 AM"],
  "useAI": true,
  "commutePreference": "balanced"
}
```

### **AI Features**

#### **Ask AI Assistant**
```http
POST /api/ask_ai
```
Get AI-powered answers about your schedule:
```json
{
  "question": "How can I optimize my schedule?",
  "routine": [/* Your current routine */]
}
```

#### **Check Exam Conflicts**
```http
POST /api/check_exam_conflicts_ai
```
Analyze potential exam conflicts in your schedule.

## **Getting Started**

### **1. Accessing the Application**
* Visit [https://routinez.vercel.app](https://routinez.vercel.app)
* No installation or login required
* Works on all modern browsers

### **2. Creating Your First Schedule**

1. Click "Generate Routine" on the homepage
2. Select your desired courses from the course list
3. Choose your preferred days and time slots
4. (Optional) Select specific faculty members
5. Choose between AI or manual generation
6. Click "Generate" to create your schedule

### **3. Using the AI Assistant**

1. Generate a routine first
2. Click on the AI Assistant button
3. Ask questions about your schedule
4. Get intelligent suggestions and analysis

## **Troubleshooting**

### **Common Issues**

* **No schedules generated**
  * Check if you've selected compatible time slots
  * Ensure courses have available seats
  * Try different day/time combinations

* **AI features not working**
  * Check your internet connection
  * Try refreshing the page
  * Clear browser cache

* **Seat availability issues**
  * Click refresh to get latest data
  * Check the API status indicator
  * Try again in a few minutes

## **Best Practices**

1. **Course Selection**
   * Start with required courses first
   * Keep alternative courses in mind
   * Check seat availability before planning

2. **Schedule Optimization**
   * Consider your commute time
   * Balance your daily course load
   * Leave gaps for breaks and study time

3. **Using AI Features**
   * Be specific with your questions
   * Provide context about your preferences
   * Review AI suggestions carefully

## **Updates and Support**

* The application is regularly updated with new features
* Clear your browser cache after updates
* For support, use the feedback form in the app

## **Contributing**

We welcome contributions! To contribute:
1. Fork the repository
2. Create your feature branch
3. Submit a pull request

For detailed contribution guidelines, see our [GitHub repository](https://github.com/cswasif/routinez_Latest).

## **License**

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## **Project Structure**

This project follows a standard structure suitable for Vercel deployment:

```
RoutinEZ/
├── api/                     # Contains Vercel Serverless Functions (Python)
│   ├── requirements.txt     # Python dependencies for serverless function
│   └── usisvercel.py        # Main backend serverless function (Flask application)
├── USIS/
│   └── usis-frontend/       # React frontend application
│       ├── public/          # Static assets
│       ├── src/             # Frontend source code
│       │   ├── components/  # Reusable React components
│       │   │   ├── ui/      # UI components (e.g., waves, grid)
│       │   │   └── ...      # Other components
│       │   ├── App.js       # Main application component and core logic
│       │   ├── App.css      # Main application styles
│       │   └── index.js     # Application entry point
│       └── package.json     # Frontend dependencies and scripts
├── .gitignore              # Specifies intentionally untracked files
├── LICENSE                 # Project license
├── README.md               # Project documentation (this file)
└── vercel.json             # Vercel configuration for routing serverless functions
```

## **Vercel Deployment**

This project is configured for easy deployment on Vercel. The `vercel.json` file at the root of the repository specifies how incoming requests are handled.

-   The `rewrites` rule in `vercel.json` routes all requests to `/api/*` to the `api/usisvercel.py` serverless function.
-   Vercel automatically detects the React application in the `USIS/usis-frontend` directory and builds/serves it as the frontend.

To deploy to Vercel:

1.  Push your changes to the `main` branch of your connected GitHub repository.
2.  Vercel will automatically detect the push and trigger a new build and deployment.
3.  Once the deployment is complete, your application will be live at your Vercel project URL.

### 🚨 Important: Clear Browser Cache After Deployment

After a new Vercel deployment, it is **highly recommended** to clear your browser's cache and cookies for the application's URL. This ensures that your browser loads the latest version of the frontend code, which is crucial for seeing recent changes and avoiding issues like outdated API endpoints being called.

## **Acknowledgements**

-   Based on the USIS course data structure.
-   Utilizes open-source libraries like React, Flask, Axios, date-fns, and html2canvas.

## **Contact**

For any questions, issues, or feedback, please open an issue on the GitHub repository.

## **Future Enhancements**

-   [ ] Dark mode support
-   [ ] Mobile responsiveness improvements
-   [ ] More advanced conflict resolution algorithms
-   [ ] Integration of course prerequisites checking
-   [ ] Analysis of GPA impact based on routine choices
-   [ ] Export routine to other formats (e.g., PDF, iCal)
-   [ ] Multi-language support

# USIS API Documentation

<p align="center">
  <img src="assets/logo.png" alt="RoutineZ Logo" width="150" height="150"/>
</p>

<h1 align="center">RoutineZ - Smart Course Scheduling</h1>

## Overview
The USIS API is a Flask-based backend service that provides course scheduling and routine generation functionality with AI assistance. It uses Google's Gemini AI for intelligent routine optimization and feedback.

## Core Features
- Course and section information retrieval
- AI-assisted routine generation
- Exam conflict detection
- Schedule compatibility checking
- Time slot management
- Lab schedule handling
- AI-powered routine feedback

## API Endpoints

### Course Management
- `GET /api/courses` - Get list of all available courses
- `GET /api/course_details` - Get detailed information about a specific course
- `GET /api/faculty` - Get list of all faculty members
- `GET /api/faculty_for_courses` - Get faculty members for specific courses
- `GET /api/exam_schedule` - Get exam schedule for a specific course section

### Routine Generation
- `POST /api/routine` - Generate a course routine with optional AI optimization
- `POST /api/ask_ai` - Get AI assistance for routine-related questions
- `POST /api/get_routine_feedback_ai` - Get AI feedback on a generated routine
- `POST /api/check_exam_conflicts_ai` - Check and analyze exam conflicts
- `POST /api/check_time_conflicts_ai` - Check and analyze time conflicts

## Key Functions

### Time Management
```python
class TimeUtils:
    @staticmethod
    def convert_to_bd_time(time_str)
    # Converts time string to Bangladesh timezone
    
    @staticmethod
    def time_to_minutes(tstr)
    # Converts time string to minutes (handles both 24-hour and 12-hour formats)
    
    @staticmethod
    def minutes_to_time(minutes)
    # Converts minutes to time string in 24-hour format (HH:MM:SS)
```

### Exam Conflict Management
```python
class ExamConflictChecker:
    @staticmethod
    def check_conflicts(sections)
    # Checks for conflicts between mid-term and final exams of sections
    
    @staticmethod
    def format_conflict_message(conflicts)
    # Formats exam conflicts message in a concise way
```

### Schedule Compatibility Functions
```python
def check_schedule_compatibility(schedule1, schedule2)
# Checks if two schedules are compatible (no time conflicts)

def is_valid_combination(sections)
# Checks if a combination of sections has any schedule conflicts

def filter_section_by_time(section, selected_times)
# Checks if section schedules fit within selected time ranges
```

### Lab Schedule Management
```python
def get_lab_schedule(section)
# Extracts and formats lab schedule information, supporting both array and nested object formats

def get_lab_schedules_flat(section)
# Normalizes labSchedules to a flat array of schedules
```

### AI Integration
```python
def try_ai_routine_generation(valid_combination, selected_days, selected_times, commute_preference)
# Generates AI-assisted routine using Gemini AI

def get_routine_feedback_for_api(routine, commute_preference=None)
# Gets AI feedback on a generated routine
```

### Scoring and Optimization
```python
def calculate_routine_score(combination, selected_days, selected_times, commute_preference)
# Calculates a score for a routine combination based on various factors

def calculate_campus_days(combination)
# Calculates the total number of unique days a student needs to be on campus
```

## Environment Setup
Required environment variables:
- `GOOGLE_API_KEY` - Google Gemini AI API key
- `