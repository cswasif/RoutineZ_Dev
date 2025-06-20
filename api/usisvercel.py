import requests
from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
import re
from datetime import datetime, timezone, timedelta
import json
import pytz
import demjson3
import json as pyjson
import os
from itertools import product
import time
import traceback
import logging
import itertools
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Global debug flag - set to True for development, False for production
DEBUG = False

def debugprint(*args, **kwargs):
    """Print debug messages only when DEBUG is True"""
    if DEBUG:
        print(*args, **kwargs)

debugprint("\n=== Loading Environment Variables ===")
# Debug: Print all environment variables
debugprint("Available environment variables:", list(os.environ.keys()))

# Hardcoded Google API key
GOOGLE_API_KEY = "AIzaSyC9fjJ5afylqK_RzxAWUwI1Y9yN06BJCI0"
debugprint("Using hardcoded GOOGLE_API_KEY")
debugprint("✓ GOOGLE_API_KEY is set and has a value")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Disable Flask's default access logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configure Gemini API
gemini_configured = False
try:
    debugprint("\n=== Configuring Gemini API ===")
    genai.configure(api_key=GOOGLE_API_KEY)
    debugprint("✓ genai.configure called with API key")
    # Create a single model instance to be reused
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    debugprint("✓ GenerativeModel instance created")
    debugprint("Gemini API configured with shared model instance.")
    gemini_configured = True
    debugprint("✓ Gemini API configured successfully")
except ImportError as ie:
    print(f"✗ ImportError configuring Gemini: {ie}")
    print("✗ Warning: google.generativeai package not installed. AI features will be disabled.")
except Exception as e:
    print(f"✗ Failed to configure Gemini API: {str(e)}")
    print(f"Error type: {type(e)}")
    gemini_model = None

def check_ai_availability():
    """Check if AI features are available."""
    debugprint("\n=== Checking AI Availability ===")
    if not GOOGLE_API_KEY:
        debugprint("✗ Google API key not configured")
        return False, "Google API key not configured"
    if not gemini_model:
        debugprint("✗ Gemini API not properly configured")
        return False, "Gemini API not properly configured"
    debugprint("✓ AI features available")
    return True, "AI features available"

@app.route("/api/connapi-status")
def check_connapi_status():
    try:
        response = requests.get("https://connect-api-lab-fix.vercel.app/raw-schedule", timeout=30)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        data = response.json()
        
        return jsonify({
            "status": "online",
            "cached": data.get("cached", True),
            "message": "API is online and responding"
        })
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "cached": True,
            "error": "Connection timed out. Please try again later."
        }), 503
    except requests.exceptions.RequestException as e:
        print(f"Error checking ConnAPI status: {e}")
        return jsonify({
            "status": "error",
            "cached": True,
            "error": "Unable to connect to the API. Please try again later."
        }), 503
    except Exception as e:
        print(f"Unexpected error checking ConnAPI status: {e}")
        return jsonify({
            "status": "error",
            "cached": True,
            "error": "An unexpected error occurred. Please try again later."
        }), 503

@app.route("/api/test")
def test():
    env_vars = list(os.environ.keys())
    api_key = os.environ.get("GOOGLE_API_KEY")
    return jsonify({
        "status": "ok",
        "environment": {
            "has_api_key": bool(api_key),
            "api_key_length": len(api_key) if api_key else 0,
            "available_vars": env_vars
        }
    })

@app.route("/api/courses")
def get_courses():
    try:
        # Get show_all parameter from query string, default to False
        show_all = request.args.get("show_all", "false").lower() == "true"
        
        data = load_data()  # Load data directly in the route
        if data is None:
            return jsonify({"error": "Failed to load course data. Please try again later."}), 503
            
        courses_data = {}
        for section in data:
            code = section.get("courseCode")
            name = section.get("courseName", code)
            available_seats = section.get("capacity", 0) - section.get("consumedSeat", 0)
            
            # Always process the course and include it in the response
            if code not in courses_data:
                courses_data[code] = {
                    "code": code, 
                    "name": name, 
                    "totalAvailableSeats": 0,
                    "hasAvailableSeats": False  # Add flag to indicate if course has any seats
                }
            courses_data[code]["totalAvailableSeats"] += available_seats
            if available_seats > 0:
                courses_data[code]["hasAvailableSeats"] = True
                
        courses_list = list(courses_data.values())
        return jsonify(courses_list)
    except Exception as e:
        print(f"Error in /api/courses: {e}")
        return jsonify({"error": "Failed to process courses data. Please try again later."}), 503


# Initialize data as None
data = None

def load_data():
    try:
        DATA_URL = "https://connect-api-lab-fix.vercel.app/raw-schedule"  # Using Vercel deployment
        debugprint(f"\n=== Loading Fresh Data from {DATA_URL} ===")
        
        # Add retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                debugprint(f"Attempt {attempt + 1}/{max_retries}...")
                response = requests.get(DATA_URL, timeout=30)  # Increased timeout
                response.raise_for_status()
                raw_json = response.json()
                
                debugprint(f"Raw response type: {type(raw_json)}")
                
                # Handle both direct list and {data: [...]} formats
                if isinstance(raw_json, dict) and "data" in raw_json:
                    debugprint("Response is a dict with 'data' key")
                    fresh_data = raw_json["data"]
                else:
                    debugprint("Response is a direct list")
                    fresh_data = raw_json  # If it's already a list
                
                if not isinstance(fresh_data, list):
                    debugprint(f"Warning: Expected list data, got {type(fresh_data)}")
                    continue
                
                # Count sections by course
                course_counts = {}
                for section in fresh_data:
                    course = section.get("courseCode")
                    if course:
                        course_counts[course] = course_counts.get(course, 0) + 1
                
                debugprint(f"Successfully loaded {len(fresh_data)} total sections")
                debugprint("Sections per course:")
                for course, count in sorted(course_counts.items()):
                    debugprint(f"  {course}: {count} sections")
                
                return fresh_data
            except requests.exceptions.RequestException as e:
                debugprint(f"Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    time.sleep(retry_delay)
            except json.JSONDecodeError as e:
                debugprint(f"JSON decode error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        debugprint("All retry attempts failed")
        return None
    except Exception as e:
        debugprint(f"Critical error in load_data: {e}")
        return None


# Add at the top of usis.py
BD_TIMEZONE = pytz.timezone("Asia/Dhaka")


# Create TimeUtils class
class TimeUtils:
    @staticmethod
    def convert_to_bd_time(time_str):
        """Convert time string to Bangladesh timezone."""
        debugprint(f"Converting time to Bangladesh timezone: {time_str}")
        try:
            time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
            dt = datetime.now().replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=time_obj.second,
                microsecond=0,
            )
            bd_dt = BD_TIMEZONE.localize(dt)
            result = bd_dt.strftime("%H:%M:%S")
            debugprint(f"Converted {time_str} to Bangladesh time: {result}")
            return result
        except Exception as e:
            debugprint(f"Error converting time to Bangladesh timezone: {e}")
            return time_str

    @staticmethod
    def time_to_minutes(tstr):
        """Convert time string to minutes (handles both 24-hour and 12-hour formats)."""
        if not tstr:
            debugprint(f"Warning: Empty time string")
            return 0

        tstr = tstr.strip().upper()
        debugprint(f"Converting time to minutes: {tstr}")

        try:
            if "AM" in tstr or "PM" in tstr:
                if ":" not in tstr:
                    tstr = tstr.replace(" ", ":00 ")
                tstr = re.sub(r":\d+\s*(AM|PM)", r" \1", tstr)
                try:
                    dt = datetime.strptime(tstr, "%I:%M %p")
                    minutes = dt.hour * 60 + dt.minute
                    debugprint(f"Converted {tstr} to {minutes} minutes (12-hour format)")
                    return minutes
                except ValueError:
                    try:
                        dt = datetime.strptime(tstr, "%I %p")
                        minutes = dt.hour * 60 + dt.minute
                        debugprint(f"Converted {tstr} to {minutes} minutes (12-hour short format)")
                        return minutes
                    except ValueError:
                        debugprint(f"Warning: Could not parse time string: {tstr}")
                        return 0
            else:
                try:
                    dt = datetime.strptime(tstr, "%H:%M:%S")
                    minutes = dt.hour * 60 + dt.minute
                    debugprint(f"Converted {tstr} to {minutes} minutes (24-hour format)")
                    return minutes
                except ValueError:
                    try:
                        dt = datetime.strptime(tstr, "%H:%M")
                        minutes = dt.hour * 60 + dt.minute
                        debugprint(f"Converted {tstr} to {minutes} minutes (24-hour short format)")
                        return minutes
                    except ValueError:
                        debugprint(f"Warning: Could not parse time string: {tstr}")
                        return 0

        except Exception as e:
            debugprint(f"Error converting time to minutes: {e}")
            return 0

    @staticmethod
    def minutes_to_time(minutes):
        """Convert minutes to time string in 24-hour format (HH:MM:SS)."""
        try:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours:02d}:{mins:02d}:00"
        except Exception as e:
            debugprint(f"Error converting minutes to time: {e}")
            return "00:00:00"


# Create an ExamConflictChecker class
class ExamConflictChecker:
    @staticmethod
    def check_conflicts(sections):
        """Check for conflicts between mid-term and final exams of sections."""
        exam_conflicts = []
        for i, section1 in enumerate(sections):
            for j in range(i + 1, len(sections)):
                section2 = sections[j]
                conflicts = check_exam_conflicts(section1, section2)
                if conflicts:
                    exam_conflicts.extend(conflicts)
        return exam_conflicts

    @staticmethod
    def format_conflict_message(conflicts):
        """Format exam conflicts message in a concise way without repetition."""
        if not conflicts:
            return ""

        # Get unique course pairs with conflicts (excluding self-conflicts)
        conflict_pairs = {}  # Changed to dict to store conflict details
        for conflict in conflicts:
            # Skip self-conflicts
            if conflict["course1"] == conflict["course2"]:
                continue
            # Sort courses to avoid duplicates like (A,B) and (B,A)
            courses = tuple(sorted([conflict["course1"], conflict["course2"]]))

            # Store conflict details by course pair
            if courses not in conflict_pairs:
                conflict_pairs[courses] = {"mid": None, "final": None}

            # Store the first occurrence of each exam type
            if (
                "Mid" in (conflict["type1"], conflict["type2"])
                and not conflict_pairs[courses]["mid"]
            ):
                conflict_pairs[courses]["mid"] = conflict["date"]
            if (
                "Final" in (conflict["type1"], conflict["type2"])
                and not conflict_pairs[courses]["final"]
            ):
                conflict_pairs[courses]["final"] = conflict["date"]

        if not conflict_pairs:
            return ""  # No conflicts after removing self-conflicts

        # Build concise message
        courses_involved = sorted(
            set(course for pair in conflict_pairs.keys() for course in pair)
        )

        message = "Exam Conflicts:\n\n"
        message += "Affected Courses:\n"
        message += ", ".join(courses_involved)

        message += "\n\nConflicting Pairs:\n"
        for courses, details in conflict_pairs.items():
            course1, course2 = courses
            conflicts_info = []
            if details["mid"]:
                conflicts_info.append(f"Mid: {details['mid']}")
            if details["final"]:
                conflicts_info.append(f"Final: {details['final']}")
            message += f"{course1} ⟷ {course2} ({', '.join(conflicts_info)})\n"

        return message.strip()


