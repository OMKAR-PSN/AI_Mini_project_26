import { useEffect, useState } from 'react';
import { Satellite, LayoutDashboard, FlaskConical, Network, Moon, Sun } from 'lucide-react';
interface NavBarProps { currentPage: string; onNavigate: (page: string) => void; }
export default function NavBar({ currentPage, onNavigate }: NavBarProps) {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme || 'light');
  useEffect(() => {
    const media = matchMedia('(prefers-color-scheme: dark)');
    const change = () => {
      let saved; try { saved = localStorage.getItem('satquery_theme'); } catch { /* unavailable storage */ }
      if (saved !== 'light' && saved !== 'dark') { const next = media.matches ? 'dark' : 'light'; document.documentElement.dataset.theme = next; setTheme(next); }
    };
    media.addEventListener('change', change); return () => media.removeEventListener('change', change);
  }, []);
  const toggle = () => { const next = theme === 'dark' ? 'light' : 'dark'; setTheme(next); document.documentElement.dataset.theme = next; try { localStorage.setItem('satquery_theme', next); } catch {/* session-only theme */ } };
  return <><a className="skip-link" href="#main-content">Skip to content</a><header className="app-nav">
    <button className="brand" onClick={() => onNavigate('home')} aria-label="SatQuery AI home"><Satellite size={26} /><span>SatQuery AI<small>Earth observation workspace</small></span></button>
    <nav className="nav-pages" aria-label="Primary navigation">{[{ id: 'home', label: 'Home', icon: LayoutDashboard }, { id: 'analysis', label: 'Analysis', icon: FlaskConical }, { id: 'system', label: 'System View', icon: Network }].map(({ id, label, icon: Icon }) => <button key={id} onClick={() => onNavigate(id)} aria-current={currentPage === id ? 'page' : undefined}><Icon size={15} />{label}</button>)}</nav>
    <button className="btn-ghost" onClick={toggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}</button>
  </header></>;
}
