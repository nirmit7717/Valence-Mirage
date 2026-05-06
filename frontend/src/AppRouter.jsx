import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, createContext, useContext } from 'react';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import GamePage from './pages/GamePage';
import AboutPage from './pages/AboutPage';
import ProfilePage from './pages/ProfilePage';
import CampaignHistoryPage from './pages/CampaignHistoryPage';
import CampaignDetailPage from './pages/CampaignDetailPage';
import Navbar from './components/Navbar';

// Minimal auth context — just token + user info
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

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
        <Navbar />
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/new" element={<GamePage />} />                     {/* No ID → ConnectOverlay */}
          <Route path="/campaign/:id" element={<GamePage />} />            {/* With ID → hydrate */}
          <Route path="/campaign/:id/history" element={<CampaignDetailPage />} />
          <Route path="/campaigns" element={<CampaignHistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