# Helper function to format 24-hour time string to 12-hour AM/PM
def convert_time_24_to_12(text):
    debugprint(f"Converting 24-hour time to 12-hour format: {text}")
    def repl(match):
        t = match.group(0)
        t = t[:5]
        debugprint(f"Processing time match: {t}")
        in_time = datetime.strptime(t, "%H:%M")
        # Use %#I for Windows, %-I for others
        result = in_time.strftime("%#I:%M %p")
        debugprint(f"Converted {t} to {result}")
        return result

    result = re.sub(r"\b([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b", repl, text)
    debugprint(f"Final result: {result}")
    return result


# Define your time slots (should match frontend)
TIME_SLOTS = [
    "8:00 AM-9:20 AM",
    "9:30 AM-10:50 AM",
    "11:00 AM-12:20 PM",
    "12:30 PM-1:50 PM",
    "2:00 PM-3:20 PM",
    "3:30 PM-4:50 PM",
    "5:00 PM-6:20 PM",
]


def parse_time(tstr):
    debugprint(f"Parsing time string: {tstr}")
    try:
        result = datetime.strptime(tstr, "%I:%M %p")
        debugprint(f"Parsed {tstr} to datetime object")
        return result
    except Exception as e:
        debugprint(f"Error parsing time string: {e}")
        return None


def slot_to_minutes(slot):
    debugprint(f"Converting time slot to minutes: {slot}")
    try:
        start_str, end_str = slot.split("-")
        start = parse_time(start_str.strip())
        end = parse_time(end_str.strip())
        if start is None or end is None:
            debugprint("Failed to parse start or end time")
            return 0, 0
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        debugprint(f"Converted {slot} to minutes: {start_minutes}-{end_minutes}")
        return start_minutes, end_minutes
    except Exception as e:
        debugprint(f"Error converting time slot to minutes: {e}")
        return 0, 0


def schedules_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap."""
    overlap = max(start1, start2) < min(end1, end2)
    debugprint(f"=== STEP 2: Checking Time Conflicts ===")
    debugprint(f"Checking overlap between {start1}-{end1} and {start2}-{end2}: {'Overlap found' if overlap else 'No overlap'}")
    return overlap


def normalize_date(date_str):
    """Normalize date string to YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        # Try parsing common date formats
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
    except Exception as e:
        debugprint(f"Error normalizing date: {e}")
        return None

def exam_schedules_overlap(exam1, exam2):
    """Check if two exam schedules conflict based on date and time."""
    try:
        # Convert times to minutes for comparison
        def convert_time(time_str):
            if not isinstance(time_str, str):
                debugprint(f"Warning: Invalid time format: {time_str}")
                return None
                
            # Remove any extra whitespace
            time_str = time_str.strip()
            
            # Try 24-hour format first (HH:MM:SS)
            try:
                hours, minutes, _ = time_str.split(':')
                return int(hours) * 60 + int(minutes)
            except ValueError:
                debugprint(f"Error converting time: {time_str}")
                return None

        # Get dates and times
        date1 = normalize_date(exam1.get("date"))
        date2 = normalize_date(exam2.get("date"))
        
        if not date1 or not date2:
            debugprint("Missing date information")
            return False
        
        if date1 != date2:
            debugprint(f"Different dates: {date1} vs {date2}")
            return False
            
        time1 = convert_time(exam1.get("time"))
        time2 = convert_time(exam2.get("time"))
        
        if time1 is None or time2 is None:
            debugprint("Missing or invalid time information")
            return False
            
        # Assume each exam takes 2 hours
        exam_duration = 120  # minutes
        
        # Check for overlap
        end_time1 = time1 + exam_duration
        end_time2 = time2 + exam_duration
        
        overlap = max(time1, time2) < min(end_time1, end_time2)
        debugprint(f"Checking exam overlap: {time1}-{end_time1} vs {time2}-{end_time2}: {'Overlap' if overlap else 'No overlap'}")
        return overlap
        
    except Exception as e:
        debugprint(f"Error comparing exam schedules: {e}")
        return False  # Return False to be safe if there's an error


def check_exam_conflicts(section1, section2):
    """Check for exam conflicts between two sections."""
    conflicts = []

    # Skip comparison if sections are the same
    if section1.get("sectionId") == section2.get("sectionId"):
        return []

    # Get exam schedules
    schedule1 = section1.get("sectionSchedule", {})
    schedule2 = section2.get("sectionSchedule", {})

    # Check midterm exam conflicts
    if schedule1.get("midExamDate") and schedule2.get("midExamDate"):
        if normalize_date(schedule1["midExamDate"]) == normalize_date(schedule2["midExamDate"]):
            print(f"\nChecking midterm exam conflict for {schedule1['midExamDate']}:")
            print(f"{section1.get('courseCode')} vs {section2.get('courseCode')}")
            
            exam1 = {
                "start": schedule1.get("midExamStartTime", "").replace(" ", ""),
                "end": schedule1.get("midExamEndTime", "").replace(" ", "")
            }
            exam2 = {
                "start": schedule2.get("midExamStartTime", "").replace(" ", ""),
                "end": schedule2.get("midExamEndTime", "").replace(" ", "")
            }
            
            if exam_schedules_overlap(exam1, exam2):
                conflicts.append({
                    "course1": section1.get("courseCode"),
                    "course2": section2.get("courseCode"),
                    "type1": "Mid",
                    "type2": "Mid",
                    "date": schedule1["midExamDate"],
                    "time1": f"{schedule1.get('midExamStartTime')} - {schedule1.get('midExamEndTime')}",
                    "time2": f"{schedule2.get('midExamStartTime')} - {schedule2.get('midExamEndTime')}"
                })

    # Check final exam conflicts
    if schedule1.get("finalExamDate") and schedule2.get("finalExamDate"):
        if normalize_date(schedule1["finalExamDate"]) == normalize_date(schedule2["finalExamDate"]):
            print(f"\nChecking final exam conflict for {schedule1['finalExamDate']}:")
            print(f"{section1.get('courseCode')} vs {section2.get('courseCode')}")
            
            exam1 = {
                "start": schedule1.get("finalExamStartTime", "").replace(" ", ""),
                "end": schedule1.get("finalExamEndTime", "").replace(" ", "")
            }
            exam2 = {
                "start": schedule2.get("finalExamStartTime", "").replace(" ", ""),
                "end": schedule2.get("finalExamEndTime", "").replace(" ", "")
            }
            
            if exam_schedules_overlap(exam1, exam2):
                conflicts.append({
                    "course1": section1.get("courseCode"),
                    "course2": section2.get("courseCode"),
                    "type1": "Final",
                    "type2": "Final",
                    "date": schedule1["finalExamDate"],
                    "time1": f"{schedule1.get('finalExamStartTime')} - {schedule1.get('finalExamEndTime')}",
                    "time2": f"{schedule2.get('finalExamStartTime')} - {schedule2.get('finalExamEndTime')}"
                })

    return conflicts


def has_internal_conflicts(section):
    """Check if a single section has overlapping class or lab schedules."""
    debugprint(f"\nChecking internal conflicts for section {section.get('courseCode')} {section.get('sectionName')}")
    schedules = []
    if section.get("sectionSchedule") and section["sectionSchedule"].get(
        "classSchedules"
    ):
        debugprint("Processing class schedules")
        for sched in section["sectionSchedule"]["classSchedules"]:
            if sched.get("day") and sched.get("startTime") and sched.get("endTime"):
                schedule = {
                    "day": sched["day"].upper(),
                    "start": TimeUtils.time_to_minutes(sched["startTime"]),
                    "end": TimeUtils.time_to_minutes(sched["endTime"]),
                }
                schedules.append(schedule)
                debugprint(f"Added class schedule: {sched['day']} {sched['startTime']}-{sched['endTime']}")

    if section.get("labSchedules"):
        debugprint("Processing lab schedules")
        for lab in get_lab_schedules_flat(section):
            if lab.get("day") and lab.get("startTime") and lab.get("endTime"):
                schedule = {
                    "day": lab["day"].upper(),
                    "start": TimeUtils.time_to_minutes(lab["startTime"]),
                    "end": TimeUtils.time_to_minutes(lab["endTime"]),
                }
                schedules.append(schedule)
                debugprint(f"Added lab schedule: {lab['day']} {lab['startTime']}-{lab['endTime']}")

    debugprint(f"Found {len(schedules)} total schedules")

    # Check for conflicts among all schedules in this section
    for i in range(len(schedules)):
        for j in range(i + 1, len(schedules)):
            if schedules[i]["day"] == schedules[j]["day"]:
                debugprint(f"Checking overlap for {schedules[i]['day']}:")
                debugprint(f"Schedule 1: {TimeUtils.minutes_to_time(schedules[i]['start'])}-{TimeUtils.minutes_to_time(schedules[i]['end'])}")
                debugprint(f"Schedule 2: {TimeUtils.minutes_to_time(schedules[j]['start'])}-{TimeUtils.minutes_to_time(schedules[j]['end'])}")
                if schedules_overlap(
                    schedules[i]["start"],
                    schedules[i]["end"],
                    schedules[j]["start"],
                    schedules[j]["end"],
                ):
                    debugprint("Found internal conflict!")
                    return True
                else:
                    debugprint("No overlap found")

    debugprint("No internal conflicts found")
    return False


