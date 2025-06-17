import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import Select from "react-select";
import './App.css';
import { format } from 'date-fns';
import html2canvas from 'html2canvas';
import AnimatedGridPattern from "./components/ui/animated-grid-pattern";
import SeatStatusDialog from "./SeatStatusDialog";
import { MessageCircle } from 'lucide-react';
import { API_BASE } from './config';
import ApiStatus from './components/ApiStatus';

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const TIME_SLOTS = [
  { value: "8:00 AM-9:20 AM", label: "8:00 AM-9:20 AM (BD Time)" },
  { value: "9:30 AM-10:50 AM", label: "9:30 AM-10:50 AM (BD Time)" },
  { value: "11:00 AM-12:20 PM", label: "11:00 AM-12:20 PM (BD Time)" },
  { value: "12:30 PM-1:50 PM", label: "12:30 PM-1:50 PM (BD Time)" },
  { value: "2:00 PM-3:20 PM", label: "2:00 PM-3:20 PM (BD Time)" },
  { value: "3:30 PM-4:50 PM", label: "3:30 PM-4:50 PM (BD Time)" },
  { value: "5:00 PM-6:20 PM", label: "5:00 PM-6:20 PM (BD Time)" }
];

// Helper: format 24-hour time string to 12-hour AM/PM
export const formatTime12Hour = (timeString) => {
    if (!timeString) return 'N/A';
    try {
        const [hours, minutes] = timeString.split(':').map(Number);
        const date = new Date();
        date.setHours(hours, minutes, 0, 0);
        return format(date, 'h:mm aa');
    } catch (error) {
        return timeString;
    }
};

// Helper function to normalize lab schedules to array format
const getLabSchedulesArray = (section) => {
  const labSchedules = section.labSchedules;
  if (!labSchedules) return [];
  if (Array.isArray(labSchedules)) return labSchedules;
  if (labSchedules.classSchedules && Array.isArray(labSchedules.classSchedules)) {
    return labSchedules.classSchedules.map(sched => ({
      ...sched,
      room: section.labRoomName || sched.room || "TBA"
    }));
  }
  return [];
};

