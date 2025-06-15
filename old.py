import requests
from flask import Flask, jsonify, request, send_file
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

# Only load dotenv locally (not on Vercel)
if not os.environ.get("VERCEL"):
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

app = Flask(__name__)
CORS(app)


@app.route("/api/test")
def test():
    return jsonify({"status": "ok", "message": "Backend is working!"})


# Load environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable is not set")

# Configure Gemini API
try:
    import google.generativeai as genai

    genai.configure(api_key=GOOGLE_API_KEY)
    print("Gemini API configured.")
except Exception as e:
    print(f"Failed to configure Gemini API: {e}")

# Initialize data as None
data = None


def load_data():
    global data
    if data is None:
        try:
            DATA_URL = "http://localhost:8000/raw-schedule"
            print(f"\nLoading data from {DATA_URL}...")

            # Add retry logic
            max_retries = 3
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1}/{max_retries}...")
                    response = requests.get(DATA_URL, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if not isinstance(data, list):
                        print(f"Warning: Expected list data, got {type(data)}")
                        continue

                    print(f"Successfully loaded {len(data)} sections")
                    return data

                except (
                    requests.exceptions.RequestException,
                    json.JSONDecodeError,
                ) as e:
                    print(f"Error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    continue

            print("All retry attempts failed. Setting data to empty list.")
            data = []
            return data

        except Exception as e:
            print(f"Critical error in load_data: {e}")
            print("Setting data to empty list.")
            data = []
            return data
    return data


def initialize_data():
    global data
    data = load_data()
    if data:
        print("\n=== Initializing Data ===")
        # Count sections with exam data
        sections_with_exams = 0
        for section in data:
            has_mid = bool(
                section.get("midExamDate")
                and section.get("midExamStartTime")
                and section.get("midExamEndTime")
            )
            has_final = bool(
                section.get("finalExamDate")
                and section.get("finalExamStartTime")
                and section.get("finalExamEndTime")
            )
            if has_mid or has_final:
                sections_with_exams += 1

        print(
            f"Found {sections_with_exams} sections with exam data out of {len(data)} total sections"
        )

        # If no exam data found, initialize with example data
        if sections_with_exams == 0:
            print("No exam data found, initializing example exam data...")
            for idx, section in enumerate(data):
                # Initialize midterm exam data
                if not (
                    section.get("midExamDate")
                    and section.get("midExamStartTime")
                    and section.get("midExamEndTime")
                ):
                    section["midExamDate"] = f"2024-07-{10 + (idx % 10):02d}"
                    section["midExamStartTime"] = "10:00:00"
                    section["midExamEndTime"] = "12:00:00"
                    print(
                        f"Added midterm exam data for {section.get('courseCode')} Section {section.get('sectionName')}"
                    )

                # Initialize final exam data
                if not (
                    section.get("finalExamDate")
                    and section.get("finalExamStartTime")
                    and section.get("finalExamEndTime")
                ):
                    section["finalExamDate"] = f"2024-08-{20 + (idx % 10):02d}"
                    section["finalExamStartTime"] = "14:00:00"
                    section["finalExamEndTime"] = "16:00:00"
                    print(
                        f"Added final exam data for {section.get('courseCode')} Section {section.get('sectionName')}"
                    )
        else:
            print("Exam data found in sections, no initialization needed")


# Initialize data when app starts
initialize_data()

# Add at the top of usis.py
BD_TIMEZONE = pytz.timezone("Asia/Dhaka")


# Create TimeUtils class
class TimeUtils:
    @staticmethod
    def convert_to_bd_time(time_str):
        """Convert time string to Bangladesh timezone."""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
            dt = datetime.now().replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=time_obj.second,
                microsecond=0,
            )
            bd_dt = BD_TIMEZONE.localize(dt)
            return bd_dt.strftime("%H:%M:%S")
        except Exception as e:
            print(f"Error converting time: {e}")
            return time_str

    @staticmethod
    def time_to_minutes(tstr):
        """Convert time string to minutes (handles both 24-hour and 12-hour formats)."""
        if not tstr:
            print(f"Warning: Empty time string")
            return 0

        tstr = tstr.strip().upper()
        print(f"Converting time to minutes: {tstr}")

        try:
            if "AM" in tstr or "PM" in tstr:
                if ":" not in tstr:
                    tstr = tstr.replace(" ", ":00 ")
                tstr = re.sub(r":\d+\s*(AM|PM)", r" \1", tstr)
                try:
                    dt = datetime.strptime(tstr, "%I:%M %p")
                except ValueError:
                    try:
                        dt = datetime.strptime(tstr, "%I:%M:%S %p")
                    except ValueError:
                        tstr = re.sub(
                            r"(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(AM|PM)", r"\1:\2 \3", tstr
                        )
                        tstr = (
                            tstr.replace(":", ":00:").split(":")[0:2].join(":")
                            + " "
                            + tstr.split()[-1]
                        )
                        dt = datetime.strptime(tstr, "%I:%M %p")
            else:
                parts = tstr.split(":")
                if len(parts) == 1:
                    dt = datetime.strptime(f"{int(parts[0]):02d}:00:00", "%H:%M:%S")
                elif len(parts) == 2:
                    dt = datetime.strptime(
                        f"{int(parts[0]):02d}:{int(parts[1]):02d}:00", "%H:%M:%S"
                    )
                else:
                    dt = datetime.strptime(
                        f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}",
                        "%H:%M:%S",
                    )

            minutes = dt.hour * 60 + dt.minute
            print(f"Converted {tstr} to {minutes} minutes")
            return minutes

        except Exception as e:
            print(f"Error in time_to_minutes: {tstr} - {e}")
            return 0


# Create an ExamConflictChecker class
class ExamConflictChecker:
    @staticmethod
    def check_conflicts(sections):
        # Combined conflict checking logic
        pass

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
    def repl(match):
        t = match.group(0)
        t = t[:5]
        in_time = datetime.strptime(t, "%H:%M")
        # Use %#I for Windows, %-I for others
        return in_time.strftime("%#I:%M %p")

    return re.sub(r"\b([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b", repl, text)


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
    return datetime.strptime(tstr, "%I:%M %p")


def slot_to_minutes(slot):
    start_str, end_str = slot.split("-")
    start = parse_time(start_str.strip())
    end = parse_time(end_str.strip())
    return start.hour * 60 + start.minute, end.hour * 60 + end.minute


def schedules_overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)


def exam_schedules_overlap(exam1, exam2):
    """Check if two exam schedules conflict based on date and time."""
    try:
        # First check if the exam dates match
        if exam1.get("examDate") != exam2.get("examDate"):
            return False  # Exams are on different days, no conflict

        # Convert times to minutes for comparison
        def convert_time(time_str):
            # Handle both 24-hour and 12-hour formats
            if isinstance(time_str, str):
                if "AM" in time_str.upper() or "PM" in time_str.upper():
                    # 12-hour format
                    try:
                        dt = datetime.strptime(time_str.strip(), "%I:%M %p")
                        return dt.hour * 60 + dt.minute
                    except ValueError:
                        try:
                            dt = datetime.strptime(time_str.strip(), "%I:%M:%S %p")
                            return dt.hour * 60 + dt.minute
                        except ValueError:
                            print(f"Warning: Could not parse 12-hour time: {time_str}")
                            return 0
                else:
                    # 24-hour format
                    try:
                        dt = datetime.strptime(time_str.strip(), "%H:%M:%S")
                        return dt.hour * 60 + dt.minute
                    except ValueError:
                        try:
                            dt = datetime.strptime(time_str.strip(), "%H:%M")
                            return dt.hour * 60 + dt.minute
                        except ValueError:
                            print(f"Warning: Could not parse 24-hour time: {time_str}")
                            return 0
            return 0

        start1 = convert_time(exam1.get("startTime", ""))
        end1 = convert_time(exam1.get("endTime", ""))
        start2 = convert_time(exam2.get("startTime", ""))
        end2 = convert_time(exam2.get("endTime", ""))

        # If any of the times are invalid (0), return True to be safe
        if start1 == 0 or end1 == 0 or start2 == 0 or end2 == 0:
            print(f"Warning: Invalid exam time detected. Assuming conflict for safety.")
            print(
                f"Times: {exam1.get('startTime')} - {exam1.get('endTime')} vs {exam2.get('startTime')} - {exam2.get('endTime')}"
            )
            return True

        # Check if the time ranges overlap
        return schedules_overlap(start1, end1, start2, end2)
    except Exception as e:
        print(f"Error comparing exam schedules: {e}")
        return True  # Assume conflict if parsing fails, to be safe


