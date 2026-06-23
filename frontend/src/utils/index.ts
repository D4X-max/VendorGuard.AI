import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getRiskColor(score: number): string {
  if (score >= 80) return 'text-red-600';
  if (score >= 60) return 'text-orange-500';
  if (score >= 40) return 'text-yellow-500';
  return 'text-green-600';
}

export function getRiskBadgeColor(score: number): string {
  if (score >= 80) return 'bg-red-100 text-red-700 border-red-200';
  if (score >= 60) return 'bg-orange-100 text-orange-700 border-orange-200';
  if (score >= 40) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
  return 'bg-green-100 text-green-700 border-green-200';
}

export function getSeverityColor(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'CRITICAL': return 'bg-red-100 text-red-700 border-red-200';
    case 'HIGH':     return 'bg-orange-100 text-orange-700 border-orange-200';
    case 'MEDIUM':   return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'LOW':      return 'bg-blue-100 text-blue-700 border-blue-200';
    default:         return 'bg-gray-100 text-gray-700 border-gray-200';
  }
}

export function getStatusColor(status: string): string {
  switch (status.toUpperCase()) {
    case 'APPROVED':   return 'bg-green-100 text-green-700 border-green-200';
    case 'REJECTED':   return 'bg-red-100 text-red-700 border-red-200';
    case 'REVIEWED':   return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'DRAFT':      return 'bg-gray-100 text-gray-700 border-gray-200';
    case 'COMPLETED':  return 'bg-green-100 text-green-700 border-green-200';
    case 'PENDING':    return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'FAILED':     return 'bg-red-100 text-red-700 border-red-200';
    default:           return 'bg-gray-100 text-gray-700 border-gray-200';
  }
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}