@app.route("/api/course_details")
def course_details():
    data = load_data()
    code = request.args.get("course")
    show_all = request.args.get("show_all", "false").lower() == "true"  # Get show_all parameter
    
    debugprint(f"\n=== Getting Course Details for {code} ===")
    debugprint(f"Show All: {show_all}")
    
    # Get all sections for the course
    all_sections = [section for section in data if section.get("courseCode") == code]
    debugprint(f"Found {len(all_sections)} total sections for {code}")

    # Filter sections based on show_all parameter
    details = []
    for section in all_sections:
        available_seats = section.get("capacity", 0) - section.get("consumedSeat", 0)
        if show_all or available_seats > 0:  # Include all sections if show_all is true
            # Add available seats information
            section["availableSeats"] = available_seats
            debugprint(f"Including section {section.get('sectionName')} with {available_seats} seats")

            # Add exam information - Prioritize data from sectionSchedule
            section_schedule = section.get("sectionSchedule", {})

            # Midterm Exam
            section["midExamDate"] = section_schedule.get("midExamDate") or section.get(
                "midExamDate"
            )
            section["midExamStartTime"] = section_schedule.get(
                "midExamStartTime"
            ) or section.get("midExamStartTime")
            section["midExamEndTime"] = section_schedule.get(
                "midExamEndTime"
            ) or section.get("midExamEndTime")

            # Final Exam
            section["finalExamDate"] = section_schedule.get(
                "finalExamDate"
            ) or section.get("finalExamDate")
            section["finalExamStartTime"] = section_schedule.get(
                "finalExamStartTime"
            ) or section.get("finalExamStartTime")
            section["finalExamEndTime"] = section_schedule.get(
                "finalExamEndTime"
            ) or section.get("finalExamEndTime")

            # Optional: Add formatted exam times (12-hour AM/PM) using the
            # prioritized times
            if section.get("midExamStartTime") and section.get("midExamEndTime"):
                section["formattedMidExamTime"] = convert_time_24_to_12(
                    f"{section['midExamStartTime']} - {section['midExamEndTime']}"
                )
            else:
                section["formattedMidExamTime"] = None

            if section.get("finalExamStartTime") and section.get("finalExamEndTime"):
                section["formattedFinalExamTime"] = convert_time_24_to_12(
                    f"{section['finalExamStartTime']} - {section['finalExamEndTime']}"
                )
            else:
                section["formattedFinalExamTime"] = None

            # Format schedule information
            if section.get("sectionSchedule"):
                class_schedules = section["sectionSchedule"].get("classSchedules")
                if isinstance(class_schedules, list):
                    for schedule in class_schedules:
                        schedule["formattedTime"] = convert_time_24_to_12(
                            f"{schedule['startTime']} - {schedule['endTime']}"
                        )
                else:
                    # If classSchedules is not a list, skip formatting
                    pass

            # Format lab schedule information
            lab_schedules = section.get("labSchedules")
            if isinstance(lab_schedules, list):
                for schedule in lab_schedules:
                    schedule["formattedTime"] = convert_time_24_to_12(
                        f"{schedule['startTime']} - {schedule['endTime']}"
                    )
            else:
                # If labSchedules is not a list, skip formatting
                pass

            details.append(section)

    debugprint(f"Returning {len(details)} sections")
    return jsonify(details)


@app.route("/api/faculty")
def get_faculty():
    # Get unique faculty names from all sections
    faculty = set()
    for section in data:
        if section.get("faculties"):
            faculty.add(section.get("faculties"))
    return jsonify(list(faculty))


@app.route("/api/faculty_for_courses")
def get_faculty_for_courses():
    course_codes = request.args.get("courses", "").split(",")
    faculty = set()

    # Get faculty for each course
    for code in course_codes:
        sections = [section for section in data if section.get("courseCode") == code]
        for section in sections:
            if section.get("faculties"):
                faculty.add(section.get("faculties"))

    return jsonify(list(faculty))


def get_lab_schedule(section):
    """Extract and format lab schedule information for a section, supporting both array and nested object formats."""
    debugprint(f"\nGetting lab schedule for section {section.get('courseCode')} {section.get('sectionName')}")
    lab_schedules = section.get("labSchedules", [])
    formatted_labs = []

    # If lab_schedules is a dict (new API format), extract classSchedules
    if isinstance(lab_schedules, dict):
        debugprint("Processing lab schedules in new API format (dict with classSchedules)")
        class_schedules = lab_schedules.get("classSchedules", [])
        room = section.get("labRoomName") or lab_schedules.get("room", "TBA")
        for sched in class_schedules:
            day = sched.get("day", "").capitalize()
            start = sched.get("startTime")
            end = sched.get("endTime")
            if start and end:
                sched_start = TimeUtils.time_to_minutes(start)
                sched_end = TimeUtils.time_to_minutes(end)
                formatted_time = convert_time_24_to_12(f"{start} - {end}")
                lab_info = {
                    "day": day,
                    "startTime": start,
                    "endTime": end,
                    "formattedTime": formatted_time,
                    "room": room,
                    "startMinutes": sched_start,
                    "endMinutes": sched_end,
                }
                formatted_labs.append(lab_info)
                debugprint(f"Added lab schedule: {day} {formatted_time} in {room}")
    # If lab_schedules is a list (legacy/expected format)
    elif isinstance(lab_schedules, list):
        debugprint("Processing lab schedules in legacy format (list)")
        for lab in lab_schedules:
            day = lab.get("day", "").capitalize()
            start = lab.get("startTime")
            end = lab.get("endTime")
            room = lab.get("room", section.get("labRoomName", "TBA"))
            if start and end:
                sched_start = TimeUtils.time_to_minutes(start)
                sched_end = TimeUtils.time_to_minutes(end)
                formatted_time = convert_time_24_to_12(f"{start} - {end}")
                lab_info = {
                    "day": day,
                    "startTime": start,
                    "endTime": end,
                    "formattedTime": formatted_time,
                    "room": room,
                    "startMinutes": sched_start,
                    "endMinutes": sched_end,
                }
                formatted_labs.append(lab_info)
                debugprint(f"Added lab schedule: {day} {formatted_time} in {room}")
    # Otherwise, return empty list
    else:
        debugprint(f"Warning: Unrecognized lab schedule format: {type(lab_schedules)}")
    
    debugprint(f"Found {len(formatted_labs)} lab schedules")
    return formatted_labs


def get_lab_schedule_bd(section):
    """Extract and format lab schedule information for a section, converting times to Bangladesh timezone (GMT+6)."""
    debugprint(f"\nGetting Bangladesh timezone lab schedule for section {section.get('courseCode')} {section.get('sectionName')}")
    lab_schedules = section.get("labSchedules", []) or []
    formatted_labs = []
    for lab in lab_schedules:
        day = lab.get("day", "").capitalize()
        start = lab.get("startTime")
        end = lab.get("endTime")
        room = lab.get("room", "TBA")
        if start and end:
            debugprint(f"Converting lab time from UTC to BD: {start} - {end}")
            # Parse as UTC and convert to BD time
            try:
                # Assume input is in HH:MM:SS, treat as naive local time,
                # localize to UTC, then convert
                start_dt = datetime.strptime(start, "%H:%M:%S")
                end_dt = datetime.strptime(end, "%H:%M:%S")
                # Attach today's date for conversion
                today = datetime.now().date()
                start_dt = datetime.combine(today, start_dt.time())
                end_dt = datetime.combine(today, end_dt.time())
                # Localize to UTC, then convert to BD
                start_bd = pytz.utc.localize(start_dt).astimezone(BD_TIMEZONE)
                end_bd = pytz.utc.localize(end_dt).astimezone(BD_TIMEZONE)
                start_str_bd = start_bd.strftime("%H:%M:%S")
                end_str_bd = end_bd.strftime("%H:%M:%S")
                formatted_time = convert_time_24_to_12(f"{start_str_bd} - {end_str_bd}")
                sched_start = TimeUtils.time_to_minutes(start_str_bd)
                sched_end = TimeUtils.time_to_minutes(end_str_bd)
                debugprint(f"Converted to BD time: {start_str_bd} - {end_str_bd}")
            except Exception as e:
                # Fallback: use original times
                debugprint(f"Error converting to BD time: {e}")
                debugprint("Using original times as fallback")
                start_str_bd = start
                end_str_bd = end
                formatted_time = convert_time_24_to_12(f"{start} - {end}")
                sched_start = TimeUtils.time_to_minutes(start)
                sched_end = TimeUtils.time_to_minutes(end)
            lab_info = {
                "day": day,
                "startTime": start_str_bd,
                "endTime": end_str_bd,
                "formattedTime": formatted_time,
                "room": room,
                "startMinutes": sched_start,
                "endMinutes": sched_end,
            }
            formatted_labs.append(lab_info)
            debugprint(f"Added lab schedule: {day} {formatted_time} in {room}")
    
    debugprint(f"Found {len(formatted_labs)} lab schedules")
    return formatted_labs


def check_lab_conflicts(section1, section2):
    """Check if two sections have conflicting lab schedules."""
    debugprint(f"\nChecking lab conflicts between {section1.get('courseCode')} and {section2.get('courseCode')}")
    labs1 = get_lab_schedule(section1)
    labs2 = get_lab_schedule(section2)

    debugprint(f"Found {len(labs1)} labs for {section1.get('courseCode')} and {len(labs2)} labs for {section2.get('courseCode')}")

    for lab1 in labs1:
        for lab2 in labs2:
            if lab1["day"] == lab2["day"]:
                debugprint(f"Checking overlap for {lab1['day']}:")
                debugprint(f"{section1.get('courseCode')}: {lab1['formattedTime']} in {lab1['room']}")
                debugprint(f"{section2.get('courseCode')}: {lab2['formattedTime']} in {lab2['room']}")
                if schedules_overlap(
                    lab1["startMinutes"],
                    lab1["endMinutes"],
                    lab2["startMinutes"],
                    lab2["endMinutes"],
                ):
                    debugprint("Found lab conflict!")
                    return True
                else:
                    debugprint("No overlap found")
    
    debugprint("No lab conflicts found")
    return False


def format_exam_conflicts_message(conflicts):
    """Format exam conflicts message in a concise way without repetition."""
    if not conflicts:
        return ""

    # Get unique course pairs with conflicts (excluding self-conflicts)
    mid_conflicts = {}
    final_conflicts = {}
    courses_involved = set()

    for conflict in conflicts:
        # Skip self-conflicts
        if conflict["course1"] == conflict["course2"]:
            continue

        # Add to courses involved
        courses_involved.add(conflict["course1"])
        courses_involved.add(conflict["course2"])

        # Sort courses for consistent ordering
        course1, course2 = sorted([conflict["course1"], conflict["course2"]])
        pair = (course1, course2)

        # Store in appropriate conflict dict with date and time
        if "Mid" in (conflict["type1"], conflict["type2"]):
            mid_conflicts[pair] = {
                "date": conflict["date"],
                "time": conflict["time1"],
            }
        if "Final" in (conflict["type1"], conflict["type2"]):
            final_conflicts[pair] = {
                "date": conflict["date"],
                "time": conflict["time1"],
            }

    if not mid_conflicts and not final_conflicts:
        return ""

    # Build message with proper formatting
    message = "Exam Conflicts\n\n"
    message += f"Affected Courses: {', '.join(sorted(courses_involved))}\n\n"

    # Add midterm conflicts if any exist
    if mid_conflicts:
        message += "Midterm Conflicts\n"
        for (course1, course2), details in sorted(mid_conflicts.items()):
            message += f"{course1} ↔ {course2}: {details['date']}, {details['time']}\n"

    # Add final conflicts if any exist
    if final_conflicts:
        if mid_conflicts:  # Add extra line break if we had midterm conflicts
            message += "\n"
        message += "Final Conflicts\n"
        for (course1, course2), details in sorted(final_conflicts.items()):
            message += f"{course1} ↔ {course2}: {details['date']}, {details['time']}\n"

    return message.strip()