def check_exam_conflicts(section1, section2):
    """Check for conflicts between mid-term and final exams of two sections."""
    # Skip comparison if sections are the same or from the same course
    if section1.get("sectionId") == section2.get("sectionId") or section1.get(
        "courseCode"
    ) == section2.get("courseCode"):
        print(
            f"Skipping exam conflict check between sections of the same course or same section: {section1.get('courseCode')}"
        )
        return []

    print(
        f"=== Checking exam conflicts between {section1.get('courseCode')} Section {section1.get('sectionName')} ({section1.get('faculties')}) and {section2.get('courseCode')} Section {section2.get('sectionName')} ({section2.get('faculties')}) ==="
    )

    conflicts = []

    # Get all exam schedules
    exams1 = []
    exams2 = []

    # Get section schedules, prioritizing nested structure
    section1_schedule = section1.get("sectionSchedule", {})
    section2_schedule = section2.get("sectionSchedule", {})

    # Add mid-term exams if they exist - Prioritize from sectionSchedule
    mid1_date = section1_schedule.get("midExamDate") or section1.get("midExamDate")
    mid1_start = section1_schedule.get("midExamStartTime") or section1.get(
        "midExamStartTime"
    )
    mid1_end = section1_schedule.get("midExamEndTime") or section1.get("midExamEndTime")

    if mid1_date and mid1_start and mid1_end:
        print(
            f"{section1.get('courseCode')} Midterm: {mid1_date} {mid1_start}-{mid1_end}"
        )
        exams1.append(
            {
                "examDate": mid1_date,
                "startTime": mid1_start,
                "endTime": mid1_end,
                "type": "Mid",
            }
        )
    else:
        print(f"{section1.get('courseCode')} has no midterm exam data")

    mid2_date = section2_schedule.get("midExamDate") or section2.get("midExamDate")
    mid2_start = section2_schedule.get("midExamStartTime") or section2.get(
        "midExamStartTime"
    )
    mid2_end = section2_schedule.get("midExamEndTime") or section2.get("midExamEndTime")

    if mid2_date and mid2_start and mid2_end:
        print(
            f"{section2.get('courseCode')} Midterm: {mid2_date} {mid2_start}-{mid2_end}"
        )
        exams2.append(
            {
                "examDate": mid2_date,
                "startTime": mid2_start,
                "endTime": mid2_end,
                "type": "Mid",
            }
        )
    else:
        print(f"{section2.get('courseCode')} has no midterm exam data")

    # Add final exams if they exist - Prioritize from sectionSchedule
    final1_date = section1_schedule.get("finalExamDate") or section1.get(
        "finalExamDate"
    )
    final1_start = section1_schedule.get("finalExamStartTime") or section1.get(
        "finalExamStartTime"
    )
    final1_end = section1_schedule.get("finalExamEndTime") or section1.get(
        "finalExamEndTime"
    )

    if final1_date and final1_start and final1_end:
        print(
            f"{section1.get('courseCode')} Final: {final1_date} {final1_start}-{final1_end}"
        )
        exams1.append(
            {
                "examDate": final1_date,
                "startTime": final1_start,
                "endTime": final1_end,
                "type": "Final",
            }
        )
    else:
        print(f"{section1.get('courseCode')} has no final exam data")

    final2_date = section2_schedule.get("finalExamDate") or section2.get(
        "finalExamDate"
    )
    final2_start = section2_schedule.get("finalExamStartTime") or section2.get(
        "finalExamStartTime"
    )
    final2_end = section2_schedule.get("finalExamEndTime") or section2.get(
        "finalExamEndTime"
    )

    if final2_date and final2_start and final2_end:
        print(
            f"{section2.get('courseCode')} Final: {final2_date} {final2_start}-{final2_end}"
        )
        exams2.append(
            {
                "examDate": final2_date,
                "startTime": final2_start,
                "endTime": final2_end,
                "type": "Final",
            }
        )
    else:
        print(f"{section2.get('courseCode')} has no final exam data")

    # Check for conflicts between all exam combinations
    print("\nChecking for overlaps...")
    for exam1 in exams1:
        for exam2 in exams2:
            print(
                f"Comparing {section1.get('courseCode')} Section {section1.get('sectionName')} {exam1['type']} with {section2.get('courseCode')} Section {section2.get('sectionName')} {exam2['type']}"
            )
            if exam_schedules_overlap(exam1, exam2):
                print(
                    f"CONFLICT FOUND: {section1.get('courseCode')} Section {section1.get('sectionName')} {exam1['type']} and {section2.get('courseCode')} Section {section2.get('sectionName')} {exam2['type']} on {exam1['examDate']}"
                )
                conflicts.append(
                    {
                        "course1": section1["courseCode"],
                        "course2": section2["courseCode"],
                        "date": exam1["examDate"],
                        "type1": exam1["type"],
                        "type2": exam2["type"],
                        "time1": f"{exam1['startTime']} - {exam1['endTime']}",
                        "time2": f"{exam2['startTime']} - {exam2['endTime']}",
                    }
                )
            else:
                print(
                    f"No conflict found between {section1.get('courseCode')} Section {section1.get('sectionName')} {exam1['type']} and {section2.get('courseCode')} Section {section2.get('sectionName')} {exam2['type']}"
                )

    if not conflicts:
        print("No exam conflicts found between these sections")
    else:
        print(f"Found {len(conflicts)} conflicts!")

    return conflicts


def has_internal_conflicts(section):
    """Check if a single section has overlapping class or lab schedules."""
    schedules = []
    if section.get("sectionSchedule") and section["sectionSchedule"].get(
        "classSchedules"
    ):
        for sched in section["sectionSchedule"]["classSchedules"]:
            if sched.get("day") and sched.get("startTime") and sched.get("endTime"):
                schedules.append(
                    {
                        "day": sched["day"].upper(),
                        "start": TimeUtils.time_to_minutes(sched["startTime"]),
                        "end": TimeUtils.time_to_minutes(sched["endTime"]),
                    }
                )

    if section.get("labSchedules"):
        for lab in section["labSchedules"]:
            if lab.get("day") and lab.get("startTime") and lab.get("endTime"):
                schedules.append(
                    {
                        "day": lab["day"].upper(),
                        "start": TimeUtils.time_to_minutes(lab["startTime"]),
                        "end": TimeUtils.time_to_minutes(lab["endTime"]),
                    }
                )

    # Check for conflicts among all schedules in this section
    for i in range(len(schedules)):
        for j in range(i + 1, len(schedules)):
            if schedules[i]["day"] == schedules[j]["day"] and schedules_overlap(
                schedules[i]["start"],
                schedules[i]["end"],
                schedules[j]["start"],
                schedules[j]["end"],
            ):
                print(
                    f"Internal conflict found in section {section.get('courseCode')} {section.get('sectionName')}: {schedules[i]} conflicts with {schedules[j]}"
                )  # Debug print
                return True

    return False


@app.route("/api/courses")
def get_courses():
    data = load_data()
    # Get unique course codes and names, and calculate total available seats
    courses_data = {}
    for section in data:
        code = section.get("courseCode")
        name = section.get("courseName", code)
        available_seats = section.get("capacity", 0) - section.get("consumedSeat", 0)

        if code not in courses_data:
            courses_data[code] = {"code": code, "name": name, "totalAvailableSeats": 0}

        courses_data[code]["totalAvailableSeats"] += available_seats

    # Convert dictionary to list of course objects
    courses_list = list(courses_data.values())

    return jsonify(courses_list)


