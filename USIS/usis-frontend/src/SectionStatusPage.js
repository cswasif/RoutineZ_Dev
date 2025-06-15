// src/SectionStatusPage.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import Select from "react-select";
import './App.css'; // Assuming shared styles
import { Link } from 'react-router-dom'; // Import Link for navigation
import { formatTime12Hour } from './App';
import { API_BASE } from './config';

// Helper function to normalize lab schedules to array format
const getLabSchedulesArray = (section) => {
  const labSchedules = section.labSchedules;
  if (!labSchedules) return [];
  
  // Handle old format (array of schedules)
  if (Array.isArray(labSchedules)) {
    return labSchedules.map(sched => ({
      ...sched,
      room: section.labRoomName || sched.room || "TBA"
    }));
  }
  
  // Handle new format (object with classSchedules)
  if (labSchedules.classSchedules && Array.isArray(labSchedules.classSchedules)) {
    return labSchedules.classSchedules.map(sched => ({
      ...sched,
      room: section.labRoomName || sched.room || "TBA",
      faculty: section.labFaculties || "TBA"
    }));
  }
  
  return [];
};

function SectionStatusPage() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [sections, setSections] = useState([]);

  // Fetch all courses on mount
  useEffect(() => {
    axios.get(`${API_BASE}/courses`).then(res => setCourses(res.data));
  }, []);

  // Fetch course details when a course is selected
  useEffect(() => {
    if (selectedCourse) {
      axios
        .get(`${API_BASE}/course_details?course=${selectedCourse.value}`)
        .then(res => setSections(res.data));
    } else {
      setSections([]);
    }
  }, [selectedCourse]);

  // Sort sections by sectionName (ascending)
  const sortedSections = sections.slice().sort((a, b) => {
    const nameA = a.sectionName || '';
    const nameB = b.sectionName || '';
    return nameA.localeCompare(nameB, undefined, { numeric: true, sensitivity: 'base' });
  });

  return (
    <div style={{ maxWidth: 1200, margin: "2em auto", fontFamily: "sans-serif", border: "1px solid #ddd", borderRadius: 8 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderBottom: "1px solid #ddd", background: "#f8f8f8" }}>
        <h3 style={{ margin: 0 }}>Section Status</h3>
        {/* "Make Smart Routine" Button */}
        <Link
          to="/make-routine" // Navigate to the Make Routine page
          style={{
            padding: '8px 15px',
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            textDecoration: 'none', // Remove underline from link
            fontSize: '0.9em'
          }}
        >
          Make Smart Routine
        </Link>
         <div style={{ fontSize: "0.9em", color: "#555", marginLeft: '20px' }}>UNDERGRADUATE-SUMMER 2025</div> {/* Moved this slightly */}
      </div>

      {/* Controls Area */}
      <div style={{ padding: "10px 20px", borderBottom: "1px solid #ddd", display: "flex", alignItems: "center" }}>
        <div style={{ flexGrow: 1, marginRight: 20 }}>
           <Select
            options={courses.map(c => ({ value: c.code, label: c.code }))}
            value={selectedCourse}
            onChange={setSelectedCourse}
            placeholder="Search or select Course Code..."
            styles={{ container: (provided) => ({ ...provided, width: 200 }) }}
          />
        </div>
        {/* Placeholder icons removed */}
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        {selectedCourse && sections.length === 0 && (
           <div style={{padding: "20px", textAlign: "center"}}>No sections found for this course.</div>
        )}
        {sections.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f0f0f0" }}>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>COURSE CO...</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>SECTION </th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>CREDIT</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>FACULTY </th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>TOTAL SEAT</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>SEAT BOOKED </th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>SEAT REMAINING</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>Class Schedule</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>Lab Schedule</th>
                <th style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>Exam Day</th>
              </tr>
            </thead>
            <tbody>
              {sortedSections.map((section, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.courseCode}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.sectionName}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.courseCredit}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.faculties || 'TBA'}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.capacity}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.consumedSeat}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>{section.capacity - section.consumedSeat}</td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>
                      {section.sectionSchedule && section.sectionSchedule.classSchedules
                          ? section.sectionSchedule.classSchedules.map((sched, i) => (
                              <div key={i}>
                                  {sched.day}: {formatTime12Hour(sched.startTime)} - {formatTime12Hour(sched.endTime)} {section.roomName && `(${section.roomName})`}
                              </div>
                          ))
                          : "N/A"}
                  </td>
                  <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>
                      {getLabSchedulesArray(section).length > 0
                          ? getLabSchedulesArray(section).map((labSched, i) => (
                              <div key={i}>
                                  {labSched.day}: {formatTime12Hour(labSched.startTime)} - {formatTime12Hour(labSched.endTime)} {labSched.room && `(${labSched.room})`}
                              </div>
                          ))
                          : "N/A"}
                  </td>
                   <td style={{ border: "1px solid #ccc", padding: "8px", textAlign: "left" }}>
                       {section.sectionSchedule ? (
                           <>
                               {section.sectionSchedule.midExamDetail && <div>Mid: {section.sectionSchedule.midExamDetail}</div>}
                               {section.sectionSchedule.finalExamDetail && <div>Final: {section.sectionSchedule.finalExamDetail}</div>}
                               {!section.sectionSchedule.midExamDetail && !section.sectionSchedule.finalExamDetail && 'N/A'}
                           </>
                       ) : 'N/A'}
                   </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination/Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderTop: "1px solid #ddd", background: "#f8f8f8", fontSize: "0.9em" }}>
          <div>{/* Left controls placeholder removed */}</div>
          <div style={{ display: "flex", alignItems: "center" }}>
              <span>Page Size:</span>
              <select style={{ marginLeft: 5, marginRight: 10 }}>
                  <option>10</option>
                  <option>25</option>
                  <option>50</option>
                  <option>100</option>
              </select>
              <span>1 to {sortedSections.length} of {sortedSections.length}</span> {/* Simple count */}
          </div>
      </div>
    </div>
  );
}

export default SectionStatusPage;