def check_and_return_exam_conflicts(sections):
    """Check for exam conflicts among the given sections and return formatted message if conflicts exist."""
    exam_conflicts = []
    for i in range(len(sections)):
        section1 = sections[i]
        for j in range(i + 1, len(sections)):
            section2 = sections[j]
            conflicts = check_exam_conflicts(section1, section2)
            exam_conflicts.extend(conflicts)

    if exam_conflicts:
        error_message = format_exam_conflicts_message(exam_conflicts)
        return jsonify({"error": error_message}), 200
    return None


def get_required_days_for_course(sections):
    """Get all required days for a course's sections."""
    required_days = set()
    for section in sections:
        # Check class schedules
        if section.get("sectionSchedule") and section["sectionSchedule"].get(
            "classSchedules"
        ):
            for schedule in section["sectionSchedule"]["classSchedules"]:
                if schedule.get("day"):
                    required_days.add(schedule["day"].upper())

        # Check lab schedules
        for lab in get_lab_schedules_flat(section):
            if lab.get("day"):
                required_days.add(lab["day"].upper())

    return required_days


def check_exam_compatibility(sections):
    """Check if a set of sections has any exam conflicts. Returns (has_conflicts, error_message)."""
    exam_conflicts = []
    
    # Check all possible pairs of sections, including different sections of the same course
    for i, section1 in enumerate(sections):
        for j in range(i + 1, len(sections)):
            section2 = sections[j]
            conflicts = check_exam_conflicts(section1, section2)
            if conflicts:
                exam_conflicts.extend(conflicts)

    if exam_conflicts:
        error_message = format_exam_conflicts_message(exam_conflicts)
        return True, error_message

    return False, None


def normalize_time(time_str):
    """Normalize time string to HH:MM:SS format."""
    if not time_str:
        debugprint("Warning: Empty time string")
        return "00:00:00"

    time_str = time_str.strip().upper()
    debugprint(f"Normalizing time: {time_str}")

    try:
        # Handle AM/PM format
        if "AM" in time_str or "PM" in time_str:
            # Remove any seconds if present
            time_str = re.sub(r":\d+\s*(AM|PM)", r" \1", time_str)
            # Add missing colons if needed (e.g., "8 AM" -> "8:00 AM")
            if ":" not in time_str:
                time_str = time_str.replace(" ", ":00 ")
            try:
                dt = datetime.strptime(time_str, "%I:%M %p")
                result = dt.strftime("%H:%M:%S")
                debugprint(f"Normalized {time_str} to {result} (12-hour format)")
                return result
            except ValueError:
                try:
                    dt = datetime.strptime(time_str, "%I:%M:%S %p")
                    result = dt.strftime("%H:%M:%S")
                    debugprint(f"Normalized {time_str} to {result} (12-hour format with seconds)")
                    return result
                except ValueError:
                    # Try one more time with flexible parsing
                    time_str = re.sub(
                        r"(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(AM|PM)", r"\1:\2 \3", time_str
                    )
                    # Fix the string joining operation
                    parts = time_str.replace(":", ":00:").split(":")
                    time_str = ":".join(parts[0:2]) + " " + time_str.split()[-1]
                    dt = datetime.strptime(time_str, "%I:%M %p")
                    result = dt.strftime("%H:%M:%S")
                    debugprint(f"Normalized {time_str} to {result} (12-hour format with flexible parsing)")
                    return result
        else:
            # Handle 24-hour format
            parts = time_str.split(":")
            if len(parts) == 1:  # Just hours
                result = f"{int(parts[0]):02d}:00:00"
                debugprint(f"Normalized {time_str} to {result} (24-hour format, hours only)")
                return result
            elif len(parts) == 2:  # Hours and minutes
                result = f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"
                debugprint(f"Normalized {time_str} to {result} (24-hour format, hours and minutes)")
                return result
            else:  # Full time
                result = f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
                debugprint(f"Normalized {time_str} to {result} (24-hour format, full time)")
                return result
    except Exception as e:
        debugprint(f"Error normalizing time {time_str}: {e}")
        return "00:00:00"  # Return midnight if parsing fails


def filter_section_by_time(section, selected_times):
    """Check if section schedules fit within selected time ranges."""
    debugprint(f"\nFiltering section {section.get('courseCode')} {section.get('sectionName')} by time")
    if not selected_times:  # If no times selected, accept all
        debugprint("No time restrictions, accepting section")
        return True, "No time restrictions"

    def time_in_ranges(schedule_type, day, start_time, end_time):
        try:
            if not start_time or not end_time:
                debugprint(f"Missing time data for {schedule_type}, accepting schedule")
                return True, None  # Accept if missing time data

            # Normalize times
            start_time = normalize_time(start_time)
            end_time = normalize_time(end_time)
            debugprint(f"Checking {schedule_type} schedule: {day} {start_time}-{end_time}")

            start_minutes = TimeUtils.time_to_minutes(start_time)
            end_minutes = TimeUtils.time_to_minutes(end_time)

            # For lab sessions, we need to ensure ALL required time slots are
            # selected
            if schedule_type == "Lab":
                debugprint("Processing lab schedule")
                # Validate lab duration (should be at least 2 hours and 50
                # minutes)
                lab_duration = end_minutes - start_minutes
                if lab_duration < 170:  # 2 hours and 50 minutes = 170 minutes
                    debugprint(f"Lab duration ({lab_duration} minutes) is less than required 2 hours and 50 minutes")
                    return (
                        False,
                        f"Lab session duration ({lab_duration} minutes) is less than required 2 hours and 50 minutes",
                    )

                # Get all time slots that this lab session spans
                required_slots = []
                for time_slot in TIME_SLOTS:
                    slot_start, slot_end = time_slot.split("-")
                    slot_start = normalize_time(slot_start.strip())
                    slot_end = normalize_time(slot_end.strip())
                    range_start = TimeUtils.time_to_minutes(slot_start)
                    range_end = TimeUtils.time_to_minutes(slot_end)

                    # If this slot overlaps with the lab session, it's required
                    if start_minutes <= range_end and end_minutes >= range_start:
                        required_slots.append(time_slot)
                        debugprint(f"Found required time slot: {time_slot}")

                # Check if all required slots are selected
                if not all(slot in selected_times for slot in required_slots):
                    missing_slots = [slot for slot in required_slots if slot not in selected_times]
                    debugprint(f"Missing required time slots: {', '.join(missing_slots)}")
                    return (
                        False,
                        f"Lab session requires all time slots it spans to be selected: {', '.join(required_slots)}",
                    )
                debugprint("All required time slots are selected")
                return True, None

            # For regular classes, use the original overlap check
            debugprint("Processing regular class schedule")
            for time_slot in selected_times:
                slot_start, slot_end = time_slot.split("-")
                slot_start = normalize_time(slot_start.strip())
                slot_end = normalize_time(slot_end.strip())
                range_start = TimeUtils.time_to_minutes(slot_start)
                range_end = TimeUtils.time_to_minutes(slot_end)

                debugprint(f"Checking time slot {time_slot}")
                if start_minutes <= range_end and end_minutes >= range_start:
                    debugprint("Schedule fits in time slot")
                    return True, None

            debugprint(f"Schedule doesn't fit in any selected time slot")
            return (
                False,
                f"{schedule_type} time {start_time}-{end_time} doesn't fit in any selected time slot",
            )

        except Exception as e:
            debugprint(f"Error in time_in_ranges: {e}")
            return True, None  # Accept the section if there's an error in time parsing

    # Check class schedules
    debugprint("Checking class schedules")
    if section.get("sectionSchedule") and section["sectionSchedule"].get(
        "classSchedules"
    ):
        for schedule in section["sectionSchedule"]["classSchedules"]:
            valid, error = time_in_ranges(
                "Class",
                schedule.get("day", ""),
                schedule.get("startTime", ""),
                schedule.get("endTime", ""),
            )
            if not valid:
                debugprint(f"Class schedule invalid: {error}")
                return False, error

    # Check lab schedules
    debugprint("Checking lab schedules")
    for lab in get_lab_schedules_flat(section):
        valid, error = time_in_ranges(
            "Lab",
            lab.get("day", ""),
            lab.get("startTime", ""),
            lab.get("endTime", ""),
        )
        if not valid:
            debugprint(f"Lab schedule invalid: {error}")
            return False, error

    debugprint("All schedules fit within selected times")
    return True, None


def check_schedule_compatibility(schedule1, schedule2):
    """Check if two schedules are compatible (no time conflicts)."""
    try:
        debugprint("\n=== STEP 2: Checking Time Conflicts ===")
        
        # Safely get day values with .get()
        day1 = schedule1.get("day", "").upper() if isinstance(schedule1, dict) else ""
        day2 = schedule2.get("day", "").upper() if isinstance(schedule2, dict) else ""
        
        debugprint(f"Checking schedule compatibility:")
        debugprint(f"Schedule 1: Day={day1}, Start={schedule1.get('startTime', '')}, End={schedule1.get('endTime', '')}")
        debugprint(f"Schedule 2: Day={day2}, Start={schedule2.get('startTime', '')}, End={schedule2.get('endTime', '')}")
        
        if day1 != day2:
            debugprint(f"Different days ({day1} vs {day2}), no conflict")
            return True

        # Safely get time values with .get()
        start1 = TimeUtils.time_to_minutes(normalize_time(schedule1.get("startTime", "")))
        end1 = TimeUtils.time_to_minutes(normalize_time(schedule1.get("endTime", "")))
        start2 = TimeUtils.time_to_minutes(normalize_time(schedule2.get("startTime", "")))
        end2 = TimeUtils.time_to_minutes(normalize_time(schedule2.get("endTime", "")))

        compatible = not schedules_overlap(start1, end1, start2, end2)
        debugprint(f"Schedules are {'compatible' if compatible else 'not compatible'}")
        return compatible
    except Exception as e:
        debugprint(f"Error in check_schedule_compatibility: {e}")
        return False  # If there's any error, assume there's a conflict to be safe


def get_all_schedules(section):
    """Get all schedules (both class and lab) for a section."""
    debugprint(f"\nGetting all schedules for section {section.get('courseCode')} {section.get('sectionName')}")
    schedules = []
    # Add class schedules
    if section.get("sectionSchedule") and section["sectionSchedule"].get(
        "classSchedules"
    ):
        class_schedules = section["sectionSchedule"]["classSchedules"]
        schedules.extend(class_schedules)
        debugprint(f"Added {len(class_schedules)} class schedules")
        for sched in class_schedules:
            debugprint(f"Class schedule: {sched.get('day')} {sched.get('startTime')}-{sched.get('endTime')}")
    
    # Add lab schedules using the flat helper function
    lab_schedules = get_lab_schedules_flat(section)
    schedules.extend(lab_schedules)
    debugprint(f"Added {len(lab_schedules)} lab schedules")
    for lab in lab_schedules:
        debugprint(f"Lab schedule: {lab.get('day')} {lab.get('startTime')}-{lab.get('endTime')}")
    
    debugprint(f"Total schedules: {len(schedules)}")
    return schedules