@app.route("/api/course_details")
def course_details():
    data = load_data()
    code = request.args.get("course")
    # Get all sections for the course
    all_sections = [section for section in data if section.get("courseCode") == code]

    # Filter out sections with no available seats
    details = []
    for section in all_sections:
        available_seats = section.get("capacity", 0) - section.get("consumedSeat", 0)
        if available_seats > 0:
            # Add available seats information
            section["availableSeats"] = available_seats

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
                if section["sectionSchedule"].get("classSchedules"):
                    for schedule in section["sectionSchedule"]["classSchedules"]:
                        schedule["formattedTime"] = convert_time_24_to_12(
                            f"{schedule['startTime']} - {schedule['endTime']}"
                        )

            # Format lab schedule information
            if section.get("labSchedules"):
                for schedule in section["labSchedules"]:
                    schedule["formattedTime"] = convert_time_24_to_12(
                        f"{schedule['startTime']} - {schedule['endTime']}"
                    )

            details.append(section)

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
    """Extract and format lab schedule information for a section."""
    lab_schedules = section.get("labSchedules", []) or []
    formatted_labs = []

    for lab in lab_schedules:
        day = lab.get("day", "").capitalize()
        start = lab.get("startTime")
        end = lab.get("endTime")
        room = lab.get("room", "TBA")

        if start and end:
            sched_start = TimeUtils.time_to_minutes(start)
            sched_end = TimeUtils.time_to_minutes(end)
            formatted_time = convert_time_24_to_12(f"{start} - {end}")

            formatted_labs.append(
                {
                    "day": day,
                    "startTime": start,
                    "endTime": end,
                    "formattedTime": formatted_time,
                    "room": room,
                    "startMinutes": sched_start,
                    "endMinutes": sched_end,
                }
            )

    return formatted_labs


def get_lab_schedule_bd(section):
    """Extract and format lab schedule information for a section, converting times to Bangladesh timezone (GMT+6)."""
    lab_schedules = section.get("labSchedules", []) or []
    formatted_labs = []
    for lab in lab_schedules:
        day = lab.get("day", "").capitalize()
        start = lab.get("startTime")
        end = lab.get("endTime")
        room = lab.get("room", "TBA")
        if start and end:
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
            except Exception:
                # Fallback: use original times
                start_str_bd = start
                end_str_bd = end
                formatted_time = convert_time_24_to_12(f"{start} - {end}")
                sched_start = TimeUtils.time_to_minutes(start)
                sched_end = TimeUtils.time_to_minutes(end)
            formatted_labs.append(
                {
                    "day": day,
                    "startTime": start_str_bd,
                    "endTime": end_str_bd,
                    "formattedTime": formatted_time,
                    "room": room,
                    "startMinutes": sched_start,
                    "endMinutes": sched_end,
                }
            )
    return formatted_labs


def check_lab_conflicts(section1, section2):
    """Check if two sections have conflicting lab schedules."""
    labs1 = get_lab_schedule(section1)
    labs2 = get_lab_schedule(section2)

    for lab1 in labs1:
        for lab2 in labs2:
            if lab1["day"] == lab2["day"] and schedules_overlap(
                lab1["startMinutes"],
                lab1["endMinutes"],
                lab2["startMinutes"],
                lab2["endMinutes"],
            ):
                return True
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
                # Using time1 as they overlap anyway
                "time": conflict["time1"],
            }
        if "Final" in (conflict["type1"], conflict["type2"]):
            final_conflicts[pair] = {
                "date": conflict["date"],
                "time": conflict["time1"],
            }

    if not mid_conflicts and not final_conflicts:
        return ""

    # Build message in the new format with proper line breaks
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
        if section.get("labSchedules"):
            for lab in section["labSchedules"]:
                if lab.get("day"):
                    required_days.add(lab["day"].upper())

    return required_days


def check_exam_compatibility(sections):
    """Check if a set of sections has any exam conflicts. Returns (has_conflicts, error_message)."""
    print("\n=== Checking Exam Compatibility for All Sections ===")
    exam_conflicts = []
    for i, section1 in enumerate(sections):
        for j in range(i + 1, len(sections)):
            section2 = sections[j]
            conflicts = check_exam_conflicts(section1, section2)
            if conflicts:
                print(
                    f"Found conflicts between {section1.get('courseCode')} and {section2.get('courseCode')}"
                )
                exam_conflicts.extend(conflicts)

    if exam_conflicts:
        error_message = format_exam_conflicts_message(exam_conflicts)
        print(f"\nExam conflicts found:\n{error_message}")
        return True, error_message

    print("No exam conflicts found in any combination")
    return False, None


def normalize_time(time_str):
    """Normalize time string to HH:MM:SS format."""
    if not time_str:
        return "00:00:00"

    time_str = time_str.strip().upper()
    print(f"Normalizing time: {time_str}")

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
            except ValueError:
                try:
                    dt = datetime.strptime(time_str, "%I:%M:%S %p")
                except ValueError:
                    # Try one more time with flexible parsing
                    time_str = re.sub(
                        r"(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(AM|PM)", r"\1:\2 \3", time_str
                    )
                    time_str = (
                        time_str.replace(":", ":00:").split(":")[0:2].join(":")
                        + " "
                        + time_str.split()[-1]
                    )
                    dt = datetime.strptime(time_str, "%I:%M %p")
            return dt.strftime("%H:%M:%S")
        else:
            # Handle 24-hour format
            parts = time_str.split(":")
            if len(parts) == 1:  # Just hours
                return f"{int(parts[0]):02d}:00:00"
            elif len(parts) == 2:  # Hours and minutes
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"
            else:  # Full time
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
    except Exception as e:
        print(f"Error normalizing time {time_str}: {e}")
        return "00:00:00"  # Return midnight if parsing fails


def filter_section_by_time(section, selected_times):
    """Check if section schedules fit within selected time ranges."""
    if not selected_times:  # If no times selected, accept all
        return True, "No time restrictions"

    def time_in_ranges(schedule_type, day, start_time, end_time):
        try:
            if not start_time or not end_time:
                return True, None  # Accept if missing time data

            # Normalize times
            start_time = normalize_time(start_time)
            end_time = normalize_time(end_time)

            start_minutes = TimeUtils.time_to_minutes(start_time)
            end_minutes = TimeUtils.time_to_minutes(end_time)

            # For lab sessions, we need to ensure ALL required time slots are
            # selected
            if schedule_type == "Lab":
                # Validate lab duration (should be at least 2 hours and 50
                # minutes)
                lab_duration = end_minutes - start_minutes
                if lab_duration < 170:  # 2 hours and 50 minutes = 170 minutes
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

                # Check if all required slots are selected
                if not all(slot in selected_times for slot in required_slots):
                    return (
                        False,
                        f"Lab session requires all time slots it spans to be selected: {', '.join(required_slots)}",
                    )
                return True, None

            # For regular classes, use the original overlap check
            for time_slot in selected_times:
                slot_start, slot_end = time_slot.split("-")
                slot_start = normalize_time(slot_start.strip())
                slot_end = normalize_time(slot_end.strip())
                range_start = TimeUtils.time_to_minutes(slot_start)
                range_end = TimeUtils.time_to_minutes(slot_end)

                if start_minutes <= range_end and end_minutes >= range_start:
                    return True, None

            return (
                False,
                f"{schedule_type} time {start_time}-{end_time} doesn't fit in any selected time slot",
            )

        except Exception as e:
            print(f"Error in time_in_ranges: {e}")
            return True, None  # Accept the section if there's an error in time parsing

    # Check class schedules
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
                return False, error

    # Check lab schedules
    if section.get("labSchedules"):
        for lab in section["labSchedules"]:
            valid, error = time_in_ranges(
                "Lab",
                lab.get("day", ""),
                lab.get("startTime", ""),
                lab.get("endTime", ""),
            )
            if not valid:
                return False, error

    return True, None


def check_schedule_compatibility(schedule1, schedule2):
    """Check if two schedules are compatible (no time conflicts)."""
    if schedule1["day"].upper() != schedule2["day"].upper():
        return True

    start1 = TimeUtils.time_to_minutes(normalize_time(schedule1["startTime"]))
    end1 = TimeUtils.time_to_minutes(normalize_time(schedule1["endTime"]))
    start2 = TimeUtils.time_to_minutes(normalize_time(schedule2["startTime"]))
    end2 = TimeUtils.time_to_minutes(normalize_time(schedule2["endTime"]))

    return not schedules_overlap(start1, end1, start2, end2)


