import { NavLink } from 'react-router-dom';
import { useAuth } from '../AppRouter';

export default function Navbar() {
  const { username, logout } = useAuth();

  return (
    <nav className="vm-navbar">
      <div className="vm-navbar-brand">
        <NavLink to="/" className="vm-navbar-logo">🎲 Valence Mirage</NavLink>
      </div>
      <div className="vm-navbar-links">
        {username ? (
          <>
            <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>Dashboard</NavLink>
            <NavLink to="/campaigns" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>Campaigns</NavLink>
            <NavLink to="/profile" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>Profile</NavLink>
            <NavLink to="/about" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>About</NavLink>
            <span className="vm-nav-user">{username}</span>
            <button className="vm-nav-logout" onClick={logout}>Logout</button>
          </>
        ) : (
          <>
            <NavLink to="/about" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>About</NavLink>
            <NavLink to="/login" className={({ isActive }) => isActive ? 'vm-nav-link active' : 'vm-nav-link'}>Sign In</NavLink>
          </>
        )}
      </div>
    </nav>
  );
}
