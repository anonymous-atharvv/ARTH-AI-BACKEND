import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate, Navigate } from 'react-router-dom';
import apiClient from '../api/client';
import LanguageToggle from '../components/LanguageToggle';
import LoadingSpinner from '../components/LoadingSpinner';
import { useLanguage } from '../contexts/LanguageContext';
import type { Transaction } from '../types';
import { CATEGORY_META, SOURCE_ICONS } from '../types';
import './Transactions.css';

const DEMO_USER_ID = 'raju-demo-001';

export default function Transactions() {
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

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<'all' | 'income' | 'expense'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    loadTransactions();
  }, [uid]);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getTransactions(uid, 1, 100);
      setTransactions(res.data.items || []);
    } catch (err) {
      console.error('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = transactions.filter((tx) => {
    const matchesType = filterType === 'all' || tx.type === filterType;
    const matchesCategory = selectedCategory === 'all' || tx.category_code === selectedCategory;
    const matchesSearch =
      (tx.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tx.counterparty || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesCategory && matchesSearch;
  });

  if (loading) {
    return <LoadingSpinner message={t('Loading your ledger...', 'आपका खाता-बही लोड हो रहा है...')} />;
  }

  // Get unique categories for dropdown, filtered to be non-null strings
  const categories = Array.from(new Set(transactions.map((tx) => tx.category_code))).filter((c): c is string => Boolean(c));

  return (
    <div className="tx-page">
      <header className="dash-header">
        <div className="dash-brand">
          <Link to={`/dashboard/${uid}`} className="back-link">
            ← <span className="brand-name">Arth<span className="brand-accent">AI</span> Ledger</span>
          </Link>
        </div>
        <div className="dash-header-right">
          <LanguageToggle />
          <Link to={`/dashboard/${uid}`} className="nav-btn-link">
            {t('Dashboard', 'डैशबोर्ड')}
          </Link>
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

      <div className="tx-container">
        <div className="tx-controls">
          <input
            type="text"
            placeholder={t('Search description...', 'विवरण खोजें...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="tx-search-input"
          />

          <div className="tx-filters">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="tx-select"
            >
              <option value="all">{t('All Types', 'सभी प्रकार')}</option>
              <option value="income">{t('Income Only', 'केवल आय')}</option>
              <option value="expense">{t('Expenses Only', 'केवल खर्च')}</option>
            </select>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="tx-select"
            >
              <option value="all">{t('All Categories', 'सभी श्रेणियां')}</option>
              {categories.map((catCode) => {
                const cat = CATEGORY_META[catCode || 'other_expense'];
                return (
                  <option key={catCode} value={catCode}>
                    {cat?.name || catCode}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        <div className="tx-table-card">
          <div className="tx-table-header">
            <h3>📖 {t('Ledger Book', 'खाता बही')}</h3>
            <span>{filtered.length} matching</span>
          </div>
          <div className="tx-table-wrapper">
            <table className="tx-table">
              <thead>
                <tr>
                  <th>{t('Date', 'तारीख')}</th>
                  <th>{t('Description', 'विवरण')}</th>
                  <th>{t('Category', 'श्रेणी')}</th>
                  <th>{t('Source', 'स्रोत')}</th>
                  <th>{t('Payment', 'भुगतान')}</th>
                  <th className="align-right">{t('Amount', 'राशि')}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((tx) => {
                  const cat = CATEGORY_META[tx.category_code || 'other_expense'];
                  const isIncome = tx.type === 'income';
                  return (
                    <tr key={tx.id}>
                      <td>
                        {new Date(tx.transaction_date).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="tx-desc-cell">
                        <div className="tx-desc-title">{tx.description || tx.counterparty || 'Transaction'}</div>
                      </td>
                      <td>
                        <span
                          className="tx-cat-badge"
                          style={{
                            backgroundColor: `${cat?.color || '#64748b'}20`,
                            color: cat?.color || '#94a3b8',
                          }}
                        >
                          {cat?.icon} {cat?.name || tx.category_code}
                        </span>
                      </td>
                      <td>
                        <span className="tx-source-badge">
                          {SOURCE_ICONS[tx.source] || '📝'} {tx.source}
                        </span>
                      </td>
                      <td>
                        <span className="tx-pay-method">{tx.payment_method?.toUpperCase()}</span>
                      </td>
                      <td className={`tx-amt-cell align-right ${isIncome ? 'income' : 'expense'}`}>
                        {isIncome ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="tx-empty-row">
                      {t('No transactions found.', 'कोई लेनदेन नहीं मिला।')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