def get_all_schedules(section):
    """Get all schedules (both class and lab) for a section."""
    schedules = []
    # Add class schedules
    if section.get("sectionSchedule") and section["sectionSchedule"].get(
        "classSchedules"
    ):
        schedules.extend(section["sectionSchedule"]["classSchedules"])
    # Add lab schedules
    if section.get("labSchedules"):
        schedules.extend(section["labSchedules"])
    return schedules


def is_valid_combination(sections):
    """Check if a combination of sections has any schedule conflicts."""
    for i, section1 in enumerate(sections):
        schedules1 = get_all_schedules(section1)

        # Check for internal conflicts in the same section
        for j, sched1 in enumerate(schedules1):
            for sched2 in schedules1[j + 1 :]:
                if not check_schedule_compatibility(sched1, sched2):
                    print(
                        f"Internal conflict in {section1.get('courseCode')} section {section1.get('sectionName')}"
                    )
                    return False

        # Check conflicts with other sections
        for section2 in sections[i + 1 :]:
            # Skip schedule compatibility check if sections are from the same
            # course and faculty
            if section1.get("courseCode") == section2.get(
                "courseCode"
            ) and section1.get("faculties") == section2.get("faculties"):
                print(
                    f"Skipping schedule compatibility check between sections of the same course and faculty: {section1.get('courseCode')} ({section1.get('faculties')})"
                )
                continue

            schedules2 = get_all_schedules(section2)
            for sched1 in schedules1:
                for sched2 in schedules2:
                    if not check_schedule_compatibility(sched1, sched2):
                        print(
                            f"Conflict between {section1.get('courseCode')} Section {section1.get('sectionName')} ({section1.get('faculties')}) and {section2.get('courseCode')} Section {section2.get('sectionName')} ({section2.get('faculties')})"
                        )
                        return False
    return True


def try_all_section_combinations(course_sections_map, selected_days, selected_times):
    """
    Try all possible combinations of sections for each course to find a valid routine.
    Returns (best_routine, error_message) tuple.
    """
    print("\n=== Starting Routine Generation ===")

    # First, check exam conflicts for all possible combinations before other
    # validations
    courses = list(course_sections_map.keys())
    print(f"\nGenerating combinations for courses: {', '.join(courses)}")

    all_section_combinations = list(
        product(*[course_sections_map[course] for course in courses])
    )
    print(f"\nGenerated {len(all_section_combinations)} possible combinations")

    # First pass: Check ONLY exam conflicts
    print("\n=== PHASE 1: Checking Exam Conflicts ===")
    valid_exam_combinations = []

    for combination in all_section_combinations:
        print(f"\nChecking combination:")
        for section in combination:
            print(
                f"  {section.get('courseCode')} Section {section.get('sectionName')}"
            )
            print(
                f"    Mid Exam: {section.get('midExamDate','N/A')} {section.get('midExamStartTime', 'N/A')}-{section.get('midExamEndTime','N/A')}"
            )
            print(
                f"    Final Exam: {section.get('finalExamDate','N/A')} {section.get('finalExamStartTime','N/A')}-{section.get('finalExamEndTime',  'N/A')}"
            )

        has_exam_conflicts, exam_error = check_exam_compatibility(combination)
        if has_exam_conflicts:
            print(f"✗ Exam conflict found: {exam_error}")
            continue
        else:
            print("✓ No exam conflicts found")
            valid_exam_combinations.append(combination)

    if not valid_exam_combinations:
        error_msg = "No valid combinations found without exam conflicts.\n"
        error_msg += "Please try different sections to avoid exam schedule conflicts."
        print(f"\n✗ {error_msg}")
        return None, error_msg

    print(
        f"\n✓ Found {
            len(valid_exam_combinations)} combinations without exam conflicts"
    )

    # Second pass: Check time and day constraints
    print("\n=== PHASE 2: Checking Time and Day Constraints ===")
    for combination in valid_exam_combinations:
        print("\nTrying combination without exam conflicts:")
        for section in combination:
            print(
                f"  {
                    section.get('courseCode')} Section {
                    section.get('sectionName')}"
            )

        # Check if all sections in this combination fit the selected days and
        # times
        all_sections_valid = True
        for section in combination:
            # Check times
            valid, time_error = filter_section_by_time(section, selected_times)
            if not valid:
                print(
                    f"✗ Invalid times for {
                        section.get('courseCode')} Section {
                        section.get('sectionName')}: {time_error}"
                )
                all_sections_valid = False
                break

            # Check days
            section_days = set()
            if section.get("sectionSchedule") and section["sectionSchedule"].get(
                "classSchedules"
            ):
                section_days.update(
                    schedule["day"].upper()
                    for schedule in section["sectionSchedule"]["classSchedules"]
                )
            if section.get("labSchedules"):
                section_days.update(
                    lab["day"].upper() for lab in section["labSchedules"]
                )

            if not all(
                day in [d.upper() for d in selected_days] for day in section_days
            ):
                print(
                    f"✗ Invalid days for {
                        section.get('courseCode')} Section {
                        section.get('sectionName')}"
                )
                all_sections_valid = False
                break

        if not all_sections_valid:
            continue

        # Finally check for schedule conflicts
        if is_valid_combination(combination):
            print("✓ Valid combination found!")
            return list(combination), None
        else:
            print("✗ Schedule conflict found")

    # If we get here, no valid combination was found
    print("\n✗ No valid combination found")
    return (
        None,
        "Could not find a valid combination without conflicts. Please try different sections or time slots.",
    )


