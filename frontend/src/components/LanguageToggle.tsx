import { useLanguage } from '../contexts/LanguageContext';
import './LanguageToggle.css';

export default function LanguageToggle() {
  const { lang, toggleLang } = useLanguage();
  return (
    <button className="lang-toggle" onClick={toggleLang} title="Switch Language">
      <span className={`lang-opt ${lang === 'en' ? 'active' : ''}`}>EN</span>
      <span className={`lang-opt ${lang === 'hi' ? 'active' : ''}`}>हिंदी</span>
    </button>
  );
}
