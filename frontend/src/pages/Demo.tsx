import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import './Demo.css';

export default function Demo() {
  const [seeded, setSeeded] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { loginDemo, loading } = useAuth();

  const handleSeed = async () => {
    setError('');
    try {
      const demoUserId = await loginDemo();
      setSeeded(true);
      setTimeout(() => navigate(`/dashboard/${demoUserId}`), 1500);
    } catch (err: any) {
      setError(err?.message || 'Failed to seed demo data');
    }
  };

  return (
    <div className="demo-page">
      <div className="demo-glow"></div>
      <div className="demo-container">
        <div className="demo-logo">
          <h1 className="demo-brand">Arth<span>AI</span></h1>
          <p className="demo-subtitle">India's Agentic Financial Intelligence Layer</p>
        </div>

        <div className="demo-card">
          <div className="demo-avatar">👤</div>
          <h2 className="demo-name">Meet Raju Kumar</h2>
          <p className="demo-bio">Kirana Store Owner • Laxmi Nagar, Delhi</p>
          <div className="demo-stats">
            <div className="demo-stat">
              <span className="stat-value">90</span>
              <span className="stat-label">Days</span>
            </div>
            <div className="demo-stat">
              <span className="stat-value">40+</span>
              <span className="stat-label">Transactions</span>
            </div>
            <div className="demo-stat">
              <span className="stat-value">₹3.5L+</span>
              <span className="stat-label">Income</span>
            </div>
          </div>

          <p className="demo-desc">
            Experience ArthAI through Raju's eyes — a small kirana shop owner who uses
            WhatsApp to track his daily sales, expenses, and generates a Financial Passport
            for his first formal bank loan.
          </p>

          {seeded ? (
            <div className="demo-success">
              <span className="success-icon">✅</span>
              <p>Demo loaded! Redirecting to dashboard...</p>
            </div>
          ) : (
            <button className="demo-btn" onClick={handleSeed} disabled={loading}>
              {loading ? (
                <>
                  <span className="btn-spinner"></span>
                  Loading Raju's data...
                </>
              ) : (
                <>🚀 Load Raju's 90-Day Demo</>
              )}
            </button>
          )}

          {error && <p className="demo-error">❌ {error}</p>}
        </div>

        <div className="demo-features">
          <div className="feature">
            <span>📸</span>
            <h4>Receipt OCR</h4>
            <p>Send a photo, AI extracts the data</p>
          </div>
          <div className="feature">
            <span>🎤</span>
            <h4>Voice Notes</h4>
            <p>Speak in Hindi, we understand</p>
          </div>
          <div className="feature">
            <span>📊</span>
            <h4>ArthScore</h4>
            <p>Creditworthiness without CIBIL</p>
          </div>
          <div className="feature">
            <span>📄</span>
            <h4>Financial Passport</h4>
            <p>Bank-grade PDF for loans</p>
          </div>
        </div>
      </div>
    </div>
  );
}
