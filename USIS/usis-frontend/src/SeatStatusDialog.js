import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Modal from './components/ui/Modal';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './components/ui/table';
import axios from 'axios';
import { Button } from "./components/ui/button";
import { formatTime12Hour } from './App';
import { API_BASE } from './config';

const InfoMessage = ({ text }) => (
  <p className="mt-4 text-center text-sm text-muted-foreground">{text}</p>
);

InfoMessage.propTypes = {
  text: PropTypes.string.isRequired,
};

const SeatStatusDialog = () => {
  const [open, setOpen] = useState(false);
  const [courses, setCourses] = useState([]);
  const [courseOptions, setCourseOptions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);

  useEffect(() => {
    if (!open) {
      setSections([]);
      setSelected(null);
      setCourses([]);
      setCourseOptions([]);
      setSearchTerm('');
      setIsSuggestionsOpen(false);
      return;
    }

    setLoading(true);
    axios
      .get(`${API_BASE}/courses`)
      .then((res) => {
        setCourses(res.data);
        const sortedCourses = res.data.map((c) => ({ value: c.code, label: c.code })).sort((a, b) => a.label.localeCompare(b.label));
        setCourseOptions(sortedCourses);
        setSearchTerm('');
        setSelected(null);
      })
      .catch((error) => {
        console.error('Failed to fetch courses:', error);
        setCourses([]);
        setCourseOptions([]);
      })
      .finally(() => setLoading(false));
  }, [open]);

  useEffect(() => {
    if (!open || !selected) {
      setSections([]);
      return;
    }

    const fetchSections = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE}/course_details?course=${selected.value}`);
        if (Array.isArray(res.data)) {
          setSections(res.data.map((section) => ({ ...section, courseCode: selected.value })));
        } else {
          setSections([]);
        }
      } catch (error) {
        console.error('Failed to fetch sections for', selected.value, ':', error);
        setSections([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSections();
  }, [open, selected]);

  const handleInputChange = (event) => {
    const value = event.target.value;
    setSearchTerm(value);
    setSelected(null);
    setSections([]);

    const filteredOptions = courses
      .map((c) => ({ value: c.code, label: c.code }))
      .filter(option => option.label.toLowerCase().includes(value.toLowerCase()));
    setCourseOptions(filteredOptions);

    if ((value.length > 0 && filteredOptions.length > 0) || (value.length === 0 && courses.length > 0)) {
      setIsSuggestionsOpen(true);
    } else {
      setIsSuggestionsOpen(false);
    }
  };

  const handleOptionSelect = (option) => {
    setSelected(option);
    setSearchTerm(option.label);
    setIsSuggestionsOpen(false);
  };

  const handleInputFocus = () => {
    if (courses.length > 0) {
      setIsSuggestionsOpen(true);
    }
  };

  const handleInputBlur = () => {
    setTimeout(() => {
      setIsSuggestionsOpen(false);
    }, 200);
  };

  const hasAvailableSeats = sections.some(
    (item) => item.availableSeats > 0
  );

  const getLabSchedulesArray = (labSchedules, section) => {
    if (Array.isArray(labSchedules)) return labSchedules;
    if (labSchedules && typeof labSchedules === 'object' && Array.isArray(labSchedules.classSchedules)) {
      return labSchedules.classSchedules.map(sched => ({
        ...sched,
        room: section?.labRoomName || sched.room || 'TBA',
      }));
    }
    return [];
  };

  return (
    <>
      <Button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open seat status dialog"
        className="mt-4 md:mt-0"
        style={{
          padding: '10px 20px',
          fontSize: '16px'
        }}
      >
        Seat Status
      </Button>
      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="mb-4 w-full relative">
          <input
            type="text"
            placeholder="Search or select a course..."
            value={searchTerm}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />

          {isSuggestionsOpen && courseOptions.length > 0 && (
            <ul className="absolute z-50 w-full mt-1 rounded-md border border-black border-2 bg-white shadow-lg max-h-[200px] overflow-y-auto">
              {courseOptions.map(option => (
                <li
                  key={option.value}
                  onClick={() => handleOptionSelect(option)}
                  className="px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
                >
                  {option.label}
                </li>
              ))}
            </ul>
          )}

          {loading && courses.length === 0 && searchTerm === '' && (
            <div className="text-center py-2 text-gray-500 text-sm">Loading courses...</div>
          )}
          {searchTerm !== '' && courseOptions.length === 0 && !loading && (
            <div className="text-center py-2 text-gray-500 text-sm">No matching courses found.</div>
          )}
          {!loading && courses.length === 0 && searchTerm === '' && (
            <div className="text-center py-2 text-gray-500 text-sm">No courses loaded.</div>
          )}
        </div>
        <div className="min-h-[200px] max-h-[400px] overflow-y-auto overflow-x-auto">
          {loading && selected ? (
            <div className="text-center py-8 text-gray-500">Loading sections...</div>
          ) : !selected && searchTerm === '' ? (
            <InfoMessage text="Search or select a course from the list above to see seat status." />
          ) : sections.length === 0 && !loading && (selected || searchTerm !== '') ? (
            <InfoMessage text="No seat available for this course." />
          ) : hasAvailableSeats ? (
            <div className="min-w-[900px]">
              <Table>
                <TableHeader className="bg-transparent">
                  <TableRow className="border-border hover:bg-transparent [&>:not(:last-child)]:border-r">
                    <TableHead className="px-2 py-2 text-sm font-bold">Section</TableHead>
                    <TableHead className="px-2 py-2 text-sm font-bold">Faculty</TableHead>
                    <TableHead className="px-2 py-2 text-sm font-bold">Seats</TableHead>
                    <TableHead className="px-2 py-2 text-sm font-bold max-w-[150px] truncate">
                      Schedule
                    </TableHead>
                    <TableHead className="px-2 py-2 text-sm font-bold max-w-[120px] truncate">
                      Midterm Exam
                    </TableHead>
                    <TableHead className="px-2 py-2 text-sm font-bold max-w-[120px] truncate">
                      Final Exam
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="[&_td:first-child]:rounded-l-lg [&_td:last-child]:rounded-r-lg">
                  {[...sections].sort((a, b) => {
                    const sectionA = parseInt(a.sectionName, 10) || 0;
                    const sectionB = parseInt(b.sectionName, 10) || 0;
                    return sectionA - sectionB;
                  }).map((item) => (
                    <TableRow
                      key={item.sectionId || `${item.courseCode}-${item.sectionName}`}
                      className="border-border hover:bg-transparent [&>:not(:last-child)]:border-r text-sm"
                    >
                      <TableCell className="px-2 py-2 font-semibold align-top whitespace-nowrap text-sm">
                        {item.sectionName}
                        <div className="text-xs text-gray-500 font-normal">{item.courseCode}</div>
                      </TableCell>
                      <TableCell className="px-2 py-2 align-top whitespace-nowrap text-sm">
                        {item.faculties || 'TBA'}
                      </TableCell>
                      <TableCell className="px-2 py-2 align-top whitespace-nowrap text-sm">
                        {typeof item.availableSeats !== 'undefined'
                          ? `${item.availableSeats} / ${item.capacity}`
                          : '-'}
                      </TableCell>
                      <TableCell
                        className="px-1 py-1 align-top max-w-[150px] truncate text-xs"
                        title={[
                          ...(item.sectionSchedule?.classSchedules || []).map(
                            (sched) => `${sched.day} ${sched.startTime} - ${sched.endTime}`
                          ),
                          ...getLabSchedulesArray(item.labSchedules, item).map(
                            (sched) => `Lab: ${sched.day} ${sched.startTime} - ${sched.endTime} (${sched.room || ''})`
                          ),
                        ].join('\n')}
                      >
                        <div className="flex flex-col gap-0.5">
                          {(item.sectionSchedule?.classSchedules || []).map((sched, i) => (
                            <span key={`${sched.day}-${sched.startTime}-${i}`} className="truncate">
                              {sched.day} {formatTime12Hour(sched.startTime)} - {formatTime12Hour(sched.endTime)}
                            </span>
                          ))}
                          {getLabSchedulesArray(item.labSchedules, item).map((sched, i) => (
                            <span
                              key={`lab-${sched.day}-${sched.startTime}-${i}`}
                              className="truncate text-gray-600 text-xs"
                            >
                              Lab: {sched.day} {formatTime12Hour(sched.startTime)} - {formatTime12Hour(sched.endTime)}
                              {sched.room ? ` (${sched.room})` : ''}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell
                        className="px-1 py-1 align-top max-w-[120px] truncate text-xs"
                        title={`${item.midExamDate}${item.formattedMidExamTime ? `\n${item.formattedMidExamTime}` : ''}`}
                      >
                        {item.midExamDate ? (
                          <>
                            <div className="truncate">{item.midExamDate}</div>
                            {item.formattedMidExamTime && (
                              <div className="text-gray-500 text-xs truncate">
                                {item.formattedMidExamTime}
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400 text-[10px]">-</span>
                        )}
                      </TableCell>
                      <TableCell
                        className="px-1 py-1 align-top max-w-[120px] truncate text-xs"
                        title={`${item.finalExamDate}${item.formattedFinalExamTime ? `\n${item.formattedFinalExamTime}` : ''}`}
                      >
                        {item.finalExamDate ? (
                          <>
                            <div className="truncate">{item.finalExamDate}</div>
                            {item.formattedFinalExamTime && (
                              <div className="text-gray-500 text-xs truncate">
                                {item.formattedFinalExamTime}
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400 text-[10px]">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <InfoMessage text="No seat available for this course." />
          )}
        </div>
      </Modal>
    </>
  );
};

export default SeatStatusDialog;