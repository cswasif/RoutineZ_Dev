import React from 'react';

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
    // Add lab schedule days
    if (section.labSchedules) {
      const labSchedules = Array.isArray(section.labSchedules) ? section.labSchedules : 
        (section.labSchedules.classSchedules || []);
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

export default CampusDaysDisplay; 