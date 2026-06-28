import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import ArthScoreGauge from '../components/ArthScoreGauge';
import PLChart from '../components/PLChart';
import TransactionFeed from '../components/TransactionFeed';
import LanguageToggle from '../components/LanguageToggle';
import LoanImpactCalculator from '../components/LoanImpactCalculator';
import InsightCard from '../components/InsightCard';
import { useLanguage } from '../contexts/LanguageContext';
import type { DashboardSummary, ArthScore, PnlData, Transaction } from '../types';
import './Dashboard.css';

const DEMO_USER_ID = 'raju-demo-001';

export default function Dashboard() {
  const { userId } = useParams<{ userId: string }>();
  const uid = userId || DEMO_USER_ID;
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [score, setScore] = useState<ArthScore | null>(null);
  const [pnl, setPnl] = useState<PnlData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [pnlPeriod, setPnlPeriod] = useState('90d');

  useEffect(() => {
    loadAll();
  }, [uid, pnlPeriod]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [sumRes, scoreRes, pnlRes, txRes] = await Promise.all([
        apiClient.getSummary(uid),
        apiClient.getArthScore(uid),
        apiClient.getPnl(uid, pnlPeriod),
        apiClient.getTransactions(uid, 1, 50),
      ]);
      setSummary(sumRes.data);
      setScore(scoreRes.data);
      setPnl(pnlRes.data);
      setTransactions(txRes.data.items || []);
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
        </div>
        <div className="dash-right">
          {score && (
            <>
              <ArthScoreGauge
                score={score.score}
                grade={score.grade}
                maxLoan={score.max_loan_eligible}
              />
              <div style={{ marginTop: '20px' }}>
                <LoanImpactCalculator maxLoan={score.max_loan_eligible} score={score.score} />
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
