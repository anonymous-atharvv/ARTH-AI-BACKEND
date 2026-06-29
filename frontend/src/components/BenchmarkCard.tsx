// frontend/src/components/BenchmarkCard.tsx
import { useLanguage } from '../contexts/LanguageContext';

interface BenchmarkData {
  available: boolean;
  percentile_vs_peers?: number;
  peer_count?: number;
  business_type?: string;
  insight_en?: string;
  insight_hi?: string;
}

export default function BenchmarkCard({ data }: { data: BenchmarkData }) {
  const { lang, t } = useLanguage();

  if (!data || !data.available) return null;

  const pct = data.percentile_vs_peers || 0;
  const isAbove = pct >= 0;
  const color = isAbove ? '#4ade80' : '#f87171';

  return (
    <div style={{
      background: `linear-gradient(135deg, ${isAbove ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)'} 0%, rgba(15,23,42,0.8) 100%)`,
      border: `1px solid ${isAbove ? 'rgba(74,222,128,0.3)' : 'rgba(248,113,113,0.3)'}`,
      borderRadius: '16px', padding: '20px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '28px' }}>{isAbove ? '🏆' : '📊'}</span>
        <div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {t(
              `VS ${data.peer_count} SIMILAR BUSINESSES (${data.business_type})`,
              `${data.peer_count} समान व्यवसायों के मुकाबले (${data.business_type})`
            )}
          </div>
          <div style={{ fontSize: '22px', fontWeight: 800, color }}>
            {isAbove ? '+' : ''}{pct.toFixed(0)}%
          </div>
          <p style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '4px', lineHeight: 1.5 }}>
            {lang === 'hi' ? data.insight_hi : data.insight_en}
          </p>
        </div>
      </div>
    </div>
  );
}
