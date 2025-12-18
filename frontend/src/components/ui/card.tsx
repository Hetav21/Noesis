import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className }) => {
  return (
    <div className={`bg-white text-gray-900 border border-gray-200 rounded-lg shadow-lg p-4 ${className}`}>
      {children}
    </div>
  );
};