function renderRoutineGrid(sections, selectedDays) {
  console.log("Rendering routine grid...");
  console.log("Sections received:", sections);
  console.log("Selected days:", selectedDays);
  
  // Helper to get abbreviated day name
  const getAbbreviatedDay = (day) => day.substring(0, 3);
  
  // Build a lookup: { [day]: { [timeSlotValue]: [entries, ...] } }
  const grid = {};
  for (const day of DAYS) {
    grid[day] = {};
    for (const slot of TIME_SLOTS.map(s => s.value)) {
      grid[day][slot] = [];
    }
  }

  // Helper function to format time for display
  const formatDisplayTime = (timeStr) => {
    if (!timeStr) return '';
    try {
      // Handle both 24-hour and 12-hour formats
      let hours, minutes;
      if (timeStr.includes(':')) {
        [hours, minutes] = timeStr.split(':').map(Number);
        if (timeStr.includes('AM') || timeStr.includes('PM')) {
          const period = timeStr.includes('PM');
          if (period && hours !== 12) hours += 12;
          if (!period && hours === 12) hours = 0;
        }
      } else {
        return timeStr;
      }
      const date = new Date();
      date.setHours(hours);
      date.setMinutes(minutes);
      return format(date, 'h:mm aa');
    } catch (error) {
      return timeStr;
    }
  };

  console.log("Iterating through sections for grid population:", sections);
  sections.forEach(section => {
    // Process class schedules
    if (section.sectionSchedule && section.sectionSchedule.classSchedules) {
      section.sectionSchedule.classSchedules.forEach(sched => {
        const day = sched.day.charAt(0).toUpperCase() + sched.day.slice(1).toLowerCase();
        if (!selectedDays.includes(day)) return;

        const startTime = formatDisplayTime(sched.startTime);
        const endTime = formatDisplayTime(sched.endTime);
        const formattedTime = `${startTime} - ${endTime}`;

        // Find matching time slot
        TIME_SLOTS.forEach(slot => {
          const [slotStart, slotEnd] = slot.value.split('-').map(t => t.trim());
          const schedStart = timeToMinutes(sched.startTime);
          const schedEnd = timeToMinutes(sched.endTime);
          const slotStartMin = timeToMinutes(slotStart);
          const slotEndMin = timeToMinutes(slotEnd);

          if (schedules_overlap(schedStart, schedEnd, slotStartMin, slotEndMin)) {
            grid[day][slot.value].push({
              type: "class",
              section: section,
              formattedTime: formattedTime,
              day: day,
              room: sched.room || section.roomName
            });
          }
        });
      });
    }

    // Process lab schedules
    const labSchedulesArr = getLabSchedulesArray(section);
    if (labSchedulesArr.length > 0) {
      labSchedulesArr.forEach(lab => {
        const day = lab.day.charAt(0).toUpperCase() + lab.day.slice(1).toLowerCase();
        if (!selectedDays.includes(day)) return;

        const startTime = formatDisplayTime(lab.startTime);
        const endTime = formatDisplayTime(lab.endTime);
        const formattedTime = `${startTime} - ${endTime}`;

        // Find matching time slot
        TIME_SLOTS.forEach(slot => {
          const [slotStart, slotEnd] = slot.value.split('-').map(t => t.trim());
          const labStart = timeToMinutes(lab.startTime);
          const labEnd = timeToMinutes(lab.endTime);
          const slotStartMin = timeToMinutes(slotStart);
          const slotEndMin = timeToMinutes(slotEnd);

          if (schedules_overlap(labStart, labEnd, slotStartMin, slotEndMin)) {
            grid[day][slot.value].push({
              type: "lab",
              section: section,
              formattedTime: formattedTime,
              day: day,
              room: lab.room || section.labRoomName
            });
          }
        });
      });
    }
  });

  // Helper to format room display
  const formatRoomDisplay = (entry) => {
    // If it's a simple room string, just return it
    if (typeof entry.room === 'string' && !entry.room.includes(';')) {
      return entry.room;
    }

    // If the room contains day/time information, extract the room for the current day
    const roomParts = entry.room.split(';').map(part => part.trim());
    for (const part of roomParts) {
      const dayMatch = part.toUpperCase().includes(entry.day.toUpperCase());
      if (dayMatch) {
        // Extract just the room number after the colon
        const roomNumber = part.split(':').pop().trim();
        return roomNumber;
      }
    }
    return 'TBA'; // Fallback if no room found for current day
  };

  return (
    <table className="routine-table">
      <thead>
        <tr>
          <th>Time/Day</th>
          {selectedDays.map(day => <th key={day}>{day.substring(0, 3)}</th>)}
        </tr>
      </thead>
      <tbody>
        {TIME_SLOTS.map(slot => (
          <tr key={slot.value}>
            <td>{slot.value}</td>
            {selectedDays.map(day => (
              <td key={day}>
                {grid[day][slot.value].map((entry, idx) => (
                  <div key={idx} className={entry.type === "class" ? "class-block" : "lab-block"}>
                    <div>
                      <span>{entry.type === "class" ? "Class" : "Lab"}</span>
                      {entry.section.courseCode}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {entry.section.sectionName && <div>Section: {entry.section.sectionName}</div>}
                      {entry.section.faculties && <div>Faculty: {entry.section.faculties}</div>}
                      {entry.room && <div>Room: {formatRoomDisplay(entry)}</div>}
                    </div>
                  </div>
                ))}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Helper to convert time string to minutes
function timeToMinutes(tstr) {
  tstr = tstr.trim();
  try {
    if (tstr.includes('AM') || tstr.includes('PM')) {
      const [time, period] = tstr.split(' ');
      let [h, m] = time.split(':').map(Number);
      if (period === 'PM' && h !== 12) h += 12;
      if (period === 'AM' && h === 12) h = 0;
      return h * 60 + m;
    } else if (tstr.includes(':')) {
      const [h, m] = tstr.split(':').map(Number);
      return h * 60 + m;
    } else {
      return 0;
    }
  } catch(e) {
    console.error("Error in timeToMinutes:", tstr, e);
    return 0;
  }
}

// Helper to check if two time ranges overlap (in minutes)
function schedules_overlap(start1, end1, start2, end2) {
  return Math.max(start1, start2) < Math.min(end1, end2);
}

// New Component: SeatStatusPage
const SeatStatusPage = ({ courses }) => {
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [sections, setSections] = useState([]);
  const [isLoadingSections, setIsLoadingSections] = useState(false);

  // Fetch course details when a course is selected
  useEffect(() => {
    if (selectedCourse) {
      setIsLoadingSections(true);
      axios.get(`${API_BASE}/course_details?course=${selectedCourse.value}`)
        .then(res => setSections(res.data))
        .catch(error => {
          console.error("Error fetching sections:", error);
          setSections([]); // Clear sections on error
        })
        .finally(() => setIsLoadingSections(false));
    } else {
      setSections([]);
      setIsLoadingSections(false);
    }
  }, [selectedCourse]);

  const sortedSections = sections.slice().sort((a, b) => {
    const nameA = a.sectionName || '';
    const nameB = b.sectionName || '';
    return nameA.localeCompare(nameB, undefined, { numeric: true, sensitivity: 'base' });
  });

  return (
    <div className="seat-status-container">
      <h2 className="seat-status-heading">Seat Status</h2>
      <div style={{ marginBottom: '18px', maxWidth: 400, marginLeft: 'auto', marginRight: 'auto' }}>
        <Select
          options={courses.map(c => ({ value: c.code, label: c.code }))}
          value={selectedCourse}
          onChange={setSelectedCourse}
          placeholder="Search and select a course..."
          isClearable={true}
          isSearchable={true}
        />
      </div>
      {isLoadingSections && (
        <div className="seat-status-message loading">Loading sections...</div>
      )}
      {!selectedCourse && !isLoadingSections && (
        <div className="seat-status-message info">Please select a course to view seat status.</div>
      )}
      {selectedCourse && !isLoadingSections && sections.length === 0 && (
        <div className="seat-status-message warning">No seat available for this course.</div>
      )}
      {selectedCourse && sections.length > 0 && (
        <div className="seat-status-table-wrapper">
          <table className="seat-status-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Faculty</th>
                <th>Seats</th>
                <th>Schedule</th>
                <th>Midterm Exam</th>
                <th>Final Exam</th>
              </tr>
            </thead>
            <tbody>
              {sortedSections.map(section => (
                <tr key={section.sectionId}>
                  <td>
                    <div style={{ fontWeight: '500' }}>{section.sectionName}</div>
                    <div style={{ fontSize: '0.9em', color: '#6c757d' }}>{section.courseCode}</div>
                  </td>
                  <td>{section.faculties || 'TBA'}</td>
                  <td>
                    <div className={
                      section.availableSeats > 10 ? 'seat-badge seat-available' :
                      section.availableSeats > 0 ? 'seat-badge seat-few' : 'seat-badge seat-full'
                    }>
                      {section.availableSeats} / {section.capacity}
                    </div>
                  </td>
                  <td>
                    {/* Class Schedule */}
                    {(section.sectionSchedule?.classSchedules || []).map((schedule, index) => (
                      <div key={index} className="class-schedule">
                        <span className="schedule-day">{schedule.day}</span>{' '}
                        <span>{formatTime12Hour(schedule.startTime)} - {formatTime12Hour(schedule.endTime)}</span>
                        {schedule.room && (
                          <span className="schedule-room"> ({schedule.room})</span>
                        )}
                      </div>
                    ))}
                    {/* Lab Schedule */}
                    {getLabSchedulesArray(section).map((schedule, index) => (
                      <div key={index} className="lab-schedule">
                        <span className="schedule-day">Lab: {schedule.day}</span>{' '}
                        <span>{formatTime12Hour(schedule.startTime)} - {formatTime12Hour(schedule.endTime)}</span>
                        {schedule.room && (
                          <span className="schedule-room"> ({schedule.room})</span>
                        )}
                      </div>
                    ))}
                  </td>
                  <td>
                    {section.midExamDate ? (
                      <>
                        <div>{section.midExamDate}</div>
                        {section.formattedMidExamTime && <div style={{ color: '#666', fontSize: '0.97em' }}>{section.formattedMidExamTime}</div>}
                      </>
                    ) : (
                      <span style={{ color: '#aaa', fontStyle: 'italic' }}>Not Scheduled</span>
                    )}
                  </td>
                  <td>
                    {section.finalExamDate ? (
                      <>
                        <div>{section.finalExamDate}</div>
                        {section.formattedFinalExamTime && <div style={{ color: '#666', fontSize: '0.97em' }}>{section.formattedFinalExamTime}</div>}
                      </>
                    ) : (
                      <span style={{ color: '#aaa', fontStyle: 'italic' }}>Not Scheduled</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Add ExamConflictMessage component before App component
const ExamConflictMessage = ({ message }) => {
  // Parse the message into sections
  const sections = {
    courses: [],
    midtermConflicts: [],
    finalConflicts: []
  };

  // Get unique course codes from the first "Affected Courses" section only
  const coursesMatch = message.match(/^Exam Conflicts\n\nAffected Courses:\s*([^\n]*)/m);
  if (coursesMatch) {
    sections.courses = [...new Set(
      coursesMatch[1]
        .split(/[,\s]+/)
        .map(c => c.trim())
        .filter(Boolean)
    )];
  }

  // Extract midterm conflicts
  const midtermMatch = message.match(/Midterm Conflicts\n([^]*?)(?=\nFinal Conflicts|$)/s);
  if (midtermMatch) {
    sections.midtermConflicts = midtermMatch[1]
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.includes('↔') || line.includes('->'));
  }

  // Extract final conflicts
  const finalMatch = message.match(/Final Conflicts\n([^]*?)$/s);
  if (finalMatch) {
    sections.finalConflicts = finalMatch[1]
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.includes('↔') || line.includes('->'));
  }

  return (
    <div style={{
      backgroundColor: '#fff3f3',
      border: '1px solid #ffcdd2',
      borderRadius: '8px',
      padding: '20px',
      margin: '16px 0',
      color: '#d32f2f',
      fontSize: '0.95em',
      lineHeight: '1.5'
    }}>
      <div style={{ 
        fontWeight: 'bold', 
        marginBottom: '16px', 
        fontSize: '1.2em',
        textAlign: 'center',
        color: '#c62828'
      }}>
        Exam Conflicts
      </div>
      
      <div style={{ 
        marginBottom: '20px',
        textAlign: 'center',
        padding: '8px',
        backgroundColor: 'rgba(255, 205, 210, 0.2)',
        borderRadius: '4px'
      }}>
        <strong>Affected Courses:</strong>{' '}
        {sections.courses.map((course, i) => (
          <span key={i} style={{
            display: 'inline-block',
            margin: '0 4px',
            padding: '2px 8px',
            backgroundColor: 'rgba(255, 205, 210, 0.5)',
            borderRadius: '4px',
            fontWeight: '500'
          }}>
            {course}
          </span>
        ))}
      </div>

      {sections.midtermConflicts.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <div style={{ 
            fontWeight: 'bold', 
            marginBottom: '12px', 
            color: '#c62828',
            borderBottom: '1px solid rgba(198, 40, 40, 0.2)',
            paddingBottom: '4px'
          }}>
            Midterm Conflicts
          </div>
          {sections.midtermConflicts.map((conflict, index) => (
            <div key={index} style={{ 
              marginBottom: '8px',
              padding: '12px',
              backgroundColor: 'rgba(255, 205, 210, 0.2)',
              borderRadius: '6px',
              fontSize: '0.95em'
            }}>
              {conflict}
            </div>
          ))}
        </div>
      )}

      {sections.finalConflicts.length > 0 && (
        <div>
          <div style={{ 
            fontWeight: 'bold', 
            marginBottom: '12px', 
            color: '#c62828',
            borderBottom: '1px solid rgba(198, 40, 40, 0.2)',
            paddingBottom: '4px'
          }}>
            Final Conflicts
          </div>
          {sections.finalConflicts.map((conflict, index) => (
            <div key={index} style={{ 
              marginBottom: '8px',
              padding: '12px',
              backgroundColor: 'rgba(255, 205, 210, 0.2)',
              borderRadius: '6px',
              fontSize: '0.95em'
            }}>
              {conflict}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Add ExamSchedule component before RoutineResult
const ExamSchedule = ({ sections }) => {
  // Extract and organize exam dates
  const examDates = sections.map(section => {
    return {
      courseCode: section.courseCode,
      sectionName: section.sectionName,
      midExamDate: section.sectionSchedule?.midExamDate || null,
      midExamStartTime: section.sectionSchedule?.midExamStartTime || null,
      midExamEndTime: section.sectionSchedule?.midExamEndTime || null,
      midExamTime: section.sectionSchedule?.midExamStartTime && section.sectionSchedule?.midExamEndTime ? 
        `${formatTime12Hour(section.sectionSchedule.midExamStartTime)} - ${formatTime12Hour(section.sectionSchedule.midExamEndTime)}` : null,
      finalExamDate: section.sectionSchedule?.finalExamDate || null,
      finalExamStartTime: section.sectionSchedule?.finalExamStartTime || null,
      finalExamEndTime: section.sectionSchedule?.finalExamEndTime || null,
      finalExamTime: section.sectionSchedule?.finalExamStartTime && section.sectionSchedule?.finalExamEndTime ? 
        `${formatTime12Hour(section.sectionSchedule.finalExamStartTime)} - ${formatTime12Hour(section.sectionSchedule.finalExamEndTime)}` : null
    };
  });

  return (
    <div style={{
      marginTop: "40px",
      padding: "24px",
      backgroundColor: "#ffffff",
      borderRadius: "12px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
      border: "1px solid #e0e0e0"
    }}>
      <h3 style={{ 
        textAlign: 'center', 
        marginBottom: '24px',
        color: '#222',
        fontSize: '1.4em',
        fontWeight: '600',
        borderBottom: '2px solid #f0f0f0',
        paddingBottom: '12px'
      }}>
        Exam Dates
      </h3>
      <div style={{ overflowX: 'auto' }}>
        <table className="routine-table">
          <thead>
            <tr>
              <th>Course</th>
              <th>Section</th>
              <th>Midterm Exam</th>
              <th>Final Exam</th>
            </tr>
          </thead>
          <tbody>
            {examDates.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#888', padding: '12px', fontStyle: 'italic' }}>
                  No exams scheduled.
                </td>
              </tr>
            ) : (
              examDates.map((exam, index) => (
                <tr key={index}>
                  <td>{exam.courseCode}</td>
                  <td>{exam.sectionName}</td>
                                     <td>
                     {exam.midExamDate ? (
                       <>
                         <div>{exam.midExamDate}</div>
                         <div style={{ color: '#666', fontSize: '0.97em' }}>{exam.midExamTime}</div>
                       </>
                     ) : (
                       <span style={{ color: '#aaa', fontStyle: 'italic' }}>Not Scheduled</span>
                     )}
                   </td>
                   <td>
                     {exam.finalExamDate ? (
                       <>
                         <div>{exam.finalExamDate}</div>
                         <div style={{ color: '#666', fontSize: '0.97em' }}>{exam.finalExamTime}</div>
                       </>
                     ) : (
                       <span style={{ color: '#aaa', fontStyle: 'italic' }}>Not Scheduled</span>
                     )}
                   </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Add CampusDaysDisplay component before RoutineResult
const CampusDaysDisplay = ({ routine }) => {
  if (!routine || !Array.isArray(routine)) return null;

  const days = new Set();
  routine.forEach(section => {
    // Add class schedule days
    if (section.sectionSchedule?.classSchedules) {
      section.sectionSchedule.classSchedules.forEach(sched => {
        days.add(sched.day.toUpperCase());
      });
    }
    // Add lab schedule days using getLabSchedulesArray helper
    const labSchedules = getLabSchedulesArray(section);
    if (labSchedules.length > 0) {
      labSchedules.forEach(lab => {
        days.add(lab.day.toUpperCase());
      });
    }
  });

  const sortedDays = Array.from(days).sort((a, b) => {
    const dayOrder = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
    return dayOrder.indexOf(a) - dayOrder.indexOf(b);
  });

  return (
    <div style={{ 
      marginBottom: '20px', 
      padding: '15px',
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      border: '1px solid #e9ecef'
    }}>
      <h4 style={{ margin: '0 0 10px 0', color: '#495057' }}>Campus Days</h4>
      <div style={{ fontSize: '1.1em' }}>
        <span style={{ fontWeight: 'bold' }}>Total Days: {sortedDays.length}</span>
        <br />
        <span style={{ color: '#6c757d' }}>
          Required Days: {sortedDays.join(', ')}
        </span>
      </div>
    </div>
  );
};

// Custom option component for the main course selection dropdown
const CourseOption = ({ innerRef, innerProps, data, isSelected }) => (
  <div ref={innerRef} {...innerProps} style={{ padding: '8px 12px', cursor: 'pointer', color: data.isDisabled ? '#aaa' : 'black' }}>
    <div>
      <span style={{ fontWeight: 'bold', textDecoration: data.isDisabled ? 'line-through' : 'none' }}>{data.label}</span>
      {data.isDisabled && (
        <span style={{ fontSize: '0.8em', color: '#dc3545', marginLeft: '10px' }}>(No Seats Available)</span>
      )}
    </div>
  </div>
);

// --- Make Routine Page ---
const MakeRoutinePage = () => {
  const [routineCourses, setRoutineCourses] = useState([]);
  const [availableCourses, setAvailableCourses] = useState([]); // Add this state
  const [availableFacultyByCourse, setAvailableFacultyByCourse] = useState({});
  const [selectedFacultyByCourse, setSelectedFacultyByCourse] = useState({});
  const [selectedSectionsByFaculty, setSelectedSectionsByFaculty] = useState({});
  const [courseSearchTerm, setCourseSearchTerm] = useState('');
  const [isCourseSuggestionsOpen, setIsCourseSuggestionsOpen] = useState(false);

  // Add useEffect to fetch courses
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await axios.get(`${API_BASE}/courses`);
        setAvailableCourses(response.data);
      } catch (error) {
        console.error('Error fetching courses:', error);
      }
    };
    fetchCourses();
  }, []);

  const [routineDays, setRoutineDays] = useState(DAYS.map(d => ({ value: d, label: d }))); // Reverted to include all days
  const [routineResult, setRoutineResult] = useState(null);
  const [routineFaculty, setRoutineFaculty] = useState(null);
  const [routineFacultyOptions, setRoutineFacultyOptions] = useState([]);
  const [routineTimes, setRoutineTimes] = useState(TIME_SLOTS);
  const [routineError, setRoutineError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiFeedback, setAiFeedback] = useState(null);
  const [commutePreference, setCommutePreference] = useState("");
  const [usedAI, setUsedAI] = useState(false);
  const [courseOptions, setCourseOptions] = useState([]);
  const [filteredCourseOptions, setFilteredCourseOptions] = useState([]);
  const [isDaySuggestionsOpen, setIsDaySuggestionsOpen] = useState(false); // Day suggestions list visibility

  const [daySearchTerm, setDaySearchTerm] = useState(''); // Input value for day search
  const [filteredDayOptions, setFilteredDayOptions] = useState(DAYS.map(d => ({ value: d, label: d }))); // Filtered day suggestions

  const [timeSearchTerm, setTimeSearchTerm] = useState(''); // Input value for time search
  const [filteredTimeOptions, setFilteredTimeOptions] = useState(TIME_SLOTS); // Filtered time suggestions
  const [isTimeSuggestionsOpen, setIsTimeSuggestionsOpen] = useState(false); // Time suggestions list visibility

  // Add state for faculty search and suggestions
  const [facultySearchTerm, setFacultySearchTerm] = useState({});
  const [filteredFacultyOptions, setFilteredFacultyOptions] = useState({});
  const [isFacultySuggestionsOpen, setIsFacultySuggestionsOpen] = useState({});

  // Add state for section search and suggestions (per course+faculty)
  const [sectionSearchTerm, setSectionSearchTerm] = useState({});
  const [filteredSectionOptions, setFilteredSectionOptions] = useState({});
  const [isSectionSuggestionsOpen, setIsSectionSuggestionsOpen] = useState({});

  const routineGridRef = useRef(null);

  // Function to handle PNG download
  const handleDownloadPNG = () => {
    if (routineGridRef.current) {
      const element = routineGridRef.current;
      
      // Create a temporary container with white background
      const tempContainer = document.createElement('div');
      tempContainer.style.position = 'absolute';
      tempContainer.style.left = '-9999px';
      tempContainer.style.background = '#ffffff';
      tempContainer.style.padding = '20px';
      
      // Clone the element and its children
      const clone = element.cloneNode(true);
      tempContainer.appendChild(clone);
      document.body.appendChild(tempContainer);

      // Set options for better quality and full capture
      const options = {
        scale: 2,
        backgroundColor: '#ffffff',
        logging: false,
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight,
        useCORS: true,
        allowTaint: true,
        onclone: (clonedDoc) => {
          const clonedElement = clonedDoc.querySelector('[data-routine-grid]');
          if (clonedElement) {
            clonedElement.style.width = `${element.scrollWidth}px`;
            clonedElement.style.height = `${element.scrollHeight}px`;
          }
        }
      };

      html2canvas(tempContainer, options).then(canvas => {
        // Remove the temporary container
        document.body.removeChild(tempContainer);

        // Create download link
        const link = document.createElement('a');
        link.download = 'routine.png';
        link.href = canvas.toDataURL('image/png', 1.0);
        link.click();
      });
    }
  };

  useEffect(() => {
    axios.get(`${API_BASE}/courses`).then(res => {
      // Prepare options for the main course select, including disabled state
      const options = res.data.map(course => ({
        value: course.code,
        label: course.code,
        isDisabled: course.totalAvailableSeats <= 0,
        totalAvailableSeats: course.totalAvailableSeats
      }));
      // Sort options alphabetically
      options.sort((a, b) => a.label.localeCompare(b.label));
      setCourseOptions(options);
      setFilteredCourseOptions(options);
    });
  }, []);

  // Handler and logic implementations (copied from previous working version)
  const handleCourseSelect = async (selectedOptions) => {
    setRoutineCourses(selectedOptions);
    for (const course of selectedOptions) {
      try {
        const res = await axios.get(`${API_BASE}/course_details?course=${course.value}`);
        const facultySections = {};
        res.data.forEach(section => {
          if (section.faculties) {
            const availableSeats = section.capacity - section.consumedSeat;
            if (availableSeats > 0) {
              if (!facultySections[section.faculties]) {
                facultySections[section.faculties] = {
                  sections: [],
                  totalSeats: 0,
                  availableSeats: 0
                };
              }
              facultySections[section.faculties].sections.push(section);
              facultySections[section.faculties].totalSeats += section.capacity;
              facultySections[section.faculties].availableSeats += availableSeats;
            }
          }
        });
        setAvailableFacultyByCourse(prev => ({ ...prev, [course.value]: facultySections }));
      } catch (error) {}
    }
    // Remove faculty data for unselected courses
    const selectedCourseCodes = selectedOptions.map(c => c.value);
    setAvailableFacultyByCourse(prev => {
      const newState = {};
      selectedCourseCodes.forEach(code => { if (prev[code]) newState[code] = prev[code]; });
      return newState;
    });
    setSelectedFacultyByCourse(prev => {
      const newState = {};
      selectedCourseCodes.forEach(code => { if (prev[code]) newState[code] = prev[code]; });
      return newState;
    });
    setSelectedSectionsByFaculty(prev => {
      const newState = {};
      selectedCourseCodes.forEach(code => { if (prev[code]) newState[code] = prev[code]; });
      return newState;
    });
  };

  const handleFacultyChange = (courseValue, selected) => {
    setSelectedFacultyByCourse(prev => ({ ...prev, [courseValue]: selected }));
    // Clear section selections for unselected faculty
    setSelectedSectionsByFaculty(prev => {
      const newState = { ...prev };
      if (!newState[courseValue]) newState[courseValue] = {};
      const selectedFacultyValues = selected.map(f => f.value);
      Object.keys(newState[courseValue]).forEach(faculty => {
        if (!selectedFacultyValues.includes(faculty)) {
          delete newState[courseValue][faculty];
        }
      });
      return newState;
    });
  };

  const handleSectionChange = (courseValue, faculty, selectedSection) => {
    setSelectedSectionsByFaculty(prev => ({
      ...prev,
      [courseValue]: {
        ...(prev[courseValue] || {}),
        [faculty]: selectedSection
      }
    }));
  };

  const handleGenerateRoutine = (useAI) => {
    // Reset state
    setRoutineError("");
    setRoutineResult(null);
    setAiFeedback(null);
    setUsedAI(useAI);

    // Validate that at least two days are selected
    if (routineDays.length < 2) {
      setRoutineError("Please select at least two days. Classes typically require two days per week.");
      return;
    }

    // Validate commute preference for AI mode
    if (useAI && !commutePreference) {
      setRoutineError("Please select a commute preference (Live Far or Live Near) when using AI.");
      return;
    }

    // Get selected days in uppercase for comparison
    const selectedDays = routineDays.map(d => d.value.toUpperCase());

    setIsLoading(true);

    const courseFacultyMap = routineCourses.map(course => {
      const selectedFaculty = selectedFacultyByCourse[course.value] || [];
      const facultyWithSections = selectedFaculty.map(f => ({
        value: f.value,
        section: selectedSectionsByFaculty[course.value]?.[f.value]?.value || null
      }));

      return {
        course: course.value,
        faculty: facultyWithSections.map(f => f.value),
        sections: Object.fromEntries(
          facultyWithSections
            .filter(f => f.section)
            .map(f => [f.value, f.section])
        )
      };
    });

    axios.post(`${API_BASE}/routine`, {
      courses: courseFacultyMap,
      days: selectedDays,
      times: routineTimes.map(t => t.value),
      useAI: useAI,
      commutePreference: commutePreference
    }).then(res => {
      setIsLoading(false);
      
      // Check for error response from backend
      if (res.data && res.data.error) {
        setRoutineError(res.data.error);
        setRoutineResult(null);
        setAiFeedback(null);
        return;
      }

      let geminiResponse = res.data;

      // Handle potential nested routine structure from backend
      if (geminiResponse && geminiResponse.routine && Array.isArray(geminiResponse.routine)) {
        geminiResponse = geminiResponse.routine;
      } else if (!Array.isArray(geminiResponse)) {
        geminiResponse = geminiResponse ? [geminiResponse] : [];
      }

      // Ensure geminiResponse is an array before proceeding
      if (!Array.isArray(geminiResponse)) {
        console.error("Unexpected response format from backend:", res.data);
        setRoutineError('Failed to process routine response from backend.');
        setRoutineResult(null);
        setAiFeedback(null);
        return;
      }

      // Continue with existing validation for lab and class days
      const selectedDaysUpper = routineDays.map(d => d.value.toUpperCase());
      let labDayMismatch = false;
      let classDayMismatch = false;
      const mismatchedLabs = [];
      const mismatchedClasses = [];

      geminiResponse.forEach(section => {
        const requiredClassDays = section.sectionSchedule?.classSchedules?.map(s => s.day.toUpperCase()) || [];
        requiredClassDays.forEach(classDayUpper => {
          if (!selectedDaysUpper.includes(classDayUpper)) {
            classDayMismatch = true;
            mismatchedClasses.push(`${section.courseCode} (${classDayUpper})`);
          }
        });

        if (section.labSchedules && section.labSchedules.length > 0) {
          section.labSchedules.forEach(labSched => {
            const labDayUpper = labSched.day.toUpperCase();
            if (!selectedDaysUpper.includes(labDayUpper)) {
              labDayMismatch = true;
              mismatchedLabs.push(`${section.courseCode} Lab (${labSched.day})`);
            }
          });
        }
      });

      if (classDayMismatch || labDayMismatch) {
        let errorMessage = "Cannot generate routine with the selected days:\n\n";
        if (classDayMismatch) {
          errorMessage += `- Missing required class day(s) for: ${mismatchedClasses.join(', ')}\n`;
        }
        if (labDayMismatch) {
          errorMessage += `- Missing required lab day(s) for: ${mismatchedLabs.join(', ')}\n`;
        }
        errorMessage += "\nPlease select the necessary day(s) for all courses.";
        setRoutineError(errorMessage);
        return;
      }

      setRoutineResult(geminiResponse);
      if (res.data && res.data.feedback) {
        setAiFeedback(res.data.feedback);
      }
    }).catch(error => {
      console.error("Error generating routine:", error);
      setRoutineError('Failed to generate routine. Please try again.');
    }).finally(() => {
      setIsLoading(false);
    });
  };

  // New handler for course input change
  const handleCourseInputChange = (event) => {
    const value = event.target.value;
    setCourseSearchTerm(value);

    // Filter available courses based on search term
    const filtered = availableCourses
        .filter(course => 
            course.code.toLowerCase().includes(value.toLowerCase()) &&
            !routineCourses.some(selected => selected.value === course.code)
        )
        .map(course => ({
            value: course.code,
            label: course.code,
            isDisabled: !course.sections?.some(section => section.availableSeats > 0)
        }));

    setFilteredCourseOptions(filtered);
    setIsCourseSuggestionsOpen(value.length > 0 && filtered.length > 0);
  };

  // New handler for selecting a course from suggestions
  const handleCourseSuggestionSelect = async (option) => {
    // Check if any section has available seats
    const courseData = availableCourses.find(c => c.code === option.value);
    const hasAvailableSection = courseData?.sections?.some(section => section.availableSeats > 0);
    
    // Prevent adding if no section has available seats
    if (!hasAvailableSection) {
        alert(`Cannot add ${option.label}: No seats available.`);
        setCourseSearchTerm(''); // Clear input after attempted selection
        setIsCourseSuggestionsOpen(false); // Close suggestions
        return;
    }

    // Add the selected course to the routineCourses state if not already present
    if (!routineCourses.some(course => course.value === option.value)) {
        const updatedCourses = [...routineCourses, option];
        setRoutineCourses(updatedCourses);

        try {
            const res = await axios.get(`${API_BASE}/course_details?course=${option.value}`);
            const facultySections = {};
            res.data.forEach(section => {
                if (section.faculties) {
                    const availableSeats = section.capacity - section.consumedSeat;
                    if (availableSeats > 0) {
                        if (!facultySections[section.faculties]) {
                            facultySections[section.faculties] = {
                                sections: [],
                                totalSeats: 0,
                                availableSeats: 0
                            };
                        }
                        facultySections[section.faculties].sections.push(section);
                        facultySections[section.faculties].totalSeats += section.capacity;
                        facultySections[section.faculties].availableSeats += availableSeats;
                    }
                }
            });
            setAvailableFacultyByCourse(prev => ({ ...prev, [option.value]: facultySections }));
        } catch (error) {
            console.error(`Error fetching faculty for ${option.value}:`, error);
        }
    }

    setCourseSearchTerm(''); // Clear input after selection
    setIsCourseSuggestionsOpen(false); // Close suggestions
  };

  // New handler for removing a course tag
  const handleRemoveCourseTag = (courseValue) => {
      setRoutineCourses(routineCourses.filter(course => course.value !== courseValue));
      // When a tag is removed, add the course back to filtered options if search term is empty
      if (courseSearchTerm === '') {
        const removedCourse = courseOptions.find(opt => opt.value === courseValue);
        if(removedCourse) {
            setFilteredCourseOptions([...filteredCourseOptions, removedCourse].sort((a, b) => a.label.localeCompare(b.label)));
        }
      } else {
           // If there's a search term, re-filter based on current input
            const filtered = courseOptions.filter(option =>
                option.label.toLowerCase().includes(courseSearchTerm.toLowerCase()) && !routineCourses.some(rc => rc.value === option.value && rc.value !== courseValue) // Exclude the one just removed from the exclusion list
            );
            setFilteredCourseOptions(filtered);
      }
      // Also remove corresponding faculty and section selections for the removed course
        setSelectedFacultyByCourse(prev => {
            const newState = { ...prev };
            delete newState[courseValue];
            return newState;
        });
        setSelectedSectionsByFaculty(prev => {
            const newState = { ...prev };
            delete newState[courseValue];
            return newState;
        });
  };

  // New handlers for input focus and blur
  const handleCourseInputFocus = () => {
      // Show suggestions on focus, filtered to exclude selected courses
      setFilteredCourseOptions(courseOptions.filter(option => !routineCourses.some(rc => rc.value === option.value)));
      setIsCourseSuggestionsOpen(true);
  };

  const handleCourseInputBlur = () => {
      // Delay hiding suggestions to allow click on suggestion item
      setTimeout(() => {
          setIsCourseSuggestionsOpen(false);
          setCourseSearchTerm(''); // Clear input on blur
      }, 200);
  };

  // New handler for day input change
  const handleDayInputChange = (event) => {
    const value = event.target.value;
    setDaySearchTerm(value);

    if (value === '') {
        // If input is cleared, show all days that are not already selected
        setFilteredDayOptions(DAYS.map(d => ({ value: d, label: d })).filter(option => !routineDays.some(rd => rd.value === option.value)));
    } else {
        // Filter days based on input value (case-insensitive) and exclude already selected ones
        const filtered = DAYS.map(d => ({ value: d, label: d })).filter(option =>
            option.label.toLowerCase().includes(value.toLowerCase()) && !routineDays.some(rd => rd.value === option.value)
        );
        setFilteredDayOptions(filtered);
    }

    // Open suggestions if there is input or available options
    setIsDaySuggestionsOpen(true);
  };

  // New handler for selecting a day from suggestions
  const handleDaySuggestionSelect = (option) => {
      // Add the selected day to the routineDays state if not already present
      if (!routineDays.some(day => day.value === option.value)) {
          setRoutineDays([...routineDays, option]);
      }
      setDaySearchTerm(''); // Clear input after selection
      setFilteredDayOptions(DAYS.map(d => ({ value: d, label: d })).filter(opt => !routineDays.some(rd => rd.value === opt.value && opt.value !== option.value))); // Update suggestions
      setIsDaySuggestionsOpen(false); // Close suggestions after selection
  };

  // New handler for removing a day tag
  const handleRemoveDayTag = (dayValue) => {
      setRoutineDays(routineDays.filter(day => day.value !== dayValue));
       // When a tag is removed, add the day back to filtered options if search term is empty
      if (daySearchTerm === '') {
        const removedDay = DAYS.find(day => day === dayValue);
        if(removedDay) {
            setFilteredDayOptions([...filteredDayOptions, {value: removedDay, label: removedDay}].sort((a, b) => a.label.localeCompare(b.label)));
        }
      } else {
           // If there's a search term, re-filter based on current input
            const filtered = DAYS.map(d => ({ value: d, label: d })).filter(option =>
                option.label.toLowerCase().includes(daySearchTerm.toLowerCase()) && !routineDays.some(rd => rd.value === option.value && rd.value !== dayValue) // Exclude the one just removed from the exclusion list
            );
            setFilteredDayOptions(filtered);
      }
  };

   // New handlers for day input focus and blur
  const handleDayInputFocus = () => {
      // Show suggestions on focus, filtered to exclude selected days
      setFilteredDayOptions(DAYS.map(d => ({ value: d, label: d })).filter(option => !routineDays.some(rd => rd.value === option.value)));
      setIsDaySuggestionsOpen(true);
  };

  const handleDayInputBlur = () => {
      // Delay hiding suggestions to allow click on suggestion item
      setTimeout(() => {
          setIsDaySuggestionsOpen(false);
          setDaySearchTerm(''); // Clear input on blur
      }, 200);
  };

  // New handler for time input change
  const handleTimeInputChange = (event) => {
    const value = event.target.value;
    setTimeSearchTerm(value);

    if (value === '') {
        // If input is cleared, show all times that are not already selected
        setFilteredTimeOptions(TIME_SLOTS.filter(option => !routineTimes.some(rt => rt.value === option.value)));
    } else {
        // Filter times based on input value (case-insensitive) and exclude already selected ones
        const filtered = TIME_SLOTS.filter(option =>
            option.label.toLowerCase().includes(value.toLowerCase()) && !routineTimes.some(rt => rt.value === option.value)
        );
        setFilteredTimeOptions(filtered);
    }

    // Open suggestions if there is input or available options
    setIsTimeSuggestionsOpen(true);
  };

  // New handler for selecting a time from suggestions
  const handleTimeSuggestionSelect = (option) => {
      // Add the selected time to the routineTimes state if not already present
      if (!routineTimes.some(time => time.value === option.value)) {
          setRoutineTimes([...routineTimes, option]);
      }
      setTimeSearchTerm(''); // Clear input after selection
      setFilteredTimeOptions(TIME_SLOTS.filter(opt => !routineTimes.some(rt => rt.value === opt.value && opt.value !== option.value))); // Update suggestions
      setIsTimeSuggestionsOpen(false); // Close suggestions after selection
  };

  // New handler for removing a time tag
  const handleRemoveTimeTag = (timeValue) => {
      setRoutineTimes(routineTimes.filter(time => time.value !== timeValue));
       // When a tag is removed, add the time back to filtered options if search term is empty
      if (timeSearchTerm === '') {
        const removedTime = TIME_SLOTS.find(opt => opt.value === timeValue);
        if(removedTime) {
            setFilteredTimeOptions([...filteredTimeOptions, removedTime].sort((a, b) => a.label.localeCompare(b.label)));
        }
      } else {
           // If there's a search term, re-filter based on current input
            const filtered = TIME_SLOTS.filter(option =>
                option.label.toLowerCase().includes(timeSearchTerm.toLowerCase()) && !routineTimes.some(rt => rt.value === option.value && rt.value !== timeValue) // Exclude the one just removed from the exclusion list
            );
            setFilteredTimeOptions(filtered);
      }
  };

   // New handlers for time input focus and blur
  const handleTimeInputFocus = () => {
      // Show suggestions on focus, filtered to exclude selected times
      setFilteredTimeOptions(TIME_SLOTS.filter(option => !routineTimes.some(rt => rt.value === option.value)));
      setIsTimeSuggestionsOpen(true);
  };

  const handleTimeInputBlur = () => {
      // Delay hiding suggestions to allow click on suggestion item
      setTimeout(() => {
          setIsTimeSuggestionsOpen(false);
          setTimeSearchTerm(''); // Clear input on blur
      }, 200);
  };

  // Handler for faculty input change
  const handleFacultyInputChange = (event, courseValue) => {
    const value = event.target.value;
    setFacultySearchTerm(prev => ({ ...prev, [courseValue]: value }));
    const facultyOptions = Object.entries(availableFacultyByCourse[courseValue] || {})
      .filter(([_, info]) => info.availableSeats > 0)
      .map(([faculty, info]) => ({ value: faculty, label: faculty, info }));
    let filtered;
    if (value === '') {
      filtered = facultyOptions.filter(option => !(selectedFacultyByCourse[courseValue] || []).some(f => f.value === option.value));
    } else {
      filtered = facultyOptions.filter(option =>
        option.label.toLowerCase().includes(value.toLowerCase()) && !(selectedFacultyByCourse[courseValue] || []).some(f => f.value === option.value)
      );
    }
    setFilteredFacultyOptions(prev => ({ ...prev, [courseValue]: filtered }));
    setIsFacultySuggestionsOpen(prev => ({ ...prev, [courseValue]: true }));
  };

  // Handler for selecting a faculty from suggestions
  const handleFacultySuggestionSelect = (option, courseValue) => {
    if (!(selectedFacultyByCourse[courseValue] || []).some(f => f.value === option.value)) {
      setSelectedFacultyByCourse(prev => ({
        ...prev,
        [courseValue]: [...(prev[courseValue] || []), option]
      }));
    }
    setFacultySearchTerm(prev => ({ ...prev, [courseValue]: '' }));
    setFilteredFacultyOptions(prev => ({
      ...prev,
      [courseValue]: (prev[courseValue] || []).filter(opt => opt.value !== option.value)
    }));
    setIsFacultySuggestionsOpen(prev => ({ ...prev, [courseValue]: false }));
  };

  // Handler for removing a faculty tag
  const handleRemoveFacultyTag = (facultyValue, courseValue) => {
    setSelectedFacultyByCourse(prev => ({
      ...prev,
      [courseValue]: (prev[courseValue] || []).filter(f => f.value !== facultyValue)
    }));
  };

  // Handler for faculty input focus/blur
  const handleFacultyInputFocus = (courseValue) => {
    const facultyOptions = Object.entries(availableFacultyByCourse[courseValue] || {})
      .filter(([_, info]) => info.availableSeats > 0)
      .map(([faculty, info]) => ({ value: faculty, label: faculty, info }));
    const filtered = facultyOptions.filter(option => !(selectedFacultyByCourse[courseValue] || []).some(f => f.value === option.value));
    setFilteredFacultyOptions(prev => ({ ...prev, [courseValue]: filtered }));
    setIsFacultySuggestionsOpen(prev => ({ ...prev, [courseValue]: true }));
  };
  const handleFacultyInputBlur = (courseValue) => {
    setTimeout(() => {
      setIsFacultySuggestionsOpen(prev => ({ ...prev, [courseValue]: false }));
      setFacultySearchTerm(prev => ({ ...prev, [courseValue]: '' }));
    }, 200);
  };

  // Custom option component for faculty selection with sections
  const FacultyOption = ({ data, ...props }) => {
    const facultyInfo = availableFacultyByCourse[props.selectProps.name]?.[data.value];
    return (
      <div {...props.innerProps} style={{ padding: '8px' }}>
        <div style={{ fontWeight: 'bold' }}>{data.label}</div>
        {facultyInfo && (
          <div style={{ fontSize: '0.9em', color: '#666' }}>
            Available Seats: {facultyInfo.availableSeats} / {facultyInfo.totalSeats}
            <br />
            Sections: {facultyInfo.sections.length}
          </div>
        )}
      </div>
    );
  };

  // Add loading spinner component
  const LoadingSpinner = () => (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '20px'
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '4px solid #f3f3f3',
        borderTop: '4px solid #3498db',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }} />
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );

  // Update the routine result display with transitions
  const RoutineResult = ({ routineGridRef, onDownloadPNG }) => {
    if (isLoading) {
      return <LoadingSpinner />;
    }

    if (routineError) {
      console.log("Frontend received error:", routineError);
      console.log("Error includes 'Exam Conflicts':", routineError.includes('Exam Conflicts'));
      if (routineError.includes('Exam Conflicts')) {
        console.log("Rendering ExamConflictMessage with message:", routineError);
        return <ExamConflictMessage message={routineError} />;
      }
      return (
        <div style={{
          color: 'red',
          marginTop: '20px',
          fontWeight: 'bold',
          textAlign: 'center',
          padding: '20px',
          backgroundColor: '#fff3f3',
          borderRadius: '4px',
          border: '1px solid #ffcdd2'
        }}>
          {routineError}
        </div>
      );
    }

    if (routineResult && Array.isArray(routineResult)) {
      return (
        <div style={{
          marginTop: "20px",
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "4px",
          opacity: isLoading ? 0.5 : 1,
          transition: 'opacity 0.3s ease-in-out'
        }}>
          <h3 style={{ textAlign: 'center', marginBottom: 24 }}>{usedAI ? 'AI Routine:' : 'Generated Routine:'}</h3>
          {/* Display Feedback */}
          {aiFeedback ? (
            <div className="ai-analysis-container">
              <div className="ai-result feedback">
                <b>AI Feedback:</b><br />
                <span style={{ fontSize: '1.1em', color: '#2e7d32', fontWeight: 600 }}>{aiFeedback.split('\n')[0]}</span>
                <ul style={{ margin: '10px 0 0 0', padding: 0, listStyle: 'disc inside', color: '#333' }}>
                  {aiFeedback.split('\n').slice(1).map((line, i) => line && <li key={i}>{line}</li>)}
                </ul>
              </div>
            </div>
          ) : (
            <div className="ai-analysis-container">
              <div className="ai-result feedback" style={{ color: '#888' }}>
                <b>AI Feedback:</b> <span>No feedback available.</span>
              </div>
            </div>
          )}
          <CampusDaysDisplay routine={routineResult} />
          {/* Routine Grid Container with Ref */}
          <div ref={routineGridRef} style={{ marginTop: "20px" }} data-routine-grid>
            {renderRoutineGrid(routineResult, routineDays.map(d => d.value))}
          </div>
          
          {/* Download Button */}
          <button 
            onClick={onDownloadPNG} 
            style={{
              marginTop: '20px',
              padding: '10px 20px',
              fontSize: '1em',
              backgroundColor: '#ffffff', // White background
              color: '#333333', // Dark text color
              border: '1px solid #cccccc', // Subtle gray border
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'background-color 0.3s ease, border-color 0.3s ease'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#ffffff'}
          >
            Download as PNG
          </button>

          <ExamSchedule sections={routineResult} />
        </div>
      );
    }

    return null;
  };

  // Update the generate button to show loading state
  const GenerateButton = () => (
    <button
      onClick={() => handleGenerateRoutine(false)}
      disabled={routineCourses.length === 0 || routineDays.length === 0 || isLoading}
      style={{
        padding: "10px 20px",
        fontSize: "16px",
        backgroundColor: isLoading ? "#f0f0f0" : "#fff",
        color: isLoading ? "#aaaaaa" : "#007bff",
        border: "1.5px solid #4f8cff",
        borderRadius: "6px",
        cursor: isLoading ? "not-allowed" : "pointer",
        transition: 'background-color 0.3s, color 0.3s, border-color 0.3s, box-shadow 0.3s',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minWidth: '150px',
        boxShadow: '0 2px 10px 0 rgba(79,140,255,0.10)',
        fontWeight: 500
      }}
    >
      {isLoading && !usedAI ? (
        <>
          Generating...
        </>
      ) : (
        'Generate Routine'
      )}
    </button>
  );

  const GenerateAIButton = () => (
    <button
      onClick={() => handleGenerateRoutine(true)}  // Changed to directly call with true
      className="ai-best-routine-btn"
      style={{
        padding: "12px 28px",
        fontSize: "17px",
        fontWeight: 600,
        color: "#fff",
        border: "none",
        borderRadius: "6px",
        marginLeft: "12px",
        background: "linear-gradient(90deg, #4f8cff 0%, #007bff 100%)",
        boxShadow: "0 4px 18px 0 rgba(79,140,255,0.22), 0 1.5px 6px 0 rgba(0,123,255,0.13)",
        cursor: isLoading ? "not-allowed" : "pointer",
        outline: 'none',
        transition: 'transform 0.15s, box-shadow 0.3s',
        transform: isLoading ? 'scale(1)' : undefined
      }}
      onMouseOver={e => {
        e.currentTarget.style.transform = 'scale(1.04)';
        e.currentTarget.style.boxShadow = '0 6px 24px 0 rgba(79,140,255,0.28), 0 2px 8px 0 rgba(0,123,255,0.18)';
      }}
      onMouseOut={e => {
        e.currentTarget.style.transform = 'scale(1)';
        e.currentTarget.style.boxShadow = '0 4px 18px 0 rgba(79,140,255,0.22), 0 1.5px 6px 0 rgba(0,123,255,0.13)';
      }}
      disabled={isLoading || routineCourses.length === 0 || routineDays.length === 0}
    >
      {isLoading ? (
         "Generating with AI..."
      ) : (
         "Use AI for Best Routine"
      )}
    </button>
  );

  // Handler for section input change
  const handleSectionInputChange = (event, courseValue, facultyValue, sectionOptions) => {
    const value = event.target.value;
    setSectionSearchTerm(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: value }
    }));
    let filtered = sectionOptions;
    if (value !== '') {
      filtered = sectionOptions.filter(option => option.label.toLowerCase().includes(value.toLowerCase()));
    }
    setFilteredSectionOptions(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: filtered }
    }));
    setIsSectionSuggestionsOpen(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: true }
    }));
  };

  // Handler for selecting a section from suggestions
  const handleSectionSuggestionSelect = (option, courseValue, facultyValue) => {
    setSelectedSectionsByFaculty(prev => ({
      ...prev,
      [courseValue]: {
        ...(prev[courseValue] || {}),
        [facultyValue]: option
      }
    }));
    setSectionSearchTerm(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: '' }
    }));
    setFilteredSectionOptions(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: [] }
    }));
    setIsSectionSuggestionsOpen(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: false }
    }));
  };

  // Handler for section input focus
  const handleSectionInputFocus = (courseValue, facultyValue, sectionOptions) => {
    setFilteredSectionOptions(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: sectionOptions }
    }));
    setIsSectionSuggestionsOpen(prev => ({
      ...prev,
      [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: true }
    }));
  };

  // Handler for section input blur
  const handleSectionInputBlur = (courseValue, facultyValue) => {
    setTimeout(() => {
      setIsSectionSuggestionsOpen(prev => ({
        ...prev,
        [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: false }
      }));
      setSectionSearchTerm(prev => ({
        ...prev,
        [courseValue]: { ...(prev[courseValue] || {}), [facultyValue]: '' }
      }));
    }, 200);
  };

  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h2>Make Routine</h2>
      <p>Select courses and their faculty, then choose available days and times.</p>
      {/* Course Selection with Autocomplete and Tags */}
      <div style={{ marginBottom: "20px", position: "relative", textAlign: "left" }}>
        <label style={{ display: "block", marginBottom: "5px", fontSize: '1.13em', fontWeight: 600, letterSpacing: '0.01em' }}>Courses:</label>
        <div style={{ 
          display: "flex", 
          flexWrap: "wrap", 
          alignItems: "center", 
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          padding: "8px 12px",
          backgroundColor: "#fff",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
        }}>
          {/* Display selected course tags */}
          {routineCourses.map(course => (
            <span key={course.value} style={{ backgroundColor: '#f0f0f0', color: '#555555', borderRadius: '4px', padding: '2px 8px', marginRight: '5px', marginBottom: '5px', display: 'inline-flex', alignItems: 'center' }}>
              {course.label}
              <button
                type="button"
                onClick={() => handleRemoveCourseTag(course.value)}
                style={{ marginLeft: '5px', cursor: 'pointer', background: 'none', border: 'none', color: '#555555', padding: 0 }}
              >
                &times;
              </button>
            </span>
          ))}
          {/* Course input field */}
          <input
            type="text"
          placeholder="Select courses..."
            aria-label="Select courses"
            value={courseSearchTerm}
            onChange={handleCourseInputChange}
            onFocus={handleCourseInputFocus}
            onBlur={handleCourseInputBlur}
            style={{ flexGrow: 1, border: 'none', outline: 'none', padding: '5px' }}
          />
        </div>

        {/* Course suggestions list */}
        {(isCourseSuggestionsOpen && filteredCourseOptions.length > 0 && ( !isLoading && courseOptions.length > 0 )) && (
  <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto" style={{ textAlign: "left" }} role="listbox" tabIndex={0}>
    {filteredCourseOptions.map(option => (
      <li
        key={option.value}
        onClick={() => handleCourseSuggestionSelect(option)}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
        role="option"
        aria-selected={false}
      >
        {option.label} {option.isDisabled && "(No seats available)"}
      </li>
    ))}
  </ul>
)}
         {/* Loading or empty state messages for courses */}
        {isLoading && courseOptions.length === 0 && courseSearchTerm === '' && (
             <div className="text-center py-2 text-gray-500 text-sm">Loading courses...</div>
        )}
         {!isLoading && courseOptions.length > 0 && courseSearchTerm !== '' && filteredCourseOptions.length === 0 && (
                 <div className="text-center py-2 text-gray-500 text-sm">No matching courses found.</div>
              )}
            {!isLoading && courseOptions.length === 0 && courseSearchTerm === '' && (
                <div className="text-center py-2 text-gray-500 text-sm">No courses loaded.</div>
            )}

      </div>
      {/* Faculty Selection for Each Course */}
      {routineCourses.map(course => {
        const facultyOptions = Object.entries(availableFacultyByCourse[course.value] || {})
          .filter(([_, info]) => info.availableSeats > 0)
          .map(([faculty, info]) => ({ value: faculty, label: faculty, info }));
        const selectedFaculty = selectedFacultyByCourse[course.value] || [];

        return (
          <div key={course.value} className="card" style={{ marginBottom: "10px", padding: "10px 14px", fontSize: "0.97em", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ fontWeight: 600, fontSize: "1.08em", marginBottom: 2 }}>{course.label}</div>
            {/* Faculty selection */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label style={{ minWidth: 55, fontSize: "0.95em", color: "#444", marginBottom: 0 }}>Faculty:</label>
              <div style={{ position: 'relative', minWidth: 180 }}>
                {/* Display selected faculty tags */}
                {(selectedFacultyByCourse[course.value] || []).map(faculty => (
                  <span key={faculty.value} style={{ backgroundColor: '#f0f0f0', color: '#555555', borderRadius: '4px', padding: '2px 8px', marginRight: '5px', marginBottom: '2px', display: 'inline-flex', alignItems: 'center', fontSize: '0.97em' }}>
                    {faculty.label}
                    <button
                      type="button"
                      onClick={() => handleRemoveFacultyTag(faculty.value, course.value)}
                      style={{ marginLeft: '5px', cursor: 'pointer', background: 'none', border: 'none', color: '#555555', padding: 0 }}
                    >
                      &times;
                    </button>
                  </span>
                ))}
                {/* Faculty input field */}
                <input
                  type="text"
                  placeholder="Select faculty..."
                  aria-label={`Select faculty for ${course.label}`}
                  value={facultySearchTerm[course.value] || ''}
                  onChange={e => handleFacultyInputChange(e, course.value)}
                  onFocus={() => handleFacultyInputFocus(course.value)}
                  onBlur={() => handleFacultyInputBlur(course.value)}
                  style={{ flexGrow: 1, border: 'none', outline: 'none', padding: '5px', minWidth: 90 }}
                />
                {/* Faculty suggestions list */}
                {(isFacultySuggestionsOpen[course.value] && filteredFacultyOptions[course.value] && filteredFacultyOptions[course.value].length > 0) && (
  <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto" style={{ textAlign: "left" }} role="listbox" tabIndex={0}>
    {filteredFacultyOptions[course.value].map(option => (
      <li
        key={option.value}
        onClick={() => handleFacultySuggestionSelect(option, course.value)}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
        role="option"
        aria-selected={false}
      >
        {option.label}
      </li>
    ))}
  </ul>
)}
              </div>
            </div>
            {/* Section selection (vertical, below faculty) */}
              {selectedFaculty.map(faculty => {
                const facultyInfo = availableFacultyByCourse[course.value]?.[faculty.value];
                if (!facultyInfo) return null;
                const sectionOptions = facultyInfo.sections.map(section => ({
                  value: section.sectionName,
                  label: `${section.sectionName} (${section.capacity - section.consumedSeat} seats)`,
                  section: section
                }));
              const selectedSection = selectedSectionsByFaculty[course.value]?.[faculty.value] || null;
                return (
                <div key={faculty.value} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: 4 }}>
                  <label style={{ fontSize: "0.85em", color: "#666", marginBottom: 0, minWidth: 60 }}>
                    {faculty.value} Section:
                      </label>
                  {/* Custom section dropdown */}
                  <div style={{ position: 'relative', minWidth: 120 }}>
                    {/* Tag for selected section */}
                    {selectedSection && (
                      <span style={{ backgroundColor: '#f0f0f0', color: '#555555', borderRadius: '4px', padding: '2px 8px', marginRight: '5px', marginBottom: '2px', display: 'inline-flex', alignItems: 'center', fontSize: '0.97em' }}>
                        {selectedSection.label}
                        <button
                          type="button"
                          onClick={() => handleSectionSuggestionSelect(null, course.value, faculty.value)}
                          style={{ marginLeft: '5px', cursor: 'pointer', background: 'none', border: 'none', color: '#555555', padding: 0 }}
                        >
                          &times;
                        </button>
                      </span>
                    )}
                    {/* Section input field: only show if not selected */}
                    {!selectedSection && (
                      <input
                        type="text"
                        placeholder="Section..."
                        aria-label={`Select section for ${faculty.value} in ${course.label}`}
                        value={sectionSearchTerm[course.value]?.[faculty.value] || ''}
                        onChange={e => handleSectionInputChange(e, course.value, faculty.value, sectionOptions)}
                        onFocus={() => handleSectionInputFocus(course.value, faculty.value, sectionOptions)}
                        onBlur={() => handleSectionInputBlur(course.value, faculty.value)}
                        style={{ width: '100%', border: '1px solid #ccc', borderRadius: '4px', padding: '5px', minWidth: 60 }}
                      />
                    )}
                    {/* Section suggestions list */}
                    {(isSectionSuggestionsOpen[course.value]?.[faculty.value] && filteredSectionOptions[course.value]?.[faculty.value]?.length > 0) && (
  <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto" style={{ textAlign: "left" }} role="listbox" tabIndex={0}>
    {filteredSectionOptions[course.value][faculty.value].map(option => (
      <li
        key={option.value}
        onClick={() => handleSectionSuggestionSelect(option, course.value, faculty.value)}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
        role="option"
        aria-selected={false}
      >
        {option.label}
      </li>
    ))}
  </ul>
)}
                    </div>
                  </div>
                );
              })}
          </div>
        );
      })}
      {/* Available Days Selection with Autocomplete and Tags */}
      <div style={{ marginBottom: "20px", position: "relative", textAlign: "left" }}>
        <label style={{ display: "block", marginBottom: "5px", fontSize: '1.13em', fontWeight: 600, letterSpacing: '0.01em' }}>Available Days:</label>
        <div style={{ 
          display: "flex", 
          flexWrap: "wrap", 
          alignItems: "center", 
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          padding: "8px 12px",
          backgroundColor: "#fff",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
        }}>
          {/* Display selected day tags */}
          {routineDays.map(day => (
            <span key={day.value} style={{ backgroundColor: '#f0f0f0', color: '#555555', borderRadius: '4px', padding: '2px 8px', marginRight: '5px', marginBottom: '5px', display: 'inline-flex', alignItems: 'center' }}>
              {day.label}
              <button
                type="button"
                onClick={() => handleRemoveDayTag(day.value)}
                style={{ marginLeft: '5px', cursor: 'pointer', background: 'none', border: 'none', color: '#555555', padding: 0 }}
              >
                &times;
              </button>
            </span>
          ))}
          {/* Day input field: only show if not all days are selected */}
          {routineDays.length < DAYS.length && (
            <input
              type="text"
          placeholder="Select days..."
              value={daySearchTerm}
              onChange={handleDayInputChange}
              onFocus={handleDayInputFocus}
              onBlur={handleDayInputBlur}
              style={{ flexGrow: 1, border: 'none', outline: 'none', padding: '5px' }}
        />
          )}
      </div>

        {/* Day suggestions list */}
        {(isDaySuggestionsOpen && filteredDayOptions.length > 0) && (
  <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto" style={{ textAlign: "left" }} role="listbox" tabIndex={0}>
    {filteredDayOptions.map(option => (
      <li
        key={option.value}
        onClick={() => handleDaySuggestionSelect(option)}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
        role="option"
        aria-selected={false}
      >
        {option.label}
      </li>
    ))}
  </ul>
)}
      </div>
      {/* Available Times Selection with Autocomplete and Tags */}
      <div style={{ marginBottom: "20px", position: "relative", textAlign: "left" }}>
        <label style={{ display: "block", marginBottom: "5px", fontSize: '1.13em', fontWeight: 600, letterSpacing: '0.01em' }}>Available Times:</label>
        <div style={{ 
          display: "flex", 
          flexWrap: "wrap", 
          alignItems: "center", 
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          padding: "8px 12px",
          backgroundColor: "#fff",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
        }}>
          {/* Display selected time tags */}
          {routineTimes.map(time => (
            <span key={time.value} style={{ backgroundColor: '#f0f0f0', color: '#555555', borderRadius: '4px', padding: '2px 8px', marginRight: '5px', marginBottom: '5px', display: 'inline-flex', alignItems: 'center' }}>
              {time.label}
              <button
                type="button"
                onClick={() => handleRemoveTimeTag(time.value)}
                style={{ marginLeft: '5px', cursor: 'pointer', background: 'none', border: 'none', color: '#555555', padding: 0 }}
              >
                &times;
              </button>
            </span>
          ))}
          {/* Time input field: only show if not all times are selected */}
          {routineTimes.length < TIME_SLOTS.length && (
            <input
              type="text"
              placeholder="Select available times..."
              value={timeSearchTerm}
              onChange={handleTimeInputChange}
              onFocus={handleTimeInputFocus}
              onBlur={handleTimeInputBlur}
              style={{ flexGrow: 1, border: 'none', outline: 'none', padding: '5px' }}
            />
          )}
        </div>

        {/* Time suggestions list */}
{(isTimeSuggestionsOpen && filteredTimeOptions.length > 0) && (
  <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto" style={{ textAlign: "left" }} role="listbox" tabIndex={0}>
    {filteredTimeOptions.map(option => (
      <li
        key={option.value}
        onClick={() => handleTimeSuggestionSelect(option)}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
        role="option"
        aria-selected={false}
      >
        {option.label}
      </li>
    ))}
  </ul>
)}
      </div>
      {/* Commute Preference Selection */}
      <div style={{ marginBottom: "20px", textAlign: "left" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold", color: "#555", fontSize: '1.13em', letterSpacing: '0.01em' }}>Commute Preference:</label>
        <div>
          <label style={{ marginRight: "15px" }}>
            <input
              type="radio"
              value="far"
              checked={commutePreference === "far"}
              onChange={(e) => setCommutePreference(e.target.value)}
              style={{ marginRight: "5px" }}
            />
            Live Far (More classes on same day)
          </label>
          <label>
            <input
              type="radio"
              value="near"
              checked={commutePreference === "near"}
              onChange={(e) => setCommutePreference(e.target.value)}
              style={{ marginRight: "5px" }}
            />
            Live Near (Spread out classes)
          </label>
        </div>
      </div>
      {/* Summary of selections - always render strings only */}
      <div style={{ marginBottom: "20px", color: "#555" }}>
        <div>
          <b>Selected Courses:</b> {(Array.isArray(routineCourses) && routineCourses.length) ? routineCourses.map(c => (typeof c === 'object' ? (c.label || c.value || '') : String(c))).join(', ') : "None"}
        </div>
        <div>
          <b>Selected Days:</b> {Array.isArray(routineDays) && routineDays.length ? routineDays.map(d => (typeof d === 'object' ? (d.label || d.value || '') : String(d))).join(', ') : "None"}
        </div>
         {Object.keys(selectedFacultyByCourse).length > 0 && (
           <div>
             <b>Selected Faculty:</b> {
               Object.entries(selectedFacultyByCourse)
                 .map(([courseCode, faculties]) => 
                  `${courseCode}: ${faculties.map(f => f && typeof f === 'object' ? (f.label || f.value || '') : String(f)).join(', ')}`
                 )
                 .join('; ')
             }
           </div>
         )}
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: "10px", marginBottom: "20px" }}>
        <GenerateButton />
        <GenerateAIButton />
        </div>
      <div style={{ fontSize: "0.9em", color: "#555", marginTop: "10px" }}>
        Using the AI for routine generation may provide a better combination of courses and times,
        and can offer feedback on the generated routine.
      </div>
      <RoutineResult routineGridRef={routineGridRef} onDownloadPNG={handleDownloadPNG} />
    </div>
  );
};

