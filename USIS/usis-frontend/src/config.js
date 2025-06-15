// Determine if we're running in development or production
const isDevelopment = process.env.NODE_ENV === 'development';

// Set the API base URL based on the environment
export const API_BASE = isDevelopment ? 'http://localhost:5000/api' : '/api'; 