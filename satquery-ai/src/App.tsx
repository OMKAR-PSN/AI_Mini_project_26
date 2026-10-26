// SatQuery AI — Root Application

import { useState } from 'react';
import NavBar from './components/layout/NavBar';
import HomePage from './pages/HomePage';
import AnalysisPage from './pages/AnalysisPage';
import SystemViewPage from './pages/SystemViewPage';

type Page = 'home' | 'analysis' | 'system';

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [demoScenario, setDemoScenario] = useState<string | null>(null);

  const handleStartDemo = (scenarioId: string) => {
    setDemoScenario(scenarioId);
    setPage('analysis');
  };

  const handleNavigate = (p: string) => {
    setPage(p as Page);
    if (p !== 'analysis') setDemoScenario(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar currentPage={page} onNavigate={handleNavigate} />

      <main id="main-content" className="flex-1" tabIndex={-1}>
        {page === 'home' && (
          <div key="home" className="animate-fade-in">
            <HomePage onNavigate={handleNavigate} onStartDemo={handleStartDemo} />
          </div>
        )}
        {page === 'analysis' && (
          <div key="analysis" className="animate-fade-in">
            <AnalysisPage
              initialScenario={demoScenario}
              key={demoScenario ?? 'analysis'}
            />
          </div>
        )}
        {page === 'system' && (
          <div key="system" className="animate-fade-in">
            <SystemViewPage />
          </div>
        )}
      </main>
    </div>
  );
}