function Footer() {
  return (
    <footer
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '32px 0 16px 0',
        background: 'transparent',
      }}
    >
      <div
        style={{
          fontSize: '1.1em',
          fontWeight: 500,
          color: '#555',
          letterSpacing: '0.02em',
          marginBottom: '16px',
          textAlign: 'center',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        Made with
        <span
          style={{
            color: '#ff3b3b',
            fontSize: '1.3em',
            verticalAlign: 'middle',
            filter: 'drop-shadow(0 1px 6px #ffb3b3)',
            textShadow: '0 2px 8px #ffb3b3',
            margin: '0 2px',
          }}
        >
          &hearts;
        </span>
        by
        <span
          style={{
            background: 'linear-gradient(90deg, #4f8cff 0%, #007bff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 600,
            fontSize: '1em',
            letterSpacing: '0.03em',
            textShadow: '0 2px 8px rgba(79,140,255,0.13)',
          }}
        >
          Wasif Faisal
        </span>
      </div>
      <a
        href="https://m.me/wa5if"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Messenger for bug reports or feedback"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#888',
          textDecoration: 'none',
          fontSize: '1em',
          marginTop: '8px',
          transition: 'color 0.2s',
        }}
        onMouseOver={e => {
          e.currentTarget.style.color = '#007bff';
        }}
        onMouseOut={e => {
          e.currentTarget.style.color = '#888';
        }}
      >
        <MessageCircle size={28} color="currentColor" />
        <span>Report bugs</span>
      </a>
    </footer>
  );
}