def is_valid_combination(sections):
    """Check if a combination of sections has any schedule conflicts."""
    debugprint("\nChecking if section combination is valid")
    for i, section1 in enumerate(sections):
        debugprint(f"\nProcessing section {section1.get('courseCode')} {section1.get('sectionName')}")
        schedules1 = get_all_schedules(section1)

        # Check for internal conflicts in the same section
        debugprint("Checking for internal conflicts")
        for j, sched1 in enumerate(schedules1):
            for sched2 in schedules1[j + 1 :]:
                if not check_schedule_compatibility(sched1, sched2):
                    debugprint(f"Found internal conflict in {section1.get('courseCode')} section {section1.get('sectionName')}")
                    return False

        # Check conflicts with other sections
        debugprint("Checking conflicts with other sections")
        for section2 in sections[i + 1 :]:
            debugprint(f"Comparing with section {section2.get('courseCode')} {section2.get('sectionName')}")
            # Skip schedule compatibility check if sections are from the same
            # course and faculty
            if section1.get("courseCode") == section2.get(
                "courseCode"
            ) and section1.get("faculties") == section2.get("faculties"):
                debugprint(f"Skipping schedule compatibility check between sections of the same course and faculty: {section1.get('courseCode')} ({section1.get('faculties')})")
                continue

            schedules2 = get_all_schedules(section2)
            for sched1 in schedules1:
                for sched2 in schedules2:
                    if not check_schedule_compatibility(sched1, sched2):
                        debugprint(f"Found conflict between {section1.get('courseCode')} Section {section1.get('sectionName')} ({section1.get('faculties')}) and {section2.get('courseCode')} Section {section2.get('sectionName')} ({section2.get('faculties')})")
                        return False
    debugprint("No conflicts found, combination is valid")
    return True


def try_all_section_combinations(course_sections_map, selected_days, selected_times):
    """Try all possible combinations of sections to find a valid routine."""
    try:
        debugprint("\n=== Trying Section Combinations ===")
        
        # Get all possible combinations
        courses = list(course_sections_map.keys())
        all_combinations = list(itertools.product(*[course_sections_map[course] for course in courses]))
        print(f"Generated {len(all_combinations)} possible combinations")
        
        # Convert selected times to minutes for easier comparison
        time_ranges = []
        for time_slot in selected_times:
            start, end = time_slot.split("-")
            start_mins = TimeUtils.time_to_minutes(start.strip())
            end_mins = TimeUtils.time_to_minutes(end.strip())
            time_ranges.append((start_mins, end_mins))
            
        print(f"\nSelected time ranges:")
        for start, end in time_ranges:
            print(f"• {TimeUtils.minutes_to_time(start)} - {TimeUtils.minutes_to_time(end)}")
            
        # Iterate through combinations
        print("\nChecking combinations for conflicts...")
        valid_combinations = []
        
        for idx, combination in enumerate(all_combinations, 1):
            print(f"\nTrying combination {idx}/{len(all_combinations)}")
            
            # Check if all sections are within selected days and times
            valid = True
            conflicts = []
            
            # Check for time conflicts between sections
            for i in range(len(combination)):
                section1 = combination[i]
                for j in range(i + 1, len(combination)):
                    section2 = combination[j]
                    
                    # Skip if same course (different sections of same course can't be taken)
                    if section1.get("courseCode") == section2.get("courseCode"):
                        valid = False
                        conflicts.append(f"Cannot take multiple sections of {section1.get('courseCode')}")
                        break
                    
                    # Check for time conflicts
                    if has_time_conflict(section1, section2):
                        valid = False
                        conflicts.append(f"Time conflict between {section1.get('courseCode')} and {section2.get('courseCode')}")
                        break
                        
                if not valid:
                    break
            
            if not valid:
                print("\nConflicts found:")
                for conflict in conflicts:
                    print(f"• {conflict}")
                continue
            
            # Check if sections fit within selected days and times
            for section in combination:
                course_code = section.get("courseCode")
                section_name = section.get("sectionName")
                print(f"\nChecking {course_code} Section {section_name}")
                
                # Check class schedules
                if section.get("sectionSchedule"):
                    for schedule in section["sectionSchedule"].get("classSchedules", []):
                        day = schedule.get("day", "").upper()
                        if day not in selected_days:
                            print(f"❌ Class day {day} not in selected days")
                            valid = False
                            conflicts.append(f"{course_code} requires {day}")
                            break
                            
                        start_time = TimeUtils.time_to_minutes(schedule.get("startTime", ""))
                        end_time = TimeUtils.time_to_minutes(schedule.get("endTime", ""))
                        
                        # Check if class time is within any selected time slot
                        time_valid = False
                        for time_start, time_end in time_ranges:
                            if start_time >= time_start and end_time <= time_end:
                                time_valid = True
                                break
                                
                        if not time_valid:
                            print(f"❌ Class time {schedule.get('startTime')} - {schedule.get('endTime')} outside selected times")
                            valid = False
                            conflicts.append(f"{course_code} time conflict")
                            break
                            
                # Check lab schedules
                lab_schedules = get_lab_schedules_flat(section)
                for lab in lab_schedules:
                    day = lab.get("day", "").upper()
                    if day not in selected_days:
                        print(f"❌ Lab day {day} not in selected days")
                        valid = False
                        conflicts.append(f"{course_code} Lab requires {day}")
                        break
                        
                    start_time = TimeUtils.time_to_minutes(lab.get("startTime", ""))
                    end_time = TimeUtils.time_to_minutes(lab.get("endTime", ""))
                    
                    # Check if lab time is within any selected time slot
                    time_valid = False
                    for time_start, time_end in time_ranges:
                        if start_time >= time_start and end_time <= time_end:
                            time_valid = True
                            break
                            
                    if not time_valid:
                        print(f"❌ Lab time {lab.get('startTime')} - {lab.get('endTime')} outside selected times")
                        valid = False
                        conflicts.append(f"{course_code} Lab time conflict")
                        break
                        
                if not valid:
                    break
            
            if valid:
                print("\n✅ Found valid combination!")
                valid_combinations.append(list(combination))
                
            if not valid:
                print("\nConflicts in combination {idx}:")
                for conflict in conflicts:
                    print(f"• {conflict}")
        
        if valid_combinations:
            # Return the first valid combination
            return valid_combinations[0], None
                
        print("\n❌ No valid combination found")
        return None, "Could not find a valid combination without conflicts. Please try different sections or time slots."
        
    except Exception as e:
        print(f"\n❌ Error finding combinations: {e}")
        traceback.print_exc()
        return None, f"Error finding valid combinations: {e}"


