import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './contexts/LanguageContext';
import Dashboard from './pages/Dashboard';
import Demo from './pages/Demo';
import Transactions from './pages/Transactions';
import Passport from './pages/Passport';

function App() {
  const DEMO_USER_ID = 'raju-demo-001';
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to={`/dashboard/${DEMO_USER_ID}`} replace />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/:userId" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/transactions/:userId" element={<Transactions />} />
          <Route path="/passport" element={<Passport />} />
          <Route path="/passport/:userId" element={<Passport />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  );
}

export default App;