// Toast and ErrorBanner components
function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div style={{
      position: 'fixed',
      top: 24,
      left: '50%',
      transform: 'translateX(-50%)',
      background: 'rgba(40,60,255,0.97)',
      color: '#fff',
      padding: '12px 32px',
      borderRadius: 12,
      fontWeight: 600,
      fontSize: '1.08em',
      zIndex: 9999,
      boxShadow: '0 4px 24px 0 rgba(79,140,255,0.18)',
      minWidth: 180,
      textAlign: 'center',
      letterSpacing: '0.01em',
      opacity: 0.97,
      pointerEvents: 'none',
    }}>
      {message}
    </div>
  );
}
function ErrorBanner({ message, onClose }) {
  if (!message) return null;
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      background: '#ffebee',
      color: '#c62828',
      borderBottom: '2px solid #ffcdd2',
      padding: '16px 0',
      zIndex: 9998,
      textAlign: 'center',
      fontWeight: 600,
      fontSize: '1.08em',
      letterSpacing: '0.01em',
      boxShadow: '0 2px 12px 0 rgba(198,40,40,0.08)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16,
    }}>
      <span style={{marginRight: 8}}>⚠️ {message}</span>
      <button onClick={onClose} style={{
        background: 'none',
        border: 'none',
        color: '#c62828',
        fontWeight: 700,
        fontSize: '1.2em',
        cursor: 'pointer',
        marginLeft: 8,
      }} aria-label="Dismiss error">×</button>
    </div>
  );
}

