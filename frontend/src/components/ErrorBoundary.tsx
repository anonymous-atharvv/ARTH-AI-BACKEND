import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          backgroundColor: '#0a0a0c',
          color: '#ffffff',
          fontFamily: 'Inter, system-ui, sans-serif',
          textAlign: 'center',
          padding: '20px'
        }}>
          <div style={{
            background: 'radial-gradient(circle, rgba(239,68,68,0.15) 0%, rgba(0,0,0,0) 70%)',
            position: 'absolute',
            width: '600px',
            height: '600px',
            zIndex: 0
          }}></div>
          <div style={{ zIndex: 1, maxWidth: '500px' }}>
            <span style={{ fontSize: '64px', marginBottom: '20px', display: 'block' }}>⚠️</span>
            <h1 style={{ fontSize: '28px', fontWeight: 700, margin: '0 0 10px 0', background: 'linear-gradient(to right, #ff6b6b, #ff8e8e)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Oops! Something went wrong
            </h1>
            <p style={{ color: '#9ca3af', fontSize: '16px', lineHeight: 1.6, margin: '0 0 30px 0' }}>
              An unexpected error occurred in the application. Please try reloading the page.
            </p>
            {this.state.error && (
              <pre style={{
                background: '#151518',
                border: '1px solid #27272a',
                padding: '15px',
                borderRadius: '8px',
                color: '#ef4444',
                fontSize: '13px',
                overflowX: 'auto',
                textAlign: 'left',
                marginBottom: '30px',
                maxHeight: '200px'
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={this.handleReload}
              style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                color: '#ffffff',
                border: 'none',
                padding: '12px 28px',
                borderRadius: '9999px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
                transition: 'transform 0.2s, box-shadow 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.02)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.6)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = '0 4px 14px rgba(99, 102, 241, 0.4)';
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