@app.route("/api/routine", methods=["POST"])
def generate_routine():
    try:
        # Load fresh data for each routine generation request
        debugprint("\n=== Loading Fresh Course Data ===")
        fresh_data = load_data()  # Get fresh data from the API
        if not fresh_data:
            return jsonify({"error": "Failed to load current course data"}), 503
        
        # Get request data
        request_data = request.get_json()
        debugprint("\n=== Request Data ===")
        debugprint("Raw request data:", request_data)
        
        if not request_data:
            return jsonify({"error": "No data provided"}), 400

        # Handle both old and new request formats
        if "courses" in request_data:
            courses = request_data["courses"]
            days = request_data.get("days", [])
            times = request_data.get("times", [])
            use_ai = request_data.get("useAI", False)
            commute_preference = request_data.get("commutePreference", "")
            
            # Get all possible combinations
            all_combinations = []
            for course in courses:
                course_code = course["course"]
                sections_by_faculty = course.get("sections", {})
                
                debugprint(f"\n=== Processing Course: {course_code} ===")
                
                # Find all sections for this course
                course_sections = []
                
                # Get all sections for the course
                available_sections = [s for s in fresh_data if s.get("courseCode") == course_code]
                debugprint(f"Total sections found for {course_code}: {len(available_sections)}")
                
                if not available_sections:
                    debugprint(f"❌ Course not found in fresh data: {course_code}")
                    return jsonify({"error": f"Course {course_code} not found in available courses"}), 400

                # Print all sections and their details
                for section in available_sections:
                    debugprint(f"\nSection: {section.get('sectionName')}")
                    debugprint(f"Faculty: {section.get('faculties')}")
                    debugprint(f"Capacity: {section.get('capacity')}")
                    debugprint(f"Consumed Seats: {section.get('consumedSeat')}")
                    debugprint(f"Available Seats: {section.get('capacity', 0) - section.get('consumedSeat', 0)}")

                # Check if specific sections are selected
                if sections_by_faculty:
                    debugprint(f"\n=== Processing Faculty Selections for {course_code} ===")
                    # Process each selected faculty and section
                    for faculty, section_info in sections_by_faculty.items():
                        section_name = section_info.get("value")  # Get the section number
                        debugprint(f"\nProcessing Faculty: {faculty}")
                        debugprint(f"Section info: {section_info}")
                        
                        # If no specific section is selected, get all sections for this faculty
                        if not section_name:
                            debugprint(f"No specific section selected for faculty {faculty}")
                            faculty_sections = [
                                s for s in available_sections 
                                if s.get("faculties") == faculty 
                                and s.get("capacity", 0) - s.get("consumedSeat", 0) > 0
                            ]
                            debugprint(f"Found {len(faculty_sections)} available sections for faculty {faculty}:")
                            for s in faculty_sections:
                                debugprint(f"- Section {s.get('sectionName')}: {s.get('capacity', 0) - s.get('consumedSeat', 0)} seats available")
                            course_sections.extend(faculty_sections)
                            continue
                            
                        # Find matching section if specific section selected
                        matching_sections = [
                            s for s in available_sections 
                            if s.get("sectionName") == section_name 
                            and s.get("faculties") == faculty
                        ]
                        
                        if matching_sections:
                            debugprint(f"Found matching section for {course_code} section {section_name}")
                            course_sections.extend(matching_sections)
                        else:
                            debugprint(f"No matching section found for {course_code} section {section_name}")
                else:
                    debugprint(f"No sections selected for {course_code}, getting all available sections")
                    course_sections = [
                        section for section in available_sections 
                        if section.get("capacity", 0) - section.get("consumedSeat", 0) > 0
                    ]
                
                if not course_sections:
                    msg = "No available sections found"
                    if sections_by_faculty:
                        msg += " matching your selection"
                    msg += f" for {course_code}"
                    debugprint(f"❌ {msg}")
                    return jsonify({"error": msg}), 400
                
                debugprint(f"\nFinal sections selected for {course_code}: {len(course_sections)}")
                for section in course_sections:
                    debugprint(f"- Section {section.get('sectionName')} with faculty {section.get('faculties')}")
                all_combinations.append(course_sections)

            if not all_combinations:
                return jsonify({"error": "No valid sections found for any courses"}), 400

            # Generate all possible combinations
            try:
                all_combinations = list(itertools.product(*all_combinations))
                debugprint(f"Generated {len(all_combinations)} possible combinations")
            except Exception as e:
                debugprint(f"Error generating combinations: {str(e)}")
                return jsonify({"error": "Failed to generate valid combinations. Please check your course selections."}), 400

            if not all_combinations:
                return jsonify({"error": "No valid combinations could be generated"}), 400

            # STEP 1: Check exam conflicts
            debugprint("\n=== STEP 1: Checking Exam Conflicts ===")
            combinations_without_exam_conflicts = []
            for combination in all_combinations:
                # Validate combination structure
                if not all(isinstance(section, dict) and "courseCode" in section for section in combination):
                    debugprint("Invalid section found in combination, skipping...")
                    continue

                has_exam_conflicts, exam_error = check_exam_compatibility(combination)
                if has_exam_conflicts:
                    debugprint(f"✗ Exam conflict found: {exam_error}")
                    # Format the error message for the frontend's ExamConflictMessage component
                    affected_courses = [section["courseCode"] for section in combination]
                    error_msg = f"Exam Conflicts\nAffected Courses: {', '.join(affected_courses)}\n{exam_error}"
                    return jsonify({"error": error_msg}), 200
                combinations_without_exam_conflicts.append(combination)

            if not combinations_without_exam_conflicts:
                return jsonify({"error": "No valid combinations found without exam conflicts"}), 200

            # STEP 2: Check time conflicts
            debugprint("\n=== STEP 2: Checking Time Conflicts ===")
            valid_combinations = []
            for combination in combinations_without_exam_conflicts:
                if is_valid_combination(combination):
                    valid_combinations.append(combination)

            if not valid_combinations:
                return jsonify({"error": "No valid combinations found without time conflicts"}), 200

            # STEP 3: Check day/time preferences
            debugprint("\n=== STEP 3: Checking Day/Time Preferences ===")
            final_combinations = []
            for combination in valid_combinations:
                all_sections_valid = True
                for section in combination:
                    # Check if section schedules fit within selected times
                    valid_time, error = filter_section_by_time(section, times)
                    if not valid_time:
                        debugprint(f"✗ Time conflict: {error}")
                        all_sections_valid = False
                        break

                    # Check if section days are in selected days
                    section_days = set()
                    if section.get("sectionSchedule") and section["sectionSchedule"].get("classSchedules"):
                        section_days.update(schedule["day"].upper() 
                            for schedule in section["sectionSchedule"]["classSchedules"])
                    for lab in get_lab_schedules_flat(section):
                        section_days.add(lab["day"].upper())
                    
                    if not all(day.upper() in [d.upper() for d in days] for day in section_days):
                        debugprint(f"✗ Day conflict: {section.get('courseCode')} requires days not in selection")
                        all_sections_valid = False
                        break

                if all_sections_valid:
                    final_combinations.append(combination)

            if not final_combinations:
                return jsonify({"error": "No combinations found that match your day and time preferences"}), 200

            # If using AI, pass to AI routine generation
            if use_ai:
                debugprint("\n=== Using AI for Best Routine ===")
                # Sort combinations by campus days based on commute preference
                combinations_with_days = []
                for combination in final_combinations:
                    days_count, days_list = calculate_campus_days(combination)
                    combinations_with_days.append({
                        "combination": combination,
                        "campus_days": days_count,
                        "days_list": days_list
                    })

                # Sort based on commute preference
                if commute_preference == "far":
                    # For "Live Far", sort by ascending campus days (fewer days is better)
                    combinations_with_days.sort(key=lambda x: x["campus_days"])
                    debugprint("Sorted combinations by ascending campus days (fewer days is better)")
                else:
                    # For "Live Near" or no preference, sort by descending campus days (more days is better)
                    combinations_with_days.sort(key=lambda x: x["campus_days"], reverse=True)
                    debugprint("Sorted combinations by descending campus days (more days is better)")

                # Use the best combination
                best_combination = combinations_with_days[0]["combination"]
                debugprint(f"Selected best combination with {combinations_with_days[0]['campus_days']} campus days: {', '.join(combinations_with_days[0]['days_list'])}")
                return try_ai_routine_generation(best_combination, days, times, commute_preference)

            # Return the first valid combination
            debugprint("\n=== Using Manual Routine Generation ===")
            return jsonify({"routine": final_combinations[0]}), 200

    except Exception as e:
        debugprint(f"Error in generate_routine: {str(e)}")
        return jsonify({"error": "An error occurred while generating the routine"}), 500

def try_ai_routine_generation(valid_combination, selected_days, selected_times, commute_preference):
    """AI-assisted routine generation using Gemini AI."""
    try:
        debugprint("\n=== Using AI for Best Routine ===")
        
        # Check AI availability first
        ai_available, message = check_ai_availability()
        if not ai_available:
            debugprint(f"AI not available: {message}")
            return jsonify({"routine": valid_combination}), 200

        # Calculate routine score
        score = calculate_routine_score(valid_combination, selected_days, selected_times, commute_preference)
        debugprint(f"Routine score: {score}")

        # Get feedback
        feedback = get_routine_feedback_for_api(valid_combination, commute_preference)
        if feedback:
            debugprint("\nAI Feedback:")
            debugprint(feedback)

        return jsonify({
            "routine": valid_combination,
            "score": score,
            "feedback": feedback
        }), 200

    except Exception as e:
        debugprint(f"Error in AI routine generation: {e}")
        return jsonify({"routine": valid_combination}), 200

def get_routine_feedback_for_api(routine, commute_preference=None):
    """Get AI feedback for a routine."""
    try:
        # Check AI availability first
        ai_available, message = check_ai_availability()
        if not ai_available:
            debugprint(f"AI not available: {message}")
            return "AI feedback not available"

        # Get the days used in the routine
        days_used = get_days_used_in_routine(routine)
        days_str = ", ".join(days_used)
        num_days = len(days_used)
        
        debugprint("\n=== Generating AI Feedback ===")
        debugprint(f"Days used: {days_str} ({num_days} days)")
        debugprint(f"Commute preference: {commute_preference}")
        
        # Build the prompt with commute preference context
        prompt = f"Look at this routine:\n{json.dumps(routine)}\n\n"
        prompt += f"This routine requires being on campus for {num_days} day(s): {days_str}.\n"
        
        if commute_preference:
            prompt += f"The student's commute preference is '{commute_preference}'.\n"
            if commute_preference.lower() == "far":
                prompt += "For 'Live Far', fewer days on campus is better.\n"
            elif commute_preference.lower() == "near":
                prompt += "For 'Live Near', more days on campus is better.\n"
        
        prompt += (
            "First, rate this routine out of 10.\n"
            "Then give me 2-3 quick points about:\n"
            "• Schedule overview\n"
            "• What works well\n"
            "• Areas for improvement\n"
            "Keep it casual and under 10 words per point.\n"
            "Format your response exactly like this:\n"
            "Score: X/10\n"
            "Schedule: [brief overview]\n"
            "Good: [what works well]\n"
            "Needs Work: [areas to improve]"
        )

        debugprint("\nGenerating AI response...")
        response = gemini_model.generate_content(prompt)
        feedback = response.text.strip()
        debugprint("AI Feedback:", feedback)
        return feedback

    except Exception as e:
        debugprint(f"Error getting routine feedback: {e}")
        traceback.print_exc()
        return "Error generating AI feedback"


def auto_fix_json(s):
    # Count open/close braces and brackets
    open_braces = s.count("{")
    close_braces = s.count("}")
    open_brackets = s.count("[")
    close_brackets = s.count("]")
    # Add missing closing braces/brackets
    s += "}" * (open_braces - close_braces)
    s += "]" * (open_brackets - close_brackets)
    return s


def format24(time_str):
    # Converts "8:00 AM" to "08:00:00"
    debugprint(f"Converting to 24-hour format: {time_str}")
    try:
        dt = datetime.strptime(time_str.strip(), "%I:%M %p")
        result = dt.strftime("%H:%M:%S")
        debugprint(f"Converted {time_str} to {result} (24-hour format)")
        return result
    except Exception as e:
        debugprint(f"Error converting to 24-hour format: {e}")
        return time_str


def timeToMinutes(tstr):
    # Accepts "08:00:00" or "8:00 AM"
    if not tstr:
        debugprint(f"Warning: Empty time string")
        return 0

    tstr = tstr.strip()
    debugprint(f"Converting time to minutes: {tstr}")
    try:
        if "AM" in tstr or "PM" in tstr:
            dt = datetime.strptime(tstr, "%I:%M %p")
            minutes = dt.hour * 60 + dt.minute
            debugprint(f"Converted {tstr} to {minutes} minutes (12-hour format)")
            return minutes
        else:
            dt = datetime.strptime(tstr, "%H:%M:%S")
            minutes = dt.hour * 60 + dt.minute
            debugprint(f"Converted {tstr} to {minutes} minutes (24-hour format)")
            return minutes
    except Exception as e:
        debugprint(f"Error converting time to minutes: {e}")
        return 0


@app.route("/api/ask_ai", methods=["POST"])
def ask_ai():
    req = request.json
    question = req.get("question", "")
    routine_context = req.get("routine", None)

    if not question:
        return jsonify({"answer": "Please provide a question."}), 400

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")  # Using flash model for better performance

        # Create a context-aware prompt
        prompt = (
            "You are an AI assistant specifically for the USIS Routine Generator. "
            "Your role is to help students with their course schedules and academic planning. "
            "You should ONLY answer questions related to course scheduling, routine generation, "
            "and academic matters within this application.\n\n"
        )

        # If routine context is provided, add it to the prompt
        if routine_context:
            prompt += (
                "The student has generated the following routine:\n"
                f"{json.dumps(routine_context, indent=2)}\n\n"
                "When answering questions, refer to this routine if relevant.\n\n"
            )

        prompt += (
            "Question: " + question + "\n\n"
            "Instructions:\n"
            "1. Only answer questions related to course scheduling and academic planning\n"
            "2. If the question is about the current routine, provide specific feedback\n"
            "3. If the question is unrelated to the application, politely redirect to course scheduling topics\n"
            "4. Keep answers concise and focused on practical scheduling advice\n"
            "5. Format your response in clear, readable markdown\n"
        )

        response = model.generate_content(prompt)
        answer = response.text.strip()
        return jsonify({"answer": answer}), 200
    except Exception as e:
        print(f"Gemini API error during AI question answering: {e}")
        return (
            jsonify(
                {
                    "answer": "Sorry, I couldn't retrieve an answer at the moment. Please try again later.",
                    "error": str(e),
                }
            ),
            500,
        )


