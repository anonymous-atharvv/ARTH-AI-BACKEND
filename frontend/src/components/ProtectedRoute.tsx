import React from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface Props {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const { token, userId: authUserId } = useAuth();
  const { userId } = useParams<{ userId?: string }>();

  if (!token || !authUserId) {
    return <Navigate to="/demo" replace />;
  }

  // Tenant Isolation check:
  // If a specific userId is requested in the route parameters, it must match the authenticated userId.
  if (userId && userId !== authUserId) {
    console.warn(`Access denied. Route user ID (${userId}) does not match authenticated user ID (${authUserId}).`);
    return <Navigate to="/demo" replace />;
  }

  return <>{children}</>;
}
