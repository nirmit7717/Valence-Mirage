import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../AppRouter';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/profile', label: 'Profile' },
  { to: '/about', label: 'About' },
];

export default function Navbar() {
  const { username, logout } = useAuth();
  const location = useLocation();

  return (
    <nav className="vm-navbar">
      <div className="vm-navbar-inner">
        <NavLink to="/dashboard" className="vm-navbar-logo">🎲 VM</NavLink>
        <div className="vm-navbar-links">
          {username ? (
            <>
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `vm-nav-link ${isActive ? 'vm-nav-active' : ''}`}
                >
                  {item.label}
                </NavLink>
              ))}
              <div className="vm-nav-separator" />
              <span className="vm-nav-user">{username}</span>
              <button className="vm-nav-logout" onClick={logout}>Logout</button>
            </>
          ) : (
            <>
              <NavLink to="/about" className={({ isActive }) => `vm-nav-link ${isActive ? 'vm-nav-active' : ''}`}>About</NavLink>
              <NavLink to="/login" className={({ isActive }) => `vm-nav-link ${isActive ? 'vm-nav-active' : ''}`}>Sign In</NavLink>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
