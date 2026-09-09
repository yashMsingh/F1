import React, { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="card border-red-500/30 bg-red-950/20 p-6 rounded-lg my-4 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <h3 className="text-lg font-semibold text-red-200">
            {this.props.fallbackTitle || "Something went wrong in this section"}
          </h3>
          <p className="text-sm text-red-300/80 mt-1 mb-4">
            {this.state.error?.message || "An unexpected error occurred while rendering."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="btn btn-secondary inline-flex items-center gap-2 text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Section
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export const LoadingSkeleton: React.FC<{ rows?: number; className?: string }> = ({
  rows = 5,
  className = "",
}) => {
  return (
    <div className={`space-y-3 animate-pulse ${className}`} aria-label="Loading data">
      <div className="h-6 bg-surface-elevated/60 rounded w-1/4 mb-4"></div>
      {Array.from({ length: rows }).map((_, idx) => (
        <div key={idx} className="h-10 bg-surface-elevated/40 rounded w-full"></div>
      ))}
    </div>
  );
};
