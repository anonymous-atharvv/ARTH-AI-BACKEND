// frontend/src/components/AAConsentButton.tsx
import { useState } from 'react';
import apiClient from '../api/client';
import { useLanguage } from '../contexts/LanguageContext';

export default function AAConsentButton({ userId }: { userId: string }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'link_ready' | 'error'>('idle');
  const [consentLink, setConsentLink] = useState('');
  const { t } = useLanguage();

  const handleInitiate = async () => {
    setStatus('loading');
    try {
      const res = await apiClient.initiateAAConsent(userId);
      if (res.data && res.data.redirect_url) {
        setConsentLink(res.data.redirect_url);
        setStatus('link_ready');
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    }
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', borderRadius: '16px', border: '1px solid #334155' }}>
      <h3 style={{ color: '#f1f5f9', fontSize: '15px', fontWeight: 700, marginBottom: '8px' }}>
        🏦 {t('Link Your Bank Account', 'अपना बैंक खाता जोड़ें')}
      </h3>
      <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px', lineHeight: 1.6 }}>
        {t(
          'Import your bank transactions automatically using RBI\'s Account Aggregator framework. Your consent, your data, your control.',
          'RBI के Account Aggregator से अपने बैंक transactions automatically import करें।'
        )}
      </p>
      {status === 'idle' && (
        <button onClick={handleInitiate} style={{
          background: 'linear-gradient(135deg, #1e40af, #3b82f6)',
          color: '#fff', border: 'none', borderRadius: '10px',
          padding: '12px 20px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
        }}>
          🔗 {t('Connect Bank (AA Framework)', 'बैंक जोड़ें (AA Framework)')}
        </button>
      )}
      {status === 'loading' && (
        <button disabled style={{
          background: '#1e293b',
          color: '#64748b', border: 'none', borderRadius: '10px',
          padding: '12px 20px', fontSize: '14px', fontWeight: 600,
        }}>
          ⏳ {t('Connecting...', 'जोड़ रहा है...')}
        </button>
      )}
      {status === 'link_ready' && (
        <a href={consentLink} target="_blank" rel="noopener noreferrer" style={{
          display: 'inline-block', background: '#16a34a', color: '#fff',
          borderRadius: '10px', padding: '12px 20px', fontSize: '14px',
          fontWeight: 600, textDecoration: 'none',
        }}>
          ✅ {t('Approve Consent →', 'सहमति दें →')}
        </a>
      )}
      {status === 'error' && (
        <div>
          <p style={{ color: '#f87171', fontSize: '13px', marginBottom: '8px' }}>
            {t('Failed to initiate. Please try again.', 'प्रयास विफल। दोबारा करें।')}
          </p>
          <button onClick={handleInitiate} style={{
            background: 'linear-gradient(135deg, #1e40af, #3b82f6)',
            color: '#fff', border: 'none', borderRadius: '10px',
            padding: '12px 20px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
          }}>
            🔗 {t('Retry Connect', 'पुनः प्रयास करें')}
          </button>
        </div>
      )}
    </div>
  );
}
