import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Format currency
export function formatCurrency(amount, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}

// Format date
export function formatDate(date) {
  if (!date) return '-';
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Format datetime
export function formatDateTime(date) {
  if (!date) return '-';
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Format time
export function formatTime(date) {
  if (!date) return '-';
  return new Date(date).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Get status color class
export function getStatusColor(status) {
  const colors = {
    registered: 'bg-slate-100 text-slate-700',
    sample_collected: 'bg-blue-100 text-blue-700',
    in_lab: 'bg-amber-100 text-amber-700',
    under_review: 'bg-violet-100 text-violet-700',
    approved: 'bg-emerald-100 text-emerald-700',
    report_released: 'bg-indigo-100 text-indigo-700',
    pending: 'bg-slate-100 text-slate-700',
    collected: 'bg-blue-100 text-blue-700',
    received: 'bg-amber-100 text-amber-700',
    processing: 'bg-violet-100 text-violet-700',
    completed: 'bg-emerald-100 text-emerald-700',
    rejected: 'bg-rose-100 text-rose-700',
    paid: 'bg-emerald-100 text-emerald-700',
    partial: 'bg-amber-100 text-amber-700',
    refunded: 'bg-slate-100 text-slate-700',
  };
  return colors[status] || 'bg-slate-100 text-slate-700';
}

// Get priority color class
export function getPriorityColor(priority) {
  const colors = {
    normal: 'bg-slate-100 text-slate-600',
    urgent: 'bg-amber-100 text-amber-700',
    stat: 'bg-rose-100 text-rose-700',
  };
  return colors[priority] || 'bg-slate-100 text-slate-600';
}

// Format status label
export function formatStatus(status) {
  if (!status) return '-';
  return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Generate initials
export function getInitials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// Calculate age from date
export function calculateAge(birthDate) {
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

// Debounce function
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
