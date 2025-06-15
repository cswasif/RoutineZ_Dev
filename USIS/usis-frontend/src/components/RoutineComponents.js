import React from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { renderRoutineGrid } from '../App';
import CampusDaysDisplay from './CampusDaysDisplay';
import ExamSchedule from './ExamSchedule';

export const GenerateButton = ({
  routineCourses,
  selectedSectionsByFaculty,
  routineDays,
  routineTimes,
  commutePreference,
  setIsLoading,
  setRoutineError,
  setRoutineResult,
  setAiFeedback,
  setToast,
  setErrorBanner,
  setUsedAI
}) => {
  const handleGenerateRoutine = async () => {
    if (!routineCourses.length) {
      setErrorBanner("Please select at least one course.");
      return;
    }

    if (!Object.keys(selectedSectionsByFaculty).length) {
      setErrorBanner("Please select sections for your courses.");
      return;
    }

    setIsLoading(true);
    setRoutineError("");
    setRoutineResult(null);
    setAiFeedback(null);

    try {
      // Prepare sections data
      const selectedSections = [];
      Object.entries(selectedSectionsByFaculty).forEach(([courseCode, facultySelections]) => {
        Object.values(facultySelections).forEach(section => {
          if (section) selectedSections.push(section.section);
        });
      });

      // Call the API to generate routine
      const response = await axios.post(`${API_BASE}/generate_routine`, {
        sections: selectedSections,
        days: routineDays.map(d => d.value),
        times: routineTimes.map(t => t.value),
        commutePreference
      });

      if (response.data.error) {
        setRoutineError(response.data.error);
      } else {
        setRoutineResult(selectedSections);
        setToast("Routine generated successfully!");
      }
    } catch (error) {
      console.error("Error generating routine:", error);
      setRoutineError("Failed to generate routine. Please try again.");
    } finally {
      setIsLoading(false);
      setUsedAI(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleGenerateRoutine}
      style={{
        backgroundColor: '#4CAF50',
        color: 'white',
        padding: '10px 20px',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em',
        fontWeight: '500'
      }}
    >
      Generate Routine
    </button>
  );
};

export const GenerateAIButton = ({
  routineCourses,
  routineDays,
  routineTimes,
  commutePreference,
  setIsLoading,
  setRoutineError,
  setRoutineResult,
  setAiFeedback,
  setToast,
  setErrorBanner,
  setSelectedSectionsByFaculty,
  setUsedAI
}) => {
  const handleGenerateAIRoutine = async () => {
    if (!routineCourses.length) {
      setErrorBanner("Please select at least one course.");
      return;
    }

    setIsLoading(true);
    setRoutineError("");
    setRoutineResult(null);
    setAiFeedback(null);

    try {
      // Call the API to generate AI routine
      const response = await axios.post(`${API_BASE}/generate_ai_routine`, {
        courses: routineCourses.map(c => c.value),
        days: routineDays.map(d => d.value),
        times: routineTimes.map(t => t.value),
        commutePreference
      });

      if (response.data.error) {
        setRoutineError(response.data.error);
      } else {
        setRoutineResult(response.data.sections);
        setAiFeedback(response.data.feedback);
        setToast("AI Routine generated successfully!");
        
        // Update selected sections
        const newSelectedSectionsByFaculty = {};
        response.data.sections.forEach(section => {
          if (!newSelectedSectionsByFaculty[section.courseCode]) {
            newSelectedSectionsByFaculty[section.courseCode] = {};
          }
          newSelectedSectionsByFaculty[section.courseCode][section.faculties] = {
            value: section.sectionName,
            label: section.sectionName,
            section: section
          };
        });
        setSelectedSectionsByFaculty(newSelectedSectionsByFaculty);
      }
    } catch (error) {
      console.error("Error generating AI routine:", error);
      setRoutineError("Failed to generate AI routine. Please try again.");
    } finally {
      setIsLoading(false);
      setUsedAI(true);
    }
  };

  return (
    <button
      type="button"
      onClick={handleGenerateAIRoutine}
      style={{
        backgroundColor: '#2196F3',
        color: 'white',
        padding: '10px 20px',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em',
        fontWeight: '500'
      }}
    >
      Generate with AI
    </button>
  );
};

export const RoutineResult = ({
  routineGridRef,
  routineResult,
  routineError,
  aiFeedback,
  routineDays
}) => {
  return (
    <div ref={routineGridRef} data-routine-grid>
      {routineResult && (
        <div style={{ marginTop: "20px" }}>
          {routineError ? (
            <div style={{ color: "red", marginBottom: "20px" }}>{routineError}</div>
          ) : (
            <>
              {aiFeedback && (
                <div style={{ marginBottom: "20px", padding: "15px", backgroundColor: "#f8f9fa", borderRadius: "8px" }}>
                  <h4 style={{ marginTop: 0 }}>AI Feedback</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{aiFeedback}</p>
                </div>
              )}
              <CampusDaysDisplay routine={routineResult} />
              <div style={{ overflowX: "auto" }}>
                {renderRoutineGrid(routineResult, routineDays.map(d => d.value))}
              </div>
              <ExamSchedule sections={routineResult} />
            </>
          )}
        </div>
      )}
    </div>
  );
}; 