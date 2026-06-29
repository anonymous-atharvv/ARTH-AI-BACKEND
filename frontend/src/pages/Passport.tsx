import { useState } from 'react';
import { useParams, Link, useNavigate, Navigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import apiClient from '../api/client';
import LanguageToggle from '../components/LanguageToggle';
import './Passport.css';

const DEMO_USER_ID = 'raju-demo-001';

export default function Passport() {
  const { userId } = useParams<{ userId: string }>();
  const authUserId = localStorage.getItem('arthai_user_id');
  const token = localStorage.getItem('arthai_token');
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [status, setStatus] = useState<'idle' | 'generating' | 'done' | 'error'>('idle');
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [passportData, setPassportData] = useState<{
    arthascore: number;
    loan_eligible: number;
    expires_at: string;
  } | null>(null);

  if (!token) {
    return <Navigate to="/demo" replace />;
  }

  const uid = userId || authUserId || DEMO_USER_ID;
  if (uid !== authUserId) {
    return <Navigate to="/demo" replace />;
  }

  const handleGenerate = async () => {
    setStatus('generating');
    try {
      const res = await apiClient.generatePassport(uid);
      setDownloadUrl(res.data.download_url);
      setPassportData({
        arthascore: res.data.arthascore,
        loan_eligible: res.data.loan_eligible,
        expires_at: res.data.expires_at,
      });
      setStatus('done');
    } catch (err) {
      console.error('Failed to generate passport:', err);
      setStatus('error');
    }
  };

  return (
    <div className="pass-page">
      <header className="dash-header">
        <div className="dash-brand">
          <Link to={`/dashboard/${uid}`} className="back-link">
            ← <span className="brand-name">Arth<span>AI</span> Passport</span>
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

      <div className="pass-container">
        <div className="pass-card">
          <div className="pass-header-info">
            <div className="pass-icon">📄</div>
            <h1 className="pass-title">{t('Financial Passport', 'वित्तीय पासपोर्ट')}</h1>
            <p className="pass-subtitle">
              {t('Bank-grade document for loan applications', 'ऋण आवेदनों के लिए बैंक-ग्रेड दस्तावेज')}
            </p>
          </div>

          <div className="pass-content">
            <h3 className="pass-section-title">
              {t("What's included in the document:", 'दस्तावेज में क्या शामिल होगा:')}
            </h3>
            <div className="pass-items">
              {[
                { icon: '📊', name: t('12-month P&L Statement', '12 महीने का पी एंड एल विवरण') },
                { icon: '🎯', name: t('ArthScore™ with full breakdown', 'पूर्ण विश्लेषण के साथ ArthScore™') },
                { icon: '📝', name: t('AI-generated business narrative', 'AI-जनरेटेड व्यावसायिक विवरण') },
                { icon: '💰', name: t('Estimated loan eligibility certificate', 'अनुमानित ऋण पात्रता प्रमाण पत्र') },
                { icon: '🏦', name: t('RBI-compliant digital verification format', 'RBI-अनुपालन डिजिटल सत्यापन प्रारूप') },
              ].map((item, idx) => (
                <div key={idx} className="pass-item">
                  <span className="pass-item-icon">{item.icon}</span>
                  <span className="pass-item-text">{item.name}</span>
                  <span className="pass-item-check">✓</span>
                </div>
              ))}
            </div>

            {status === 'idle' && (
              <button onClick={handleGenerate} className="pass-btn-primary">
                🚀 {t('Generate Financial Passport', 'वित्तीय पासपोर्ट बनाएं')}
              </button>
            )}

            {status === 'generating' && (
              <div className="pass-generating">
                <div className="pass-spinner"></div>
                <p>{t('Generating your passport...', 'आपका पासपोर्ट बन रहा है...')}</p>
                <span>{t('AI is structuring your statement', 'AI आपका स्टेटमेंट तैयार कर रहा है')}</span>
              </div>
            )}

            {status === 'done' && passportData && (
              <div className="pass-success-box">
                <div className="pass-result-grid">
                  <div className="pass-result-item">
                    <span className="pass-res-label">ArthScore™</span>
                    <span className="pass-res-val score">{passportData.arthascore}/900</span>
                  </div>
                  <div className="pass-result-item">
                    <span className="pass-res-label">{t('Loan Eligible', 'ऋण पात्रता')}</span>
                    <span className="pass-res-val loan">₹{passportData.loan_eligible.toLocaleString('en-IN')}</span>
                  </div>
                </div>

                <a href={downloadUrl || '#'} target="_blank" rel="noopener noreferrer" className="pass-btn-download">
                  📥 {t('Download PDF Passport', 'पीडीएफ पासपोर्ट डाउनलोड करें')}
                </a>

                <p className="pass-expiry">
                  {t('Valid until:', 'सत्यापन अवधि:')} {new Date(passportData.expires_at).toLocaleDateString('en-IN')}
                </p>
              </div>
            )}

            {status === 'error' && (
              <div className="pass-error-box">
                <p>{t('Something went wrong. Please try again.', 'कुछ गलत हुआ। कृपया दोबारा प्रयास करें।')}</p>
                <button onClick={() => setStatus('idle')} className="pass-btn-retry">
                  {t('Retry', 'पुनः प्रयास करें')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
