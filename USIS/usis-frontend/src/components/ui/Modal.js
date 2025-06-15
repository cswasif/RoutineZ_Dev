import React from "react";
import PropTypes from 'prop-types';

const Modal = ({ open, onClose, children }) => {
  if (!open) return null;

  // Prevent clicks inside the modal content from closing the modal
  const handleContentClick = (e) => {
    e.stopPropagation();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-filter backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-lg shadow-lg p-6 w-full mx-4 md:mx-auto compact-modal"
        style={{ maxWidth: '965px' }}
        onClick={handleContentClick}
      >
        {children}
      </div>
    </div>
  );
};

Modal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
};

export default Modal; 