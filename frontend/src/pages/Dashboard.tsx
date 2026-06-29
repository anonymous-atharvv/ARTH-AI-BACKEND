import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate, Navigate } from 'react-router-dom';
import apiClient from '../api/client';
import ArthScoreGauge from '../components/ArthScoreGauge';
import PLChart from '../components/PLChart';
import TransactionFeed from '../components/TransactionFeed';
import LanguageToggle from '../components/LanguageToggle';
import LoanImpactCalculator from '../components/LoanImpactCalculator';
import InsightCard from '../components/InsightCard';
import ArthScoreTrajectory from '../components/ArthScoreTrajectory';
import BenchmarkCard from '../components/BenchmarkCard';
import AAConsentButton from '../components/AAConsentButton';
import { useLanguage } from '../contexts/LanguageContext';
import type { DashboardSummary, ArthScore, PnlData, Transaction } from '../types';
import './Dashboard.css';

const DEMO_USER_ID = 'raju-demo-001';

export default function Dashboard() {
  const { userId } = useParams<{ userId: string }>();
  const authUserId = localStorage.getItem('arthai_user_id');
  const token = localStorage.getItem('arthai_token');

  if (!token) {
    return <Navigate to="/demo" replace />;
  }

  const uid = userId || authUserId || DEMO_USER_ID;
  if (uid !== authUserId) {
    return <Navigate to="/demo" replace />;
  }
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [score, setScore] = useState<ArthScore | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [pnl, setPnl] = useState<PnlData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [benchmarks, setBenchmarks] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pnlPeriod, setPnlPeriod] = useState('90d');

  useEffect(() => {
    loadAll();
  }, [uid, pnlPeriod]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [sumRes, scoreRes, pnlRes, txRes, historyRes, benchRes, forecastRes] = await Promise.all([
        apiClient.getSummary(uid),
        apiClient.getArthScore(uid),
        apiClient.getPnl(uid, pnlPeriod),
        apiClient.getTransactions(uid, 1, 50),
        apiClient.getArthScoreHistory(uid),
        apiClient.getPeerBenchmarks(uid),
        apiClient.getCashFlowForecast(uid),
      ]);
      setSummary(sumRes.data);
      setScore(scoreRes.data);
      setPnl(pnlRes.data);
      setTransactions(txRes.data.items || []);
      setHistory(historyRes.data.history || []);
      setBenchmarks(benchRes.data);
      setForecast(forecastRes.data);
    } catch (err) {
      console.error('Dashboard load failed:', err);
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>{t('Loading your financial dashboard...', 'आपका डैशबोर्ड लोड हो रहा है...')}</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dash-header">
        <div className="dash-brand">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <h1 className="brand-name">Arth<span className="brand-accent">AI</span></h1>
          </Link>
          <p className="brand-tagline">{t('Financial Intelligence', 'वित्तीय पासपोर्ट')}</p>
        </div>
        <div className="dash-header-right">
          <LanguageToggle />
          <Link to={`/transactions/${uid}`} className="nav-btn-link">
            {t('View Ledger', 'खाता बही देखें')}
          </Link>
          <Link to={`/passport/${uid}`} className="nav-btn-link passport-btn">
            {t('Financial Passport', 'वित्तीय पासपोर्ट')}
          </Link>
          <div className="user-badge">
            <span className="user-avatar">👤</span>
            <span className="user-name">{t('Raju Kumar', 'राजू कुमार')}</span>
          </div>
          <button 
            onClick={() => navigate('/demo')} 
            className="nav-btn-link logout-btn" 
            style={{ 
              background: '#dc262620', 
              color: '#f87171', 
              borderColor: '#dc262640',
              cursor: 'pointer' 
            }}
          >
            🚪 {t('Exit', 'निकास')}
          </button>
        </div>
      </header>

      {/* Insight Section */}
      {score && score.score > 0 && (
        <section className="dashboard-insights" style={{ padding: '24px 32px 0' }}>
          <InsightCard
            type="score_ready"
            data={{ score: score.score, loan: score.max_loan_eligible }}
          />
        </section>
      )}

      {/* KPI Cards */}
      <section className="kpi-grid">
        <div className="kpi-card kpi-income">
          <div className="kpi-icon">📈</div>
          <div className="kpi-info">
            <span className="kpi-label">{t('This Month Income', 'इस महीने की आय')}</span>
            <span className="kpi-value income">₹{(summary?.mtd_income || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
        <div className="kpi-card kpi-expense">
          <div className="kpi-icon">📉</div>
          <div className="kpi-info">
            <span className="kpi-label">{t('This Month Expenses', 'इस महीने का खर्च')}</span>
            <span className="kpi-value expense">₹{(summary?.mtd_expenses || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
        <div className="kpi-card kpi-profit">
          <div className="kpi-icon">💰</div>
          <div className="kpi-info">
            <span className="kpi-label">{t('Net Profit', 'शुद्ध लाभ')}</span>
            <span className={`kpi-value ${(summary?.mtd_net_profit || 0) >= 0 ? 'income' : 'expense'}`}>
              ₹{(summary?.mtd_net_profit || 0).toLocaleString('en-IN')}
            </span>
          </div>
        </div>
        <div className="kpi-card kpi-total">
          <div className="kpi-icon">📋</div>
          <div className="kpi-info">
            <span className="kpi-label">{t('Total Transactions', 'कुल लेनदेन')}</span>
            <span className="kpi-value neutral">{summary?.total_transactions || 0}</span>
          </div>
        </div>
      </section>

      {/* Main Grid */}
      <section className="dash-main-grid">
        <div className="dash-left">
          <div className="period-tabs">
            {['7d', '30d', '90d', '1y'].map((p) => (
              <button key={p} className={`period-btn ${pnlPeriod === p ? 'active' : ''}`}
                onClick={() => setPnlPeriod(p)}>{p}</button>
            ))}
          </div>
          {pnl && <PLChart data={pnl.series} period={pnlPeriod} />}
          {forecast && forecast.available && (
            <div className="forecast-card" style={{
              marginTop: '20px',
              padding: '20px',
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              backdropFilter: 'blur(12px)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🔮 {t('30-Day Cash Flow Forecast', '30-दिवसीय नकदी प्रवाह पूर्वानुमान')}
                </h3>
                <span style={{
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  background: 'rgba(74, 222, 128, 0.1)',
                  color: '#4ade80',
                  borderRadius: '12px',
                  border: '1px solid rgba(74, 222, 128, 0.2)'
                }}>
                  {forecast.confidence === 'high' ? t('High Confidence', 'उच्च आत्मविश्वास') :
                   forecast.confidence === 'medium' ? t('Medium Confidence', 'मध्यम आत्मविश्वास') :
                   t('Low Confidence', 'कम आत्मविश्वास')}
                </span>
              </div>
              <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', color: '#94a3b8', lineHeight: '1.5' }}>
                {t(
                  'Based on your transaction seasonality, we project your next month net cash flow to be: ',
                  'आपके लेनदेन की मौसमीता के आधार पर, हम अगले महीने आपके शुद्ध नकदी प्रवाह का अनुमान लगाते हैं: '
                )}
                <strong style={{ color: '#4ade80', fontSize: '1.1rem' }}>
                  ₹{forecast.projected_monthly_net.toLocaleString('en-IN')}
                </strong>
              </p>
              <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '8px' }}>
                {forecast.forecast.slice(0, 7).map((day: any, idx: number) => (
                  <div key={idx} style={{
                    minWidth: '90px',
                    padding: '10px',
                    background: 'rgba(15, 23, 42, 0.4)',
                    borderRadius: '8px',
                    textAlign: 'center',
                    border: '1px solid rgba(255, 255, 255, 0.04)'
                  }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                      {day.label}
                    </div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: day.forecast_net >= 0 ? '#4ade80' : '#f87171' }}>
                      {day.forecast_net >= 0 ? '+' : ''}₹{day.forecast_net}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="dash-right">
          {score && (
            <>
              <ArthScoreGauge
                score={score.score}
                grade={score.grade}
                maxLoan={score.max_loan_eligible}
                calculatedAt={score.calculated_at}
                dataPoints={score.data_points}
              />
              <div style={{ marginTop: '20px' }}>
                <LoanImpactCalculator maxLoan={score.max_loan_eligible} score={score.score} actualSurplus={summary?.mtd_net_profit || 0} />
              </div>
              {history && history.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <ArthScoreTrajectory history={history} />
                </div>
              )}
              {benchmarks && benchmarks.available && (
                <div style={{ marginTop: '20px' }}>
                  <BenchmarkCard data={benchmarks} />
                </div>
              )}
              <div style={{ marginTop: '20px' }}>
                <AAConsentButton userId={uid} />
              </div>
            </>
          )}
        </div>
      </section>

      {/* Category Breakdown + Transactions */}
      <section className="dash-bottom-grid">
        <div className="category-breakdown">
          <div className="cat-card">
            <h3 className="cat-title">🟢 {t('Income Categories', 'आय श्रेणियाँ')}</h3>
            <div className="cat-bars">
              {Object.entries(summary?.income_by_category || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([cat, amt]) => {
                  const maxAmt = Math.max(...Object.values(summary?.income_by_category || { x: 1 }));
                  return (
                    <div key={cat} className="cat-bar-row">
                      <span className="cat-bar-label">{cat.replace(/_/g, ' ')}</span>
                      <div className="cat-bar-track">
                        <div className="cat-bar-fill income" style={{ width: `${(amt / maxAmt) * 100}%` }}></div>
                      </div>
                      <span className="cat-bar-amt">₹{amt.toLocaleString('en-IN')}</span>
                    </div>
                  );
                })}
            </div>
          </div>
          <div className="cat-card">
            <h3 className="cat-title">🔴 {t('Expense Categories', 'खर्च श्रेणियाँ')}</h3>
            <div className="cat-bars">
              {Object.entries(summary?.expense_by_category || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([cat, amt]) => {
                  const maxAmt = Math.max(...Object.values(summary?.expense_by_category || { x: 1 }));
                  return (
                    <div key={cat} className="cat-bar-row">
                      <span className="cat-bar-label">{cat.replace(/_/g, ' ')}</span>
                      <div className="cat-bar-track">
                        <div className="cat-bar-fill expense" style={{ width: `${(amt / maxAmt) * 100}%` }}></div>
                      </div>
                      <span className="cat-bar-amt">₹{amt.toLocaleString('en-IN')}</span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
        <div className="dash-transactions">
          <TransactionFeed transactions={transactions} limit={10} />
        </div>
      </section>

      {/* Insight Card */}
      {score && score.score > 0 && (
        <section className="insight-section">
          <div className="insight-card">
            <div className="insight-icon">💡</div>
            <div className="insight-content">
              <h4>{t('AI Insight', 'AI अंतर्दृष्टि')}</h4>
              <p>{t(score.insight_en, score.insight_hi)}</p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
