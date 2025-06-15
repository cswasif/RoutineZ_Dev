import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Select from 'react-select';
import { API_BASE } from '../config';

const ExamSchedule = () => {
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [courses, setCourses] = useState([]);
  const [sections, setSections] = useState([]);
  const [isLoadingSections, setIsLoadingSections] = useState(false);

  // Fetch all courses on mount
  useEffect(() => {
    axios.get(`${API_BASE}/courses`).then(res => {
      setCourses(res.data);
    });
  }, []);

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
      <h2 className="seat-status-heading">Exam Dates</h2>
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
        <div className="seat-status-message info">Please select a course to view exam dates.</div>
      )}
      {selectedCourse && !isLoadingSections && sections.length === 0 && (
        <div className="seat-status-message warning">No exam dates available for this course.</div>
      )}
      {selectedCourse && sections.length > 0 && (
        <div className="seat-status-table-wrapper">
          <table className="seat-status-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Faculty</th>
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

export default ExamSchedule; 