@app.route("/api/get_routine_feedback_ai", methods=["POST"])
def get_routine_feedback_ai():
    """Get AI feedback for a routine."""
    try:
        debugprint("\n=== Getting AI Routine Feedback ===")
        request_data = request.get_json()
        routine = request_data.get("routine", [])
        commute_preference = request_data.get("commutePreference", "")

        if not routine:
            debugprint("❌ No routine provided")
            return jsonify({"error": "No routine provided"}), 400

        debugprint(f"Getting feedback for routine with {len(routine)} sections")
        debugprint(f"Commute preference: {commute_preference}")

        feedback = get_routine_feedback_for_api(routine, commute_preference)
        debugprint("\nAI Feedback:", feedback)
        return jsonify({"feedback": feedback}), 200

    except Exception as e:
        debugprint(f"❌ Error in get_routine_feedback_ai: {e}")
        return jsonify({"error": "Failed to get AI feedback"}), 500

@app.route("/api/check_exam_conflicts_ai", methods=["POST"])
def check_exam_conflicts_ai():
    """Check for exam conflicts using AI."""
    try:
        debugprint("\n=== Checking Exam Conflicts (AI) ===")
        request_data = request.get_json()
        routine = request_data.get("routine", [])

        if not routine:
            debugprint("❌ No routine provided")
            return jsonify({"error": "No routine provided"}), 400

        debugprint(f"Checking {len(routine)} sections for exam conflicts")

        # Check AI availability
        ai_available, message = check_ai_availability()
        if not ai_available:
            debugprint(f"❌ AI not available: {message}")
            return jsonify({"error": "AI features are not available"}), 503

        # Get exam conflicts
        conflicts = check_and_return_exam_conflicts(routine)
        if conflicts:
            debugprint("\n❌ Exam conflicts found:")
            debugprint(conflicts)
            return jsonify({"conflicts": conflicts}), 200

        debugprint("\n✓ No exam conflicts found")
        return jsonify({"message": "No exam conflicts found"}), 200

    except Exception as e:
        debugprint(f"❌ Error in check_exam_conflicts_ai: {e}")
        return jsonify({"error": "Failed to check exam conflicts"}), 500