function App() {
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [courses, setCourses] = useState([]);
  const [sections, setSections] = useState([]);
  const [routineCourses, setRoutineCourses] = useState([]);
  const [routineFaculty, setRoutineFaculty] = useState(null);
  const [routineDays, setRoutineDays] = useState(DAYS.map(d => ({ value: d, label: d }))); // Reverted to include all days
  const [routineFacultyOptions, setRoutineFacultyOptions] = useState([]);
  const [routineResult, setRoutineResult] = useState(null);
  const [availableFacultyByCourse, setAvailableFacultyByCourse] = useState({});
  const [selectedFacultyByCourse, setSelectedFacultyByCourse] = useState({});
  const [routineTimes, setRoutineTimes] = useState(TIME_SLOTS);
  const [routineError, setRoutineError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiFeedback, setAiFeedback] = useState(null);
  const [commutePreference, setCommutePreference] = useState("");
  const [selectedSectionsByFaculty, setSelectedSectionsByFaculty] = useState({});
  const [usedAI, setUsedAI] = useState(false);
  const [courseOptions, setCourseOptions] = useState([]);
  const [courseSearchTerm, setCourseSearchTerm] = useState('');
  const [filteredCourseOptions, setFilteredCourseOptions] = useState([]);
  const [isCourseSuggestionsOpen, setIsCourseSuggestionsOpen] = useState(false);
  const routineGridRef = useRef(null);

  // Function to handle PNG download
  const handleDownloadPNG = () => {
    if (routineGridRef.current) {
      const element = routineGridRef.current;
      
      // Create a temporary container with white background
      const tempContainer = document.createElement('div');
      tempContainer.style.position = 'absolute';
      tempContainer.style.left = '-9999px';
      tempContainer.style.background = '#ffffff';
      tempContainer.style.padding = '20px';
      
      // Clone the element and its children
      const clone = element.cloneNode(true);
      tempContainer.appendChild(clone);
      document.body.appendChild(tempContainer);

      // Set options for better quality and full capture
      const options = {
        scale: 2,
        backgroundColor: '#ffffff',
        logging: false,
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight,
        useCORS: true,
        allowTaint: true,
        onclone: (clonedDoc) => {
          const clonedElement = clonedDoc.querySelector('[data-routine-grid]');
          if (clonedElement) {
            clonedElement.style.width = `${element.scrollWidth}px`;
            clonedElement.style.height = `${element.scrollHeight}px`;
          }
        }
      };

      html2canvas(tempContainer, options).then(canvas => {
        // Remove the temporary container
        document.body.removeChild(tempContainer);

        // Create download link
        const link = document.createElement('a');
        link.download = 'routine.png';
        link.href = canvas.toDataURL('image/png', 1.0);
        link.click();
      });
    }
  };

  // Fetch all courses on mount
  useEffect(() => {
    axios.get(`${API_BASE}/courses`).then(res => {
      setCourses(res.data);
      // Prepare options for the main course select, including disabled state
      const options = res.data.map(course => ({
        value: course.code,
        label: course.code,
        isDisabled: course.totalAvailableSeats <= 0,
        totalAvailableSeats: course.totalAvailableSeats
      }));
      // Sort options alphabetically
      options.sort((a, b) => a.label.localeCompare(b.label));
      setCourseOptions(options);
      setFilteredCourseOptions(options);
    });
  }, []);

  // Fetch course details when a course is selected
  useEffect(() => {
    if (selectedCourse) {
      axios.get(`${API_BASE}/course_details?course=${selectedCourse.value}`)
        .then(res => setSections(res.data));
    } else {
      setSections([]);
    }
  }, [selectedCourse]);

  // Fetch faculty options when routine page is shown
  useEffect(() => {
    if (selectedCourse) {
      axios.get(`${API_BASE}/course_details?course=${selectedCourse.value}`)
          .then(res => {
            const faculties = res.data.map(section => section.faculties).filter(Boolean);
            setRoutineFacultyOptions([...new Set(faculties)]);
          });
    }
  }, [selectedCourse]);

  useEffect(() => {
    if (routineCourses.length > 0) {
      const fetchFaculties = async () => {
        const allFaculties = new Set();
        for (const course of routineCourses) {
          try {
            const res = await axios.get(`${API_BASE}/course_details?course=${course.value}`);
            const faculties = res.data.map(section => section.faculties).filter(Boolean);
            faculties.forEach(f => allFaculties.add(f));
          } catch (error) {}
        }
        setRoutineFacultyOptions([...allFaculties]);
      };
      fetchFaculties();
    }
  }, [routineCourses]);

  // Toast and error banner state
  const [toast, setToast] = useState("");
  const [errorBanner, setErrorBanner] = useState("");

  return (
    <div className="app-container">
      <Toast message={toast} onClose={() => setToast("")} />
      <ErrorBanner message={errorBanner} onClose={() => setErrorBanner("")} />
      <AnimatedGridPattern
        numSquares={30}
        maxOpacity={0.3}
        duration={3}
        repeatDelay={1}
        className="animated-grid"
      />
      <div className="content-container">
        <div className="header">
          <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start', 
              marginBottom: '20px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '5px' }}>
                  <h1 className="usis-title">RoutineZ</h1>
                  <ApiStatus />
                </div>
                <div className="tagline">BracU&apos;s #1 LIVE Routine Generator</div>
              </div>
              {routineResult && (
                <button
                  onClick={handleDownloadPNG}
                  style={{
                    backgroundColor: '#1976d2',
                    color: 'white',
                    padding: '8px 16px',
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.9em'
                  }}
                >
                  Download PNG
                </button>
              )}
            </div>
          </div>
        </div>
        <div className="flex justify-center mb-6">
          <SeatStatusDialog />
        </div>
        <div className="tab-content">
          <div className="tab-pane fade show active" id="make-routine">
            <MakeRoutinePage setToast={setToast} setErrorBanner={setErrorBanner} />
          </div>
          </div>
        </div>
      <Footer />
    </div>
  );
}

export default App;