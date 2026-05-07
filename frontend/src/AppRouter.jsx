import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState, createContext, useContext } from 'react';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import GamePage from './pages/GamePage';
import AboutPage from './pages/AboutPage';
import ProfilePage from './pages/ProfilePage';
import CampaignHistoryPage from './pages/CampaignHistoryPage';
import CampaignDetailPage from './pages/CampaignDetailPage';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

// Minimal auth context — token + user info
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

// Pages where navbar should be hidden
const NO_NAVBAR_ROUTES = ['/', '/login'];
const NO_NAVBAR_PREFIXES = ['/campaign/', '/new'];

function shouldHideNavbar(pathname) {
  if (NO_NAVBAR_ROUTES.includes(pathname)) return true;
  if (pathname === '/new') return true;
  if (pathname.startsWith('/campaign/')) return true;
  return false;
}

function AppShell() {
  const location = useLocation();
  const hideNav = shouldHideNavbar(location.pathname);

  return (
    <div className="app-shell">
      {!hideNav && <Navbar />}
      <main className={hideNav ? 'app-main-fullscreen' : 'app-main'}>
        <div className="page-fade" key={location.pathname}>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/new" element={<ProtectedRoute><GamePage /></ProtectedRoute>} />
            <Route path="/campaign/:id" element={<GamePage />} />
            <Route path="/campaign/:id/history" element={<ProtectedRoute><CampaignDetailPage /></ProtectedRoute>} />
            <Route path="/campaigns" element={<ProtectedRoute><CampaignHistoryPage /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function AppRouter() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    return token ? { token, username } : null;
  });

  const login = (token, username) => {
    localStorage.setItem('token', token);
    localStorage.setItem('username', username);
    setAuth({ token, username });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setAuth(null);
  };

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      <BrowserRouter basename="/static">
        <AppShell />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