@app.route("/api/check_time_conflicts_ai", methods=["POST"])
def check_time_conflicts_ai():
    try:
        debugprint("\n=== Checking Time Conflicts (AI) ===")
        data = request.get_json()
        routine = data.get("routine", [])

        if not routine:
            debugprint("❌ No routine provided for analysis")
            return jsonify({"error": "No routine provided for analysis"}), 400

        debugprint(f"Checking {len(routine)} sections for time conflicts")

        # Check for time conflicts
        time_conflicts = []
        for i in range(len(routine)):
            section1 = routine[i]
            for j in range(i + 1, len(routine)):
                section2 = routine[j]
                debugprint(f"\nComparing {section1.get('courseCode')} with {section2.get('courseCode')}")

                # Check class schedules
                debugprint("Checking class-class conflicts...")
                for sched1 in section1.get("sectionSchedule", {}).get("classSchedules", []):
                    for sched2 in section2.get("sectionSchedule", {}).get("classSchedules", []):
                        if sched1.get("day") == sched2.get("day"):
                            start1 = TimeUtils.time_to_minutes(sched1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(sched1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(sched2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(sched2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                debugprint(f"❌ Found class-class conflict on {sched1.get('day')}")
                                time_conflicts.append({
                                    "type": "class-class",
                                    "course1": section1.get("courseCode"),
                                    "course2": section2.get("courseCode"),
                                    "day": sched1.get("day"),
                                    "time1": f"{sched1.get('startTime')} - {sched1.get('endTime')}",
                                    "time2": f"{sched2.get('startTime')} - {sched2.get('endTime')}",
                                })

                # Check lab schedules
                debugprint("Checking lab-lab conflicts...")
                for lab1 in section1.get("labSchedules", []):
                    for lab2 in section2.get("labSchedules", []):
                        if lab1.get("day") == lab2.get("day"):
                            start1 = TimeUtils.time_to_minutes(lab1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(lab1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(lab2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(lab2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                debugprint(f"❌ Found lab-lab conflict on {lab1.get('day')}")
                                time_conflicts.append({
                                    "type": "lab-lab",
                                    "course1": section1.get("courseCode"),
                                    "course2": section2.get("courseCode"),
                                    "day": lab1.get("day"),
                                    "time1": f"{lab1.get('startTime')} - {lab1.get('endTime')}",
                                    "time2": f"{lab2.get('startTime')} - {lab2.get('endTime')}",
                                })

                # Check lab-class and class-lab conflicts
                debugprint("Checking lab-class conflicts...")
                # Lab in section1 vs Class in section2
                for lab1 in section1.get("labSchedules", []):
                    for sched2 in section2.get("sectionSchedule", {}).get("classSchedules", []):
                        if lab1.get("day") == sched2.get("day"):
                            start1 = TimeUtils.time_to_minutes(lab1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(lab1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(sched2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(sched2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                debugprint(f"❌ Found lab-class conflict on {lab1.get('day')}")
                                time_conflicts.append({
                                    "type": "lab-class",
                                    "course1": section1.get("courseCode"),
                                    "course2": section2.get("courseCode"),
                                    "day": lab1.get("day"),
                                    "time1": f"{lab1.get('startTime')} - {lab1.get('endTime')}",
                                    "time2": f"{sched2.get('startTime')} - {sched2.get('endTime')}",
                                })

                # Class in section1 vs Lab in section2
                debugprint("Checking class-lab conflicts...")
                for sched1 in section1.get("sectionSchedule", {}).get("classSchedules", []):
                    for lab2 in section2.get("labSchedules", []):
                        if sched1.get("day") == lab2.get("day"):
                            start1 = TimeUtils.time_to_minutes(sched1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(sched1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(lab2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(lab2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                debugprint(f"❌ Found class-lab conflict on {sched1.get('day')}")
                                time_conflicts.append({
                                    "type": "class-lab",
                                    "course1": section1.get("courseCode"),
                                    "course2": section2.get("courseCode"),
                                    "day": sched1.get("day"),
                                    "time1": f"{sched1.get('startTime')} - {sched1.get('endTime')}",
                                    "time2": f"{lab2.get('startTime')} - {lab2.get('endTime')}",
                                })

        if not time_conflicts:
            debugprint("\n✓ No time conflicts found")
            prompt = (
                "Analyze this schedule for time management:\n"
                "• Any gaps in your schedule?\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: X/10'"
            )

            if gemini_model:
                debugprint("\nGenerating AI analysis...")
                response = gemini_model.generate_content(prompt)
                analysis = response.text.strip()
                debugprint("AI Analysis:", analysis)
            else:
                debugprint("❌ AI analysis unavailable")
                analysis = "AI analysis unavailable"

            return jsonify({"has_conflicts": False, "analysis": analysis}), 200
        else:
            debugprint(f"\n❌ Found {len(time_conflicts)} time conflicts")
            # Format the conflicts for the AI to analyze
            conflicts_text = "\n".join(
                [
                    f"- {conflict['type']} conflict between {conflict['course1']} and {conflict['course2']} on {conflict['day']}:\n  {conflict['course1']}: {conflict['time1']}\n  {conflict['course2']}: {conflict['time2']}"
                    for conflict in time_conflicts
                ]
            )
            debugprint("\nConflicts details:")
            debugprint(conflicts_text)

            prompt = (
                f"Here are your time conflicts:\n{conflicts_text}\n\n"
                "First, rate how bad these conflicts are out of 10 (10 being worst).\n"
                "Then give me 2-3 quick points:\n"
                "• How bad is it?\n"
                "• What can you do?\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: X/10'"
            )

            if gemini_model:
                debugprint("\nGenerating AI analysis of conflicts...")
                response = gemini_model.generate_content(prompt)
                analysis = response.text.strip()
                debugprint("AI Analysis:", analysis)
            else:
                debugprint("❌ AI analysis unavailable")
                analysis = "AI analysis unavailable"

            return (
                jsonify(
                    {
                        "has_conflicts": True,
                        "conflicts": time_conflicts,
                        "analysis": analysis,
                    }
                ),
                200,
            )

    except Exception as e:
        print(f"Error in check_time_conflicts_ai: {e}")
        return jsonify({"error": "Failed to analyze time conflicts"}), 500


@app.route("/api/exam_schedule")
def get_exam_schedule():
    course_code = request.args.get("courseCode")
    section_name = request.args.get("sectionName")
    if not course_code or not section_name:
        return jsonify({"error": "Missing courseCode or sectionName"}), 400

    # Find the section in the data
    for section in data:
        if section.get("courseCode") == course_code and str(
            section.get("sectionName")
        ) == str(section_name):
            # Return only the exam fields
            return jsonify(
                {
                    "courseCode": section.get("courseCode"),
                    "sectionName": section.get("sectionName"),
                    "midExamDate": section.get("midExamDate"),
                    "midExamStartTime": section.get("midExamStartTime"),
                    "midExamEndTime": section.get("midExamEndTime"),
                    "finalExamDate": section.get("finalExamDate"),
                    "finalExamStartTime": section.get("finalExamStartTime"),
                    "finalExamEndTime": section.get("finalExamEndTime"),
                }
            )
    return jsonify({"error": "Section not found"}), 404


def calculate_routine_score(
    combination, selected_days, selected_times, commute_preference
):
    """Calculate a score for a routine combination based on various factors."""
    score = 0

    # Convert selected times to minutes for easier comparison
    time_ranges = []
    for time_slot in selected_times:
        start, end = time_slot.split("-")
        start_mins = TimeUtils.time_to_minutes(start.strip())
        end_mins = TimeUtils.time_to_minutes(end.strip())
        time_ranges.append((start_mins, end_mins))

    # Score factors
    day_distribution = {day: [] for day in selected_days}  # Track classes per day
    gaps = []  # Track gaps between classes
    early_classes = 0  # Count of early morning classes
    late_classes = 0  # Count of late afternoon classes

    for section in combination:
        # Process class schedules
        if section.get("sectionSchedule") and section["sectionSchedule"].get(
            "classSchedules"
        ):
            for schedule in section["sectionSchedule"]["classSchedules"]:
                day = schedule.get("day", "").upper()
                if day in day_distribution:
                    start_time = TimeUtils.time_to_minutes(
                        schedule.get("startTime", "")
                    )
                    end_time = TimeUtils.time_to_minutes(schedule.get("endTime", ""))
                    day_distribution[day].append((start_time, end_time))

                    # Check timing preferences
                    if start_time < 540:  # Before 9:00 AM
                        early_classes += 1
                    if end_time > 960:  # After 4:00 PM
                        late_classes += 1

        # Process lab schedules
        for lab in get_lab_schedules_flat(section):
            day = lab.get("day", "").upper()
            if day in day_distribution:
                start_time = TimeUtils.time_to_minutes(lab.get("startTime", ""))
                end_time = TimeUtils.time_to_minutes(lab.get("endTime", ""))
                day_distribution[day].append((start_time, end_time))

                if start_time < 540:
                    early_classes += 1
                if end_time > 960:
                    late_classes += 1

    # Calculate scores for different factors

    # 1. Day distribution score (prefer balanced days)
    classes_per_day = [len(schedules) for schedules in day_distribution.values()]
    day_balance_score = -abs(
        max(classes_per_day) - min(classes_per_day)
    )  # Negative because we want to minimize difference
    score += day_balance_score * 2

    # 2. Gap score (minimize gaps between classes)
    for day, schedules in day_distribution.items():
        if len(schedules) > 1:
            # Sort schedules by start time
            schedules.sort(key=lambda x: x[0])
            for i in range(len(schedules) - 1):
                # Minutes between classes
                gap = schedules[i + 1][0] - schedules[i][1]
                if gap > 30:  # Only count gaps longer than 30 minutes
                    gaps.append(gap)

    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        gap_score = -avg_gap / 60  # Convert to hours and make negative
        score += gap_score

    # 3. Timing preference score
    if commute_preference == "early":
        score += (5 - late_classes) * 2  # Reward fewer late classes
    elif commute_preference == "late":
        score += (5 - early_classes) * 2  # Reward fewer early classes
    else:  # balanced
        score += -abs(early_classes - late_classes) * 2  # Reward balance

    # 4. Commute preference: days on campus
    days_on_campus = sum(1 for schedules in day_distribution.values() if schedules)
    if commute_preference == "far":
        # Fewer days is better
        score += (len(selected_days) - days_on_campus) * 10  # Strong weight
    elif commute_preference == "near":
        # Strongly prefer routines that use all available days
        if days_on_campus == len(selected_days):
            score += 1000  # Big bonus for using all available days
        else:
            score -= (len(selected_days) - days_on_campus) * 50  # Penalize missing days

    return score


def get_days_used_in_routine(routine):
    """Get a list of unique days used in the routine."""
    debugprint("\nGetting days used in routine")
    days_used = set()
    for section in routine:
        debugprint(f"\nProcessing section {section.get('courseCode')} {section.get('sectionName')}")
        # Check class schedules
        if section.get("sectionSchedule") and section["sectionSchedule"].get("classSchedules"):
            debugprint("Processing class schedules")
            for sched in section["sectionSchedule"]["classSchedules"]:
                if sched.get("day"):
                    day = sched["day"].upper()
                    days_used.add(day)
                    debugprint(f"Added class day: {day}")
        
        # Check lab schedules
        if section.get("labSchedules"):
            debugprint("Processing lab schedules")
            if isinstance(section["labSchedules"], list):
                for lab in section["labSchedules"]:
                    if lab.get("day"):
                        day = lab["day"].upper()
                        days_used.add(day)
                        debugprint(f"Added lab day: {day}")
            elif isinstance(section["labSchedules"], dict) and section["labSchedules"].get("classSchedules"):
                for lab_schedule in section["labSchedules"]["classSchedules"]:
                    if lab_schedule.get("day"):
                        day = lab_schedule["day"].upper()
                        days_used.add(day)
                        debugprint(f"Added lab day: {day}")
    
    days_list = sorted(list(days_used))
    debugprint(f"Total days used: {len(days_list)}")
    debugprint(f"Days: {', '.join(days_list)}")
    return days_list


def calculate_campus_days(combination):
    """Calculate the total number of unique days a student needs to be on campus."""
    debugprint("\nCalculating campus days for combination")
    days = set()
    for section in combination:
        if not isinstance(section, dict):
            debugprint(f"Warning: Invalid section format: {type(section)}")
            continue

        debugprint(f"\nProcessing section {section.get('courseCode')} {section.get('sectionName')}")
        # Check class schedules
        section_schedule = section.get("sectionSchedule", {})
        if isinstance(section_schedule, dict):
            class_schedules = section_schedule.get("classSchedules", [])
            if isinstance(class_schedules, list):
                debugprint("Processing class schedules")
                for schedule in class_schedules:
                    if isinstance(schedule, dict) and schedule.get("day"):
                        day = schedule["day"].upper()
                        days.add(day)
                        debugprint(f"Added class day: {day}")

        # Check lab schedules using the normalized helper function
        debugprint("Processing lab schedules")
        for lab_schedule in get_lab_schedules_flat(section):
            if isinstance(lab_schedule, dict) and lab_schedule.get("day"):
                day = lab_schedule["day"].upper()
                days.add(day)
                debugprint(f"Added lab day: {day}")

    days_list = sorted(list(days))
    debugprint(f"Total campus days: {len(days_list)}")
    debugprint(f"Days: {', '.join(days_list)}")
    return len(days), days_list


# Helper to normalize labSchedules to a flat array, supporting both array and object (with classSchedules) formats
def get_lab_schedules_flat(section):
    """Helper to normalize labSchedules to a flat array of schedules.
    Handles both old format (array of schedules) and new format (object with classSchedules)."""
    debugprint(f"\nGetting flat lab schedules for section {section.get('courseCode')} {section.get('sectionName')}")
    labSchedules = section.get("labSchedules")
    if not labSchedules:
        debugprint("No lab schedules found")
        return []

    # Handle old format: array of schedule objects
    if isinstance(labSchedules, list):
        debugprint("Processing old format (array of schedules)")
        schedules = [
            {
                **schedule,
                "room": section.get("labRoomName") or schedule.get("room") or "TBA",
                "faculty": section.get("labFaculties") or "TBA"
            }
            for schedule in labSchedules
        ]
        debugprint(f"Found {len(schedules)} lab schedules")
        for schedule in schedules:
            debugprint(f"Lab schedule: {schedule.get('day')} {schedule.get('startTime')}-{schedule.get('endTime')} in {schedule.get('room')}")
        return schedules

    # Handle new format: object with classSchedules array
    if isinstance(labSchedules, dict) and isinstance(labSchedules.get("classSchedules"), list):
        debugprint("Processing new format (object with classSchedules)")
        schedules = [
            {
                **schedule,
                "room": section.get("labRoomName") or schedule.get("room") or "TBA",
                "faculty": section.get("labFaculties") or "TBA"
            }
            for schedule in labSchedules["classSchedules"]
        ]
        debugprint(f"Found {len(schedules)} lab schedules")
        for schedule in schedules:
            debugprint(f"Lab schedule: {schedule.get('day')} {schedule.get('startTime')}-{schedule.get('endTime')} in {schedule.get('room')}")
        return schedules

    debugprint(f"Warning: Unrecognized lab schedule format: {type(labSchedules)}")
    return []


def convert_time_24_to_12(time_str):
    """Convert 24-hour time string to 12-hour format."""
    try:
        if not time_str:
            debugprint("Warning: Empty time string")
            return ""

        # Parse the time string
        time_parts = time_str.split(":")
        if len(time_parts) < 2:
            debugprint(f"Warning: Invalid time format: {time_str}")
            return time_str

        hours = int(time_parts[0])
        minutes = int(time_parts[1])

        # Convert to 12-hour format
        period = "AM" if hours < 12 else "PM"
        hours = hours % 12
        if hours == 0:
            hours = 12

        result = f"{hours}:{minutes:02d} {period}"
        debugprint(f"Converted {time_str} to {result}")
        return result

    except Exception as e:
        debugprint(f"Error converting time: {e}")
        return time_str

def format_section_times(section):
    """Format section times in a human-readable format."""
    try:
        debugprint(f"\nFormatting times for section {section.get('courseCode')}")
        times = []
        
        # Add class schedules
        if section.get("sectionSchedule") and section["sectionSchedule"].get("classSchedules"):
            debugprint("Processing class schedules")
            for schedule in section["sectionSchedule"]["classSchedules"]:
                start = convert_time_24_to_12(schedule.get("startTime", ""))
                end = convert_time_24_to_12(schedule.get("endTime", ""))
                day = schedule.get("day", "").title()
                if start and end and day:
                    time_str = f"{day} {start}-{end}"
                    times.append(time_str)
                    debugprint(f"Added class schedule: {time_str}")
        
        # Add lab schedules
        debugprint("Processing lab schedules")
        for lab in get_lab_schedules_flat(section):
            start = convert_time_24_to_12(lab.get("startTime", ""))
            end = convert_time_24_to_12(lab.get("endTime", ""))
            day = lab.get("day", "").title()
            if start and end and day:
                time_str = f"{day} {start}-{end} (Lab)"
                times.append(time_str)
                debugprint(f"Added lab schedule: {time_str}")
        
        debugprint(f"Formatted {len(times)} schedules")
        return times

    except Exception as e:
        debugprint(f"Error formatting section times: {e}")
        return []

def has_time_conflict(section1, section2):
    """Check if two sections have time conflicts."""
    try:
        debugprint(f"\nChecking time conflicts between {section1.get('courseCode')} and {section2.get('courseCode')}")
        
        # Get all schedules for both sections
        schedules1 = get_all_schedules(section1)
        schedules2 = get_all_schedules(section2)
        
        # Check each pair of schedules
        for sched1 in schedules1:
            for sched2 in schedules2:
                if not check_schedule_compatibility(sched1, sched2):
                    debugprint(f"Found time conflict:")
                    debugprint(f"Section 1: {section1.get('courseCode')} {sched1.get('day')} {sched1.get('startTime')}-{sched1.get('endTime')}")
                    debugprint(f"Section 2: {section2.get('courseCode')} {sched2.get('day')} {sched2.get('startTime')}-{sched2.get('endTime')}")
                    return True
        
        debugprint("No time conflicts found")
        return False

    except Exception as e:
        debugprint(f"Error checking time conflicts: {e}")
        return True  # Return True to be safe if there's an error

def get_course_details(course_code, show_all=False):
    """Get details for a specific course."""
    try:
        course_data = load_data()
        if not course_data:
            return None
            
        course_details = None
        for course in course_data:
            if course["courseCode"] == course_code:
                course_details = course
                break
                
        if not course_details:
            return None
            
        sections = course_details.get("sections", [])
        
        # Filter sections based on availability if show_all is False
        filtered_sections = []
        for section in sections:
            seats = section.get("availableSeats", 0)
            if show_all or seats > 0:
                filtered_sections.append(section)
                
        return filtered_sections
        
    except Exception as e:
        debugprint(f"Error in get_course_details: {str(e)}")
        return None

def filter_sections_by_faculty(sections, faculty):
    """Filter sections by faculty."""
    try:
        debugprint(f"\n=== Filtering Sections by Faculty: {faculty} ===")
        debugprint(f"Total sections before filtering: {len(sections)}")
        
        filtered = []
        for section in sections:
            section_faculty = section.get("faculty", "")
            section_name = section.get("sectionName", "Unknown")
            
            if section_faculty == faculty:
                debugprint(f"✓ Section {section_name} matches faculty {faculty}")
                filtered.append(section)
            else:
                debugprint(f"❌ Section {section_name} has different faculty: {section_faculty}")
                
        debugprint(f"Found {len(filtered)} sections for faculty {faculty}")
        return filtered
        
    except Exception as e:
        debugprint(f"❌ Error in filter_sections_by_faculty: {str(e)}")
        return []

if __name__ == "__main__":
    import logging
    # Disable Flask's default access logs
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Run the app with logging disabled
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)  # Production mode with logging disabled

app = app
