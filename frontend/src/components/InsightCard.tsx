import { useLanguage } from '../contexts/LanguageContext';
import './InsightCard.css';

interface InsightProps {
  type: 'expense_anomaly' | 'weekly_summary' | 'score_ready' | 'income_milestone';
  data: Record<string, any>;
  onDismiss?: () => void;
}

export default function InsightCard({ type, data, onDismiss }: InsightProps) {
  const { lang } = useLanguage();

  const messages: Record<typeof type, { hi: string; en: string }> = {
    expense_anomaly: {
      hi: `⚠️ Is mahine ${data.category} का खर्च ₹${data.current?.toLocaleString('en-IN')} रहा — average से ${data.spike_pct?.toFixed(0)}% ज़्यादा।`,
      en: `⚠️ This month's ${data.category} costs are ${data.spike_pct?.toFixed(0)}% above your average.`
    },
    weekly_summary: {
      hi: `📊 इस हफ्ते: आय ₹${data.income?.toLocaleString('en-IN')}, खर्च ₹${data.expenses?.toLocaleString('en-IN')}, मुनाफा ₹${data.net?.toLocaleString('en-IN')}`,
      en: `📊 This week: Income ₹${data.income?.toLocaleString('en-IN')}, Expenses ₹${data.expenses?.toLocaleString('en-IN')}, Net ₹${data.net?.toLocaleString('en-IN')}`
    },
    score_ready: {
      hi: `🏆 आपका ArthScore ready है: ${data.score}/900। ₹${data.loan?.toLocaleString('en-IN')} तक loan eligible!`,
      en: `🏆 Your ArthScore is ready: ${data.score}/900. Eligible for loans up to ₹${data.loan?.toLocaleString('en-IN')}!`
    },
    income_milestone: {
      hi: `🎉 बधाई हो! इस महीने ₹${data.milestone?.toLocaleString('en-IN')} की income cross कर ली!`,
      en: `🎉 Congratulations! You crossed ₹${data.milestone?.toLocaleString('en-IN')} in income this month!`
    }
  };

  const text = lang === 'hi' ? messages[type].hi : messages[type].en;

  return (
    <div className={`insight-card-comp ${type}`}>
      <span className="insight-card-text">{text}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="insight-card-close" aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}