@app.route("/api/routine", methods=["POST"])
def get_routine():
    try:
        print("\n=== Starting Routine Generation Request ===")

        # Validate request data
        if not request.json:
            return jsonify({"error": "Invalid request format"}), 400

        req = request.json
        course_faculty_pairs = req.get("courses", [])
        selected_days = [day.upper() for day in req.get("days", [])]
        selected_times = req.get("times", [])
        use_ai = req.get("useAI", False)
        commute_preference = req.get("commutePreference", "")

        print("\n=== Request Parameters ===")
        print(f"Selected days: {selected_days}")
        print(f"Selected times: {selected_times}")
        print(f"Course-faculty pairs: {json.dumps(course_faculty_pairs, indent=2)}")
        print(f"Using AI: {use_ai}")

        if not course_faculty_pairs:
            return jsonify({"error": "No courses selected"}), 200

        if not selected_days:
            return jsonify({"error": "No days selected"}), 200

        if not selected_times:
            return jsonify({"error": "No time slots selected"}), 200

        # Load and verify data
        print("\n=== Loading Data ===")
        data = load_data()
        if not data:
            return jsonify({"error": "Failed to load course data"}), 200

        # Build candidate sections map
        print("\n=== Building Course Sections Map ===")
        course_sections_map = {}

        for pair in course_faculty_pairs:
            course_code = pair.get("course")
            if not course_code:
                return jsonify({"error": "Invalid course data received"}), 200

            faculty_list = pair.get("faculty", [])
            selected_sections = pair.get("sections", {})

            print(f"\nProcessing {course_code}:")
            print(f"  Selected faculty: {faculty_list}")
            print(f"  Selected sections: {selected_sections}")

            # Get all sections for this course
            course_sections = [
                section
                for section in data
                if section.get("courseCode", "").upper() == course_code.upper()
            ]

            print(f"  Found {len(course_sections)} total sections")

            if not course_sections:
                return jsonify({"error": f"No sections found for {course_code}"}), 200

            # Filter by faculty and handle optional sections
            if faculty_list:
                filtered_sections = []
                for faculty in faculty_list:
                    print(f"  Filtering for faculty: {faculty}")
                    # Get all sections for this faculty
                    faculty_sections = [
                        section
                        for section in course_sections
                        if section.get("faculties", "").upper() == faculty.upper()
                    ]

                    # If specific section is selected for this faculty, use
                    # only that section
                    if faculty in selected_sections and selected_sections[faculty]:
                        specific_sections = [
                            section
                            for section in faculty_sections
                            if str(section.get("sectionName"))
                            == str(selected_sections[faculty])
                        ]
                        if specific_sections:
                            print(
                                f"    Using selected section {
                                    selected_sections[faculty]}"
                            )
                            filtered_sections.extend(specific_sections)
                        else:
                            print(
                                f"    Selected section {
                                    selected_sections[faculty]} not found"
                            )
                            filtered_sections.extend(faculty_sections)
                    else:
                        print(f"    Using all sections for faculty")
                        filtered_sections.extend(faculty_sections)

                if filtered_sections:
                    course_sections = filtered_sections
                    print(f"  Filtered to {len(course_sections)} sections")
                else:
                    return (
                        jsonify(
                            {
                                "error": f"No sections found for {course_code} with selected faculty"
                            }
                        ),
                        200,
                    )

            # Filter sections by available seats
            sections_with_seats = []
            for section in course_sections:
                available_seats = section.get("capacity", 0) - section.get(
                    "consumedSeat", 0
                )
                if available_seats > 0:
                    print(
                        f"  Section {
                            section.get('sectionName')} has {available_seats} seats available"
                    )
                    sections_with_seats.append(section)

            if not sections_with_seats:
                return (
                    jsonify(
                        {
                            "error": f"No sections with available seats found for {course_code}"
                        }
                    ),
                    200,
                )

            course_sections_map[course_code] = sections_with_seats
            print(
                f"Added {
                    len(sections_with_seats)} sections for {course_code} to course_sections_map"
            )

        # First check for exam conflicts across all selected sections
        print("\n=== Checking Exam Conflicts ===")
        all_selected_sections = {}
        for course_code, sections in course_sections_map.items():
            for section in sections:
                # Use sectionId to ensure uniqueness
                all_selected_sections[section.get("sectionId")] = section

        # Convert the dictionary values (unique sections) back to a list
        unique_selected_sections = list(all_selected_sections.values())

        exam_conflicts = []
        for i in range(len(unique_selected_sections)):
            section1 = unique_selected_sections[i]
            for j in range(i + 1, len(unique_selected_sections)):
                section2 = unique_selected_sections[j]
                conflicts = check_exam_conflicts(section1, section2)
                if conflicts:
                    exam_conflicts.extend(conflicts)

        if exam_conflicts:
            error_msg = format_exam_conflicts_message(exam_conflicts)
            print(f"\n✗ Found exam conflicts:\n{error_msg}")
            return jsonify({"error": error_msg}), 200

        # If no exam conflicts, proceed with routine generation
        if use_ai:
            result = try_ai_routine_generation(
                course_sections_map, selected_days, selected_times, commute_preference
            )
            # If routine generated, add AI feedback
            if result[1] == 200 and result[0].json.get("routine"):
                routine = result[0].json["routine"]
                feedback = get_routine_feedback_for_api(routine, commute_preference)
                result[0].json["feedback"] = feedback
            return result
        else:
            result = try_manual_routine_generation(
                course_sections_map, selected_days, selected_times
            )
            # Do NOT add AI feedback for manual routine
            return result

    except Exception as e:
        print(f"Error in get_routine: {str(e)}")
        return (
            jsonify(
                {"error": "An unexpected error occurred while generating the routine"}
            ),
            500,
        )


def try_manual_routine_generation(course_sections_map, selected_days, selected_times):
    """Fallback function for manual routine generation when AI fails."""
    try:
        print("=== Manual Routine Generation (Conflicts Skipped) ===")

        # Get all possible combinations first
        courses = list(course_sections_map.keys())
        all_combinations = list(
            product(*[course_sections_map[course] for course in courses])
        )
        print(f"Generated {len(all_combinations)} possible combinations")

        # Skip exam conflict check as requested
        # print("\n=== STEP 1: Checking Exam Conflicts ===")
        # combinations_without_exam_conflicts = []
        # for combination in all_combinations:
        #     has_exam_conflicts, exam_error = check_exam_compatibility(combination)
        #     if has_exam_conflicts:
        #         continue # Skip combinations with exam conflicts
        #     combinations_without_exam_conflicts.append(combination)

        # if not combinations_without_exam_conflicts:
        #     error_msg = "All possible combinations have exam conflicts.\n"
        #     error_msg += ("Please try different sections to avoid exam schedule conflicts.")
        #     return jsonify({"error": error_msg}), 200

        # print(f"\nFound {len(combinations_without_exam_conflicts)} combinations without exam conflicts")

        # Proceed directly to time and day constraints
        print("=== STEP 1 (was STEP 2): Checking Time and Day Constraints ===")
        # Iterate through all combinations directly
        for combination in all_combinations:
            print("\nChecking combination for time/day constraints:")
            for section in combination:
                print(
                    f"  {
                        section['courseCode']} Section {
                        section['sectionName']}"
                )

            # Check if all sections fit selected days and times
            all_sections_valid = True
            for section in combination:
                # Check times
                valid, time_error = filter_section_by_time(section, selected_times)
                if not valid:
                    print(f"✗ Invalid times: {time_error}")
                    all_sections_valid = False
                    break

                # Check days
                section_days = set()
                if section.get("sectionSchedule") and section["sectionSchedule"].get(
                    "classSchedules"
                ):
                    section_days.update(
                        schedule["day"].upper()
                        for schedule in section["sectionSchedule"]["classSchedules"]
                    )
                if section.get("labSchedules"):
                    section_days.update(
                        lab["day"].upper() for lab in section["labSchedules"]
                    )

                if not all(
                    day in [d.upper() for d in selected_days] for day in section_days
                ):
                    print("✗ Invalid days")
                    all_sections_valid = False
                    break

            if not all_sections_valid:
                continue

            # STEP 3: Check schedule conflicts
            if is_valid_combination(combination):
                print("✓ Valid combination found!")
                return jsonify({"routine": combination}), 200
            else:
                print("✗ Schedule conflict found")

        print("✗ No valid combination found")
        return (
            jsonify(
                {
                    "error": "Could not find a valid combination. Please check your selected time slots and days."
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error in manual routine generation: {e}")
        return (
            jsonify({"error": "Error generating routine manually. Please try again."}),
            200,
        )


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
    try:
        dt = datetime.strptime(time_str.strip(), "%I:%M %p")
        return dt.strftime("%H:%M:%S")
    except Exception:
        return time_str


def timeToMinutes(tstr):
    # Accepts "08:00:00" or "8:00 AM"
    tstr = tstr.strip()
    try:
        if "AM" in tstr or "PM" in tstr:
            dt = datetime.strptime(tstr, "%I:%M %p")
        else:
            dt = datetime.strptime(tstr, "%H:%M:%S")
        return dt.hour * 60 + dt.minute
    except Exception:
        return 0


@app.route("/api/ask_ai", methods=["POST"])
def ask_ai():
    req = request.json
    question = req.get("question", "")
    routine_context = req.get("routine", None)

    if not question:
        return jsonify({"answer": "Please provide a question."}), 400

    try:
        model = genai.GenerativeModel("gemini-1.5-flash-001")

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
    try:
        data = request.get_json()
        routine = data.get("routine", [])

        if not routine:
            return jsonify({"error": "No routine provided for analysis"}), 400

        prompt = (
            f"Look at this routine:\n{json.dumps(routine)}\n\n"
            "First, rate this routine out of 10.\n"
            "Then give me 2-3 quick points about:\n"
            "• How's your schedule looking?\n"
            "• What's good and what needs work?\n"
            "Keep it casual and under 10 words per point.\n"
            "Start with 'Score: X/10'"
        )

        model = genai.GenerativeModel("gemini-1.5-flash-001")
        response = model.generate_content(prompt)
        feedback = response.text.strip()

        return jsonify({"feedback": feedback}), 200
    except Exception as e:
        print(f"Error in get_routine_feedback_ai: {e}")
        return jsonify({"error": "Failed to analyze routine"}), 500


@app.route("/api/check_exam_conflicts_ai", methods=["POST"])
def check_exam_conflicts_ai():
    try:
        data = request.get_json()
        routine = data.get("routine", [])

        if not routine:
            return jsonify({"error": "No routine provided for analysis"}), 400

        # Helper: Generate markdown table of exam dates
        def exam_dates_table(routine):
            header = "| Course | Midterm Date | Final Date |\n|--------|--------------|------------|\n"
            rows = []
            for section in routine:
                course = section.get("courseCode", "")
                mid = section.get("midExamDate", "N/A")
                final = section.get("finalExamDate", "N/A")
                rows.append(f"| {course} | {mid} | {final} |\n")
            return header + "".join(rows)

        exam_table = exam_dates_table(routine)

        # First check for conflicts using the existing function
        exam_conflicts = []
        for i in range(len(routine)):
            section1 = routine[i]
            for j in range(i + 1, len(routine)):
                section2 = routine[j]
                conflicts = check_exam_conflicts(section1, section2)
                exam_conflicts.extend(conflicts)

        if not exam_conflicts:
            # No conflicts: ask the AI to summarize the exam schedule, not to
            # look for conflicts
            prompt = (
                f"Here is a university routine's exam schedule (see table below):\n\n"
                f"{exam_table}\n\n"
                f"Full routine data:\n{json.dumps(routine)}\n\n"
                "Summarize the exam schedule in 2-3 bullet points.\n"
                "Mention any busy weeks or tight schedules, but do NOT mention any conflicts.\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: 10/10' if there are no conflicts."
            )

            model = genai.GenerativeModel("gemini-1.5-flash-001")
            response = model.generate_content(prompt)
            analysis = response.text.strip()

            return jsonify({"has_conflicts": False, "analysis": analysis}), 200
        else:
            # Format the conflicts for the AI to analyze
            conflicts_text = "\n".join(
                [
                    f"- {
                        conflict['course1']} ({
                        conflict['type1']}) and {
                        conflict['course2']} ({
                        conflict['type2']}) "
                    f"have exams on {
                            conflict['date']}:\n"
                    f"  {
                                conflict['course1']}: {
                                    conflict['time1']}\n"
                    f"  {
                                        conflict['course2']}: {
                                            conflict['time2']}"
                    for conflict in exam_conflicts
                ]
            )

            prompt = (
                f"Here is a table of all exam dates for your routine:\n\n"
                f"{exam_table}\n\n"
                f"Here are your exam conflicts:\n{conflicts_text}\n\n"
                "First, rate how bad these conflicts are out of 10 (10 being worst).\n"
                "Then give me 2-3 quick points:\n"
                "• How bad is it?\n"
                "• What can you do?\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: X/10'"
            )

            model = genai.GenerativeModel("gemini-1.5-flash-001")
            response = model.generate_content(prompt)
            analysis = response.text.strip()

            return (
                jsonify(
                    {
                        "has_conflicts": True,
                        "conflicts": exam_conflicts,
                        "analysis": analysis,
                    }
                ),
                200,
            )

    except Exception as e:
        print(f"Error in check_exam_conflicts_ai: {e}")
        return jsonify({"error": "Failed to analyze exam conflicts"}), 500


