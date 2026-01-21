import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  TestTube,
  ClipboardList,
  Droplets,
  FlaskConical,
  FileCheck,
  FileText,
  CreditCard,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react';
import { Button } from './ui/button';
import { Avatar, AvatarFallback } from './ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { getInitials } from '../lib/utils';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'lab_manager', 'technician', 'pathologist', 'receptionist'] },
  { path: '/patients', label: 'Patients', icon: Users, roles: ['admin', 'lab_manager', 'receptionist'] },
  { path: '/tests', label: 'Test Catalog', icon: TestTube, roles: ['admin', 'lab_manager'] },
  { path: '/orders', label: 'Orders', icon: ClipboardList, roles: ['admin', 'lab_manager', 'receptionist', 'technician', 'pathologist'] },
  { path: '/samples', label: 'Samples', icon: Droplets, roles: ['admin', 'lab_manager', 'technician', 'collection_staff'] },
  { path: '/technician', label: 'Lab Queue', icon: FlaskConical, roles: ['admin', 'lab_manager', 'technician'] },
  { path: '/pathologist', label: 'Review Queue', icon: FileCheck, roles: ['admin', 'lab_manager', 'pathologist'] },
  { path: '/reports', label: 'Reports', icon: FileText, roles: ['admin', 'lab_manager', 'pathologist'] },
  { path: '/billing', label: 'Billing', icon: CreditCard, roles: ['admin', 'lab_manager', 'receptionist'] },
  { path: '/analytics', label: 'Analytics', icon: BarChart3, roles: ['admin', 'lab_manager'] },
  { path: '/settings', label: 'Settings', icon: Settings, roles: ['admin'] },
];

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredNavItems = navItems.filter(item => 
    item.roles.includes(user?.role)
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-slate-900 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <TestTube className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white font-heading">LIMS.Pro</span>
          </Link>
          <button 
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setMobileMenuOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {filteredNavItems.map((item) => {
            const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
                data-testid={`nav-${item.path.slice(1)}`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 px-2">
            <Avatar className="w-9 h-9 bg-indigo-600">
              <AvatarFallback className="bg-indigo-600 text-white text-sm">
                {getInitials(user?.name)}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.name}</p>
              <p className="text-xs text-slate-400 truncate capitalize">{user?.role?.replace('_', ' ')}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className={`lg:ml-64 min-h-screen`}>
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 bg-white/80 backdrop-blur-md border-b border-slate-200/50 flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-4">
            <button 
              className="lg:hidden p-2 hover:bg-slate-100 rounded-lg"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="w-5 h-5 text-slate-600" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2" data-testid="user-menu-trigger">
                  <Avatar className="w-8 h-8 bg-indigo-600">
                    <AvatarFallback className="bg-indigo-600 text-white text-xs">
                      {getInitials(user?.name)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline text-sm font-medium">{user?.name}</span>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user?.name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-rose-600" data-testid="logout-btn">
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
