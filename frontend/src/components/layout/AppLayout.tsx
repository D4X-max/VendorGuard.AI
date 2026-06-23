import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';
import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  LogOut,
  FileText,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '../../utils';

const navigation = [
  { name: 'Dashboard',        href: '/',         icon: LayoutDashboard },
  { name: 'Vendor Directory', href: '/vendors',  icon: Users           },
  { name: 'Risk Register',    href: '/risk',     icon: ShieldAlert     },
  { name: 'Evidence',         href: '/evidence', icon: FileText        },
];

export default function AppLayout() {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const currentPage = navigation.find(
    (n) =>
      location.pathname === n.href ||
      (n.href !== '/' && location.pathname.startsWith(n.href))
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">

      {/* ── Sidebar ─────────────────────────────────────── */}
      <div className="w-64 bg-slate-900 text-white flex flex-col fixed inset-y-0 z-10">

        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <ShieldCheck className="text-brand-500 mr-2 flex-shrink-0" size={24} />
          <span className="text-lg font-bold tracking-wide">VendorGuard</span>
          <span className="ml-1 text-brand-500 font-bold">.AI</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navigation.map((item) => {
            const isActive =
              location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )}
              >
                <item.icon
                  className={cn(
                    'mr-3 flex-shrink-0 h-5 w-5 transition-colors',
                    isActive
                      ? 'text-brand-500'
                      : 'text-slate-400 group-hover:text-brand-500'
                  )}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Footer */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-2 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors flex-shrink-0"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Main Content ─────────────────────────────────── */}
      <div className="pl-64 flex-1 flex flex-col min-h-screen">

        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-8 flex-shrink-0 sticky top-0 z-10">
          <h1 className="text-xl font-semibold text-gray-800">
            {currentPage?.name || 'Dashboard'}
          </h1>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>

      </div>
    </div>
  );
}