@app.route("/api/check_time_conflicts_ai", methods=["POST"])
def check_time_conflicts_ai():
    try:
        data = request.get_json()
        routine = data.get("routine", [])

        if not routine:
            return jsonify({"error": "No routine provided for analysis"}), 400

        # Check for time conflicts
        time_conflicts = []
        for i in range(len(routine)):
            section1 = routine[i]
            for j in range(i + 1, len(routine)):
                section2 = routine[j]

                # Check class schedules
                for sched1 in section1.get("sectionSchedule", {}).get(
                    "classSchedules", []
                ):
                    for sched2 in section2.get("sectionSchedule", {}).get(
                        "classSchedules", []
                    ):
                        if sched1.get("day") == sched2.get("day"):
                            start1 = TimeUtils.time_to_minutes(sched1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(sched1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(sched2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(sched2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                time_conflicts.append(
                                    {
                                        "type": "class-class",
                                        "course1": section1.get("courseCode"),
                                        "course2": section2.get("courseCode"),
                                        "day": sched1.get("day"),
                                        "time1": f"{sched1.get('startTime')} - {sched1.get('endTime')}",
                                        "time2": f"{sched2.get('startTime')} - {sched2.get('endTime')}",
                                    }
                                )

                # Check lab schedules
                for lab1 in section1.get("labSchedules", []):
                    for lab2 in section2.get("labSchedules", []):
                        if lab1.get("day") == lab2.get("day"):
                            start1 = TimeUtils.time_to_minutes(lab1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(lab1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(lab2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(lab2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                time_conflicts.append(
                                    {
                                        "type": "lab-lab",
                                        "course1": section1.get("courseCode"),
                                        "course2": section2.get("courseCode"),
                                        "day": lab1.get("day"),
                                        "time1": f"{lab1.get('startTime')} - {lab1.get('endTime')}",
                                        "time2": f"{lab2.get('startTime')} - {lab2.get('endTime')}",
                                    }
                                )

                # Check lab-class and class-lab conflicts
                # Lab in section1 vs Class in section2
                for lab1 in section1.get("labSchedules", []):
                    for sched2 in section2.get("sectionSchedule", {}).get(
                        "classSchedules", []
                    ):
                        if lab1.get("day") == sched2.get("day"):
                            start1 = TimeUtils.time_to_minutes(lab1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(lab1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(sched2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(sched2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                time_conflicts.append(
                                    {
                                        "type": "lab-class",
                                        "course1": section1.get("courseCode"),
                                        "course2": section2.get("courseCode"),
                                        "day": lab1.get("day"),
                                        "time1": f"{lab1.get('startTime')} - {lab1.get('endTime')}",
                                        "time2": f"{sched2.get('startTime')} - {sched2.get('endTime')}",
                                    }
                                )
                # Class in section1 vs Lab in section2
                for sched1 in section1.get("sectionSchedule", {}).get(
                    "classSchedules", []
                ):
                    for lab2 in section2.get("labSchedules", []):
                        if sched1.get("day") == lab2.get("day"):
                            start1 = TimeUtils.time_to_minutes(sched1.get("startTime"))
                            end1 = TimeUtils.time_to_minutes(sched1.get("endTime"))
                            start2 = TimeUtils.time_to_minutes(lab2.get("startTime"))
                            end2 = TimeUtils.time_to_minutes(lab2.get("endTime"))

                            if schedules_overlap(start1, end1, start2, end2):
                                time_conflicts.append(
                                    {
                                        "type": "class-lab",
                                        "course1": section1.get("courseCode"),
                                        "course2": section2.get("courseCode"),
                                        "day": sched1.get("day"),
                                        "time1": f"{sched1.get('startTime')} - {sched1.get('endTime')}",
                                        "time2": f"{lab2.get('startTime')} - {lab2.get('endTime')}",
                                    }
                                )

        if not time_conflicts:
            prompt = (
                f"Check this routine for time conflicts:\n{
                    json.dumps(routine)}\n\n"
                "First, rate the time schedule out of 10.\n"
                "Then tell me in 2-3 points:\n"
                "• Any class/lab overlaps?\n"
                "• Any gaps in your schedule?\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: X/10'"
            )

            model = genai.GenerativeModel("gemini-1.5-flash-001")
            response = model.generate_content(prompt)
            analysis = response.text.strip()

            return jsonify({"has_conflicts": False, "analysis": analysis}), 200
        else:
            # Format the conflicts for the AI to analyze
            conflicts_text = "\n".join(
                [
                    f"- {
                        conflict['type']} conflict between {
                        conflict['course1']} and {
                        conflict['course2']} "
                    f"on {
                        conflict['day']}:\n"
                    f"  {
                            conflict['course1']}: {
                                conflict['time1']}\n"
                    f"  {
                                    conflict['course2']}: {
                                        conflict['time2']}"
                    for conflict in time_conflicts
                ]
            )

            prompt = (
                f"Here are your time conflicts:\n{conflicts_text}\n\n"
                "First, rate how bad these conflicts are out of 10 (10 being worst).\n"
                "Then give me 2-3 quick points:\n"
                "• How bad is it?\n"
                "• What can you do?\n"
                "Keep it casual and under 10 words per point.\n"
                "Start with 'Score: X/10'"
            )

            model = genai.GenerativeModel("gemini-1.5-flash-001")
            response = model.generate_content(prompt)
            analysis = response.text.strip()

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


def try_ai_routine_generation(
    course_sections_map, selected_days, selected_times, commute_preference
):
    """AI-assisted routine generation using Gemini AI."""
    try:
        print("\n=== AI Routine Generation with Gemini ===")

        # Get all possible combinations first
        courses = list(course_sections_map.keys())
        all_combinations = list(
            product(*[course_sections_map[course] for course in courses])
        )
        print(f"Generated {len(all_combinations)} possible combinations")

        # STEP 1: Check exam conflicts FIRST
        print("\n=== STEP 1: Checking Exam Conflicts ===")
        valid_combinations = []
        for combination in all_combinations:
            print("\nChecking combination for exam conflicts:")
            for section in combination:
                print(
                    f"  {
                        section['courseCode']} Section {
                        section['sectionName']}"
                )
                print(
                    f"    Mid Exam: {section.get('midExamDate',
                                                   'N/A')} at {section.get('midExamStartTime',
                                                                           'N/A')}-{section.get('midExamEndTime',
                                                                                                'N/A')}"
                )
                print(
                    f"    Final Exam: {section.get('finalExamDate',
                                                     'N/A')} at {section.get('finalExamStartTime',
                                                                             'N/A')}-{section.get('finalExamEndTime',
                                                                                                  'N/A')}"
                )

            has_exam_conflicts, exam_error = check_exam_compatibility(combination)
            if has_exam_conflicts:
                print(f"✗ Exam conflict found: {exam_error}")
                # Return the specific exam error message
                return jsonify({"error": exam_error}), 200

            print("✓ No exam conflicts found")

            # STEP 2: Check time and day constraints
            all_sections_valid = True
            for section in combination:
                # Check times
                valid, time_error = filter_section_by_time(section, selected_times)
                if not valid:
                    print(f"✗ Invalid times: {time_error}")
                    all_sections_valid = False
                    break

                # Check days
                section_days = set()
                if section.get("sectionSchedule") and section["sectionSchedule"].get(
                    "classSchedules"
                ):
                    section_days.update(
                        schedule["day"].upper()
                        for schedule in section["sectionSchedule"]["classSchedules"]
                    )
                if section.get("labSchedules"):
                    section_days.update(
                        lab["day"].upper() for lab in section["labSchedules"]
                    )

                if not all(
                    day in [d.upper() for d in selected_days] for day in section_days
                ):
                    print("✗ Invalid days")
                    all_sections_valid = False
                    break

            if not all_sections_valid:
                continue

            # STEP 3: Check schedule conflicts
            if is_valid_combination(combination):
                print("✓ Valid combination found!")
                valid_combinations.append(combination)
            else:
                print("✗ Schedule conflict found")

        if not valid_combinations:
            print("\n✗ No valid combinations found")
            return (
                jsonify(
                    {
                        "error": "Could not find a valid combination. Please check your selected time slots and days."
                    }
                ),
                200,
            )

        # Calculate campus days for each combination
        combinations_with_days = []
        print("\n=== Campus Days Analysis ===")
        for idx, combination in enumerate(valid_combinations):
            days_count, days_list = calculate_campus_days(combination)
            print(f"\nCombination {idx}:")
            print(f"  Total campus days: {days_count}")
            print(f"  Days required: {', '.join(days_list)}")

            combo_info = {
                "id": idx,
                "campus_days": days_count,
                "days_list": days_list,
                "combination": combination,
            }
            combinations_with_days.append(combo_info)

        # Sort combinations based on commute preference
        if commute_preference == "far":
            # For "Live Far", sort by ascending campus days (fewer days is
            # better)
            combinations_with_days.sort(key=lambda x: x["campus_days"])
        else:
            # For "Live Near" or no preference, sort by descending campus days
            # (more days is better)
            combinations_with_days.sort(key=lambda x: x["campus_days"], reverse=True)

        # Get the best campus days count
        best_days_count = combinations_with_days[0]["campus_days"]

        # Find all combinations that tie for the best campus days count
        tied_combinations = [
            combo
            for combo in combinations_with_days
            if combo["campus_days"] == best_days_count
        ]

        if len(tied_combinations) == 1:
            # No ties, use the best combination directly
            best_combination = tied_combinations[0]["combination"]
            print(f"\n✓ Selected combination with {best_days_count} campus days")
        else:
            # We have ties, use Gemini to break them
            print(
                f"\nFound {
                    len(tied_combinations)} combinations tied at {best_days_count} campus days"
            )
            print("Using Gemini to break the tie...")

            # Format combinations for Gemini
            formatted_combinations = []
            for combo in tied_combinations:
                combo_info = {
                    "id": combo["id"],
                    "campus_days": combo["campus_days"],
                    "days_list": combo["days_list"],
                    "courses": [],
                }

                for section in combo["combination"]:
                    course_info = {
                        "courseCode": section["courseCode"],
                        "section": section["sectionName"],
                        "schedules": [],
                    }

                    # Add class schedules
                    if section.get("sectionSchedule") and section[
                        "sectionSchedule"
                    ].get("classSchedules"):
                        for sched in section["sectionSchedule"]["classSchedules"]:
                            if sched["day"].upper() in selected_days:
                                course_info["schedules"].append(
                                    {
                                        "type": "class",
                                        "day": sched["day"].upper(),
                                        "time": f"{sched['startTime']} - {sched['endTime']}",
                                    }
                                )

                    # Add lab schedules
                    if section.get("labSchedules"):
                        for lab in section["labSchedules"]:
                            if lab["day"].upper() in selected_days:
                                course_info["schedules"].append(
                                    {
                                        "type": "lab",
                                        "day": lab["day"].upper(),
                                        "time": f"{lab['startTime']} - {lab['endTime']}",
                                    }
                                )

                    combo_info["courses"].append(course_info)
                formatted_combinations.append(combo_info)

            # Define commute text based on preference
            if commute_preference == "far":
                commute_text = (
                    "The student lives FAR from campus. Goal: MINIMISE campus visits by "
                    "grouping as many classes as possible on the same day."
                )
                commute_rule = (
                    "- Pack multiple classes per day\n"
                    "- Longer on-campus days are acceptable"
                )
            elif commute_preference == "near":
                commute_text = (
                    "The student lives NEAR campus. Goal: MAXIMISE campus presence by "
                    "spreading classes across MORE days (fewer classes per day)."
                )
                commute_rule = (
                    "- Distribute classes across the week\n"
                    "- Prefer short days (1–2 classes)"
                )
            else:
                commute_text = "The student has NO specific commute constraints."
                commute_rule = "- Provide a balanced, gap-free schedule"

            # First validate the number of combinations
            if len(formatted_combinations) == 0:
                print("\n⚠ No combinations to compare")
                return jsonify({"error": "No valid combinations found"}), 200

            max_id = len(formatted_combinations) - 1
            prompt = f"""
You are a university schedule optimizer. Break a tie between {len(formatted_combinations)} schedules that all require {best_days_count} campus days.

STUDENT PREFERENCE:
{commute_text}

WHAT MAKES A GOOD SCHEDULE:
1. Fewer gaps between classes = better
2. Classes in preferred time slots = better
3. Balanced workload across days = better
4. No back-to-back classes = better

SCHEDULES TO COMPARE:
{json.dumps(formatted_combinations, indent=2)}

YOUR TASK:
Pick the best schedule by comparing:
- How many gaps between classes
- How well they fit in preferred time slots
- How balanced the workload is
- How many back-to-back classes

RESPOND WITH EXACTLY 3 LINES AND NO OTHER TEXT:
BEST_ID: <A SINGLE INTEGER from 0 to {max_id} ONLY. This is the INDEX of the combination to choose.>
SCORE: <give a score from 1 to 10>
REASON: <one short sentence why this schedule is best>

Example (if there were {len(formatted_combinations)} combinations, with max_id {max_id}):
BEST_ID: {min(2, max_id)} # Example: pick 0, 1, or 2, but stay within the valid 0 to {max_id} range
SCORE: 8
REASON: This schedule has the fewest gaps and best fits preferred time slots.

IMPORTANT: You MUST provide a valid BEST_ID integer between 0 and {max_id} (inclusive). Your response format MUST be exactly 3 lines: BEST_ID, SCORE, REASON.
"""

            try:
                print("\nConsulting Gemini AI for tie-breaking...")
                model = genai.GenerativeModel("gemini-1.5-flash-001")
                response = model.generate_content(prompt)
                ai_response = response.text.strip()

                # Debug print the raw response
                print("\n=== Gemini Raw Response ===")
                print("Response type:", type(ai_response))
                print("Response length:", len(ai_response))
                print("Response content:")
                print("---")
                print(ai_response)
                print("---")

                # Debug print the response line by line
                print("\n=== Response Line Analysis ===")
                lines = ai_response.strip().split("\n")
                for i, line in enumerate(lines):
                    print(f"Line {i + 1}: '{line}'")

                # Parse Gemini response with more robust validation
                if len(lines) != 3:
                    print(
                        f"\n⚠ Invalid response format: expected 3 lines, got {
                            len(lines)}"
                    )
                    best_combination = tied_combinations[0]["combination"]
                    print("Using first combination as fallback")
                    return (
                        jsonify(
                            {
                                "routine": best_combination,
                                "feedback": "Selected schedule with optimal campus days.",
                            }
                        ),
                        200,
                    )

                best_id_line = lines[0].strip()
                if not best_id_line.startswith("BEST_ID:"):
                    print("\n⚠ Invalid response format: missing BEST_ID")
                    print(f"First line was: '{best_id_line}'")
                    best_combination = tied_combinations[0]["combination"]
                    print("Using first combination as fallback")
                    return (
                        jsonify(
                            {
                                "routine": best_combination,
                                "feedback": "Selected schedule with optimal campus days.",
                            }
                        ),
                        200,
                    )

                try:
                    best_id = int(best_id_line.split(":")[1].strip())
                    if not (0 <= best_id <= max_id):
                        print(
                            f"\n⚠ Invalid ID: {best_id} (must be between 0 and {max_id})"
                        )
                        # Use modulo to wrap around to a valid index
                        best_id = best_id % (max_id + 1)
                        print(f"Wrapped around to valid index: {best_id}")

                    best_combination = tied_combinations[best_id]["combination"]
                    print(f"\n✓ Gemini selected combination {best_id}")
                    print(f"AI Response:\n{ai_response}")
                except ValueError as e:
                    print(f"\n⚠ Could not parse ID from response: {e}")
                    print(f"Problematic line: '{best_id_line}'")
                    best_combination = tied_combinations[0]["combination"]
                    print("Using first combination as fallback")
                    return (
                        jsonify(
                            {
                                "routine": best_combination,
                                "feedback": "Selected schedule with optimal campus days.",
                            }
                        ),
                        200,
                    )

            except Exception as e:
                print(f"Error with Gemini AI: {e}")
                best_combination = tied_combinations[0]["combination"]
                print("\n⚠ Gemini error, using first combination")
                return (
                    jsonify(
                        {
                            "routine": best_combination,
                            "feedback": "Selected schedule with optimal campus days.",
                        }
                    ),
                    200,
                )

        # Format the schedules for the response
        for section in best_combination:
            section_schedules = []
            if section.get("sectionSchedule") and section["sectionSchedule"].get(
                "classSchedules"
            ):
                for sched in section["sectionSchedule"]["classSchedules"]:
                    if sched["day"].upper() in selected_days:
                        section_schedules.append(
                            {
                                "type": "class",
                                "day": sched["day"].upper(),
                                "start": TimeUtils.time_to_minutes(sched["startTime"]),
                                "end": TimeUtils.time_to_minutes(sched["endTime"]),
                                "schedule": sched,
                                "formattedTime": f"{sched['startTime']} - {sched['endTime']}",
                            }
                        )

            if section.get("labSchedules"):
                for lab in section["labSchedules"]:
                    if lab["day"].upper() in selected_days:
                        section_schedules.append(
                            {
                                "type": "lab",
                                "day": lab["day"].upper(),
                                "start": TimeUtils.time_to_minutes(lab["startTime"]),
                                "end": TimeUtils.time_to_minutes(lab["endTime"]),
                                "schedule": lab,
                                "formattedTime": f"{lab['startTime']} - {lab['endTime']}",
                            }
                        )

            section["formattedSchedules"] = section_schedules

        # Always include feedback in the response
        feedback = get_routine_feedback_for_api(best_combination, commute_preference)
        return jsonify({"routine": best_combination, "feedback": feedback}), 200

    except Exception as e:
        print(f"Error in AI routine generation: {e}")
        return (
            jsonify(
                {
                    "error": "Error generating routine with AI. Please try manual generation."
                }
            ),
            200,
        )


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
        if section.get("labSchedules"):
            for lab in section["labSchedules"]:
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


# Helper to get AI feedback for a routine
def get_routine_feedback_for_api(routine, commute_preference=None):
    try:
        import google.generativeai as genai

        model = genai.GenerativeModel("gemini-1.5-flash-001")
        # Get the days used in the routine
        days_used = get_days_used_in_routine(routine)
        days_str = ", ".join(days_used)
        num_days = len(days_used)
        commute_text = ""
        if commute_preference:
            commute_text = (
                f"The student's commute preference is '{commute_preference}'.\n"
            )
            if commute_preference.lower() == "far":
                commute_text += (
                    "For 'Live Far', fewer days on campus is better. "
                    "This routine requires being on campus for "
                    f"{num_days} day(s): {days_str}.\n"
                )
            elif commute_preference.lower() == "near":
                commute_text += (
                    "For 'Live Near', more days on campus is better. "
                    "This routine requires being on campus for "
                    f"{num_days} day(s): {days_str}.\n"
                )
            else:
                commute_text += f"This routine requires being on campus for {num_days} day(s): {days_str}.\n"
        else:
            commute_text = f"This routine requires being on campus for {num_days} day(s): {days_str}.\n"

        prompt = (
            f"Look at this routine:\n{json.dumps(routine)}\n\n"
            f"This routine requires being on campus for exactly {num_days} day(s): {days_str}.\n"
            f"The student's commute preference is '{commute_preference}'.\n"
            "When writing your feedback, always use the number of days provided above, and do not estimate or guess the number of days from the routine data.\n"
            "Assume all classes and labs are in-person (physical) unless explicitly marked as 'Online'. Do NOT say 'It's all online!' or make assumptions about online/physical mode.\n"
            "First, rate this routine out of 10.\n"
            "Then give me 2-3 quick points about:\n"
            "• How's your schedule looking?\n"
            "• What's good and what needs work?\n"
            "Keep it casual and under 10 words per point.\n"
            "Start with 'Score: X/10'"
        )
        response = model.generate_content(prompt)
        feedback = response.text.strip()
        return feedback
    except Exception as e:
        print(f"Gemini feedback error: {e}")
        return f"Gemini error: {e}"


