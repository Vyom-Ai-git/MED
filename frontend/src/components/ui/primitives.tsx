import React, { ForwardedRef, forwardRef } from "react";

// ==========================================
// BUTTON COMPONENT
// ==========================================
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = forwardRef(
  (
    { variant = "primary", size = "md", isLoading, children, className = "", disabled, ...props }: ButtonProps,
    ref: ForwardedRef<HTMLButtonElement>
  ) => {
    const baseStyle =
      "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";
    
    const variants = {
      primary: "bg-teal-600 hover:bg-teal-700 text-white shadow-sm focus:ring-teal-500",
      secondary: "bg-slate-100 hover:bg-slate-200 text-slate-700 focus:ring-slate-500",
      outline: "border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 focus:ring-teal-500",
      danger: "bg-red-600 hover:bg-red-700 text-white shadow-sm focus:ring-red-500",
      ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-slate-500",
    };

    const sizes = {
      sm: "px-3 py-1.5 text-xs",
      md: "px-4 py-2 text-sm",
      lg: "px-5 py-2.5 text-base",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

// ==========================================
// INPUT COMPONENT
// ==========================================
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef(
  (
    { label, error, helperText, icon, className = "", id, ...props }: InputProps,
    ref: ForwardedRef<HTMLInputElement>
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substring(2, 9)}`;
    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-semibold text-slate-700">
            {label}
          </label>
        )}
        <div className="relative rounded-lg shadow-sm">
          {icon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              {icon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`w-full text-sm rounded-lg border transition-colors duration-200 outline-none px-3.5 py-2.5 focus:ring-1
              ${icon ? "pl-10" : ""} 
              ${
                error
                  ? "border-red-300 text-red-900 placeholder-red-300 focus:border-red-500 focus:ring-red-500"
                  : "border-slate-200 text-slate-900 placeholder-slate-400 focus:border-teal-500 focus:ring-teal-500"
              } 
              ${className}`}
            {...props}
          />
        </div>
        {error && <span className="text-xs text-red-600">{error}</span>}
        {!error && helperText && <span className="text-xs text-slate-500">{helperText}</span>}
      </div>
    );
  }
);
Input.displayName = "Input";

// ==========================================
// SELECT COMPONENT
// ==========================================
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string | number; label: string }[];
}

export const Select = forwardRef(
  ({ label, error, options, className = "", id, ...props }: SelectProps, ref: ForwardedRef<HTMLSelectElement>) => {
    const selectId = id || `select-${Math.random().toString(36).substring(2, 9)}`;
    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label htmlFor={selectId} className="text-xs font-semibold text-slate-700">
            {label}
          </label>
        )}
        <select
          id={selectId}
          ref={ref}
          className={`w-full text-sm rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors duration-200
            ${error ? "border-red-300 focus:border-red-500 focus:ring-red-500 text-red-900" : ""}
            ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <span className="text-xs text-red-600">{error}</span>}
      </div>
    );
  }
);
Select.displayName = "Select";

// ==========================================
// BADGE (STATUS) COMPONENT
// ==========================================
interface BadgeProps {
  status: string;
  className?: string;
}

export const Badge = ({ status, className = "" }: BadgeProps) => {
  const statusStyles: Record<string, string> = {
    // Workflow States
    draft: "bg-slate-100 text-slate-700 border-slate-200",
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    processing: "bg-blue-50 text-blue-700 border-blue-200",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    verified: "bg-teal-50 text-teal-700 border-teal-200",
    published: "bg-indigo-50 text-indigo-700 border-indigo-200",
    failed: "bg-rose-50 text-rose-700 border-rose-200",
    cancelled: "bg-gray-100 text-gray-700 border-gray-200",
    
    // Billing States
    paid: "bg-emerald-100 text-emerald-800 border-emerald-200",
    partial: "bg-orange-50 text-orange-700 border-orange-200",
    refunded: "bg-indigo-100 text-indigo-800 border-indigo-200",
    
    // Active states
    active: "bg-emerald-50 text-emerald-700 border-emerald-200",
    inactive: "bg-slate-100 text-slate-700 border-slate-200",
  };

  const key = status.toLowerCase();
  const style = statusStyles[key] || "bg-slate-50 text-slate-600 border-slate-200";

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style} ${className}`}>
      {status}
    </span>
  );
};

// ==========================================
// CARD COMPONENT
// ==========================================
interface CardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  headerAction?: React.ReactNode;
  className?: string;
}

export const Card = ({ title, subtitle, children, headerAction, className = "" }: CardProps) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden ${className}`}>
      {(title || subtitle) && (
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between gap-4">
          <div>
            {title && <h3 className="text-base font-bold text-slate-900">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
};

// ==========================================
// TABLE COMPONENT
// ==========================================
interface TableColumn<T> {
  header: string;
  accessor: (row: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
}

export function Table<T>({ columns, data, isLoading, emptyMessage = "No data available" }: TableProps<T>) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-slate-100 shadow-sm">
      <table className="w-full text-left border-collapse bg-white">
        <thead>
          <tr className="bg-slate-50/75 border-b border-slate-100">
            {columns.map((col, idx) => (
              <th key={idx} className={`px-6 py-4 text-xs font-semibold text-slate-600 uppercase tracking-wider ${col.className || ""}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {isLoading ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-12 text-center">
                <div className="flex justify-center items-center gap-2.5">
                  <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-sm font-medium text-slate-500">Loading laboratory records...</span>
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-12 text-center text-sm text-slate-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-slate-50/50 transition-colors duration-150">
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className={`px-6 py-4 text-sm text-slate-700 ${col.className || ""}`}>
                    {col.accessor(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ==========================================
// MODAL COMPONENT
// ==========================================
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export const Modal = ({ isOpen, onClose, title, children, actions }: ModalProps) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Overlay */}
      <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Container */}
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="relative bg-white w-full max-w-lg rounded-xl border border-slate-200/80 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">{title}</h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 rounded-lg p-1 hover:bg-slate-50 transition-all"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6 max-h-[70vh] overflow-y-auto">{children}</div>

          {/* Footer */}
          {actions && (
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/75 flex justify-end gap-3">
              {actions}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==========================================
// TABS COMPONENT
// ==========================================
interface TabsProps {
  tabs: { id: string; label: string }[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs = ({ tabs, activeTab, onChange, className = "" }: TabsProps) => {
  return (
    <div className={`border-b border-slate-200 ${className}`}>
      <nav className="-mb-px flex space-x-8" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200
                ${
                  isActive
                    ? "border-teal-500 text-teal-600"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                }`}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
};

// ==========================================
// TOAST PROVIDER/TRIGGER STUB
// ==========================================
export interface ToastMessage {
  id: string;
  type: "success" | "error" | "info" | "warning";
  text: string;
}

export const Toast = ({ type, text, message, onClose }: { type: string; text?: string; message?: string; onClose: () => void }) => {
  const contentText = text || message || "";
  const bgColors: Record<string, string> = {
    success: "bg-emerald-50 text-emerald-800 border-emerald-200",
    error: "bg-rose-50 text-rose-800 border-rose-200",
    info: "bg-sky-50 text-sky-800 border-sky-200",
    warning: "bg-amber-50 text-amber-800 border-amber-200",
  };

  const icons: Record<string, React.ReactNode> = {
    success: (
      <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  };

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg max-w-sm w-full animate-in slide-in-from-bottom-5 duration-300 ${bgColors[type] || bgColors.info}`}>
      {icons[type] || icons.info}
      <span className="text-sm font-semibold flex-1">{contentText}</span>
      <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};