def get_days_used_in_routine(routine):
    """Return a sorted list of unique days used in the routine."""
    days = set()
    # Ensure routine is a list and iterate safely
    for section in routine if isinstance(routine, list) else []:
        # Add a check here to skip None sections
        if section is None:
            continue
        # Class schedules
        for sched in (
            section.get("sectionSchedule", {}).get("classSchedules", [])
            if isinstance(
                section.get("sectionSchedule", {}).get("classSchedules"), list
            )
            else []
        ):
            if sched and sched.get("day"):
                days.add(sched["day"].capitalize())
        # Lab schedules
        for lab in (
            section.get("labSchedules", [])
            if isinstance(section.get("labSchedules"), list)
            else []
        ):
            if lab and lab.get("day"):
                days.add(lab["day"].capitalize())
    return sorted(
        days,
        key=lambda d: [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ].index(d),
    )


def calculate_campus_days(combination):
    """Calculate the total number of unique days a student needs to be on campus."""
    days = set()
    for section in combination:
        # Check class schedules
        if section.get("sectionSchedule") and section["sectionSchedule"].get(
            "classSchedules"
        ):
            for schedule in section["sectionSchedule"]["classSchedules"]:
                if schedule.get("day"):
                    days.add(schedule["day"].upper())

        # Check lab schedules
        if section.get("labSchedules"):
            for lab in section["labSchedules"]:
                if lab.get("day"):
                    days.add(lab["day"].upper())

    return len(days), sorted(list(days))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Add this for Vercel
app = app
