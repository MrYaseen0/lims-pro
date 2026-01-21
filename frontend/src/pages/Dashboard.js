import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { analyticsAPI } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { formatCurrency } from '../lib/utils';
import {
  Users,
  ClipboardList,
  Droplets,
  FileCheck,
  TrendingUp,
  AlertCircle,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#4F46E5', '#7C3AED', '#059669', '#D97706', '#E11D48', '#0EA5E9'];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await analyticsAPI.getDashboard();
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  const statCards = [
    {
      title: "Today's Orders",
      value: data?.today_orders || 0,
      icon: ClipboardList,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      link: '/orders',
    },
    {
      title: "Today's Revenue",
      value: formatCurrency(data?.today_revenue || 0),
      icon: TrendingUp,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      link: '/billing',
    },
    {
      title: 'Pending Samples',
      value: data?.pending_samples || 0,
      icon: Droplets,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      link: '/samples',
    },
    {
      title: 'Awaiting Review',
      value: data?.pending_approval || 0,
      icon: FileCheck,
      color: 'text-violet-600',
      bgColor: 'bg-violet-50',
      link: '/pathologist',
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="dashboard">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Dashboard</h1>
          <p className="text-slate-500">Welcome back, {user?.name}</p>
        </div>
        <div className="flex gap-3">
          <Button asChild className="bg-indigo-600 hover:bg-indigo-700">
            <Link to="/orders/new" data-testid="new-order-btn">
              New Order
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => (
          <Link key={index} to={stat.link}>
            <Card className="border border-slate-200 hover:border-indigo-200 transition-colors cursor-pointer" data-testid={`stat-card-${index}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-slate-500">{stat.title}</p>
                    <p className="text-2xl font-bold text-slate-900 font-heading mt-1">{stat.value}</p>
                  </div>
                  <div className={`w-10 h-10 rounded-lg ${stat.bgColor} flex items-center justify-center`}>
                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Chart */}
        <Card className="lg:col-span-2 border border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold font-heading">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data?.daily_revenue || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { weekday: 'short' })}
                  />
                  <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
                  <Tooltip 
                    formatter={(value) => formatCurrency(value)}
                    labelFormatter={(label) => new Date(label).toLocaleDateString()}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#4F46E5" 
                    strokeWidth={2}
                    dot={{ fill: '#4F46E5', strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Test Volume Pie Chart */}
        <Card className="border border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold font-heading">Tests by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {data?.test_volumes && data.test_volumes.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.test_volumes}
                      dataKey="count"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: '#64748b' }}
                    >
                      {data.test_volumes.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <AlertCircle className="w-12 h-12 mb-2" />
                  <p>No test data available</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="border border-slate-200 hover:border-indigo-200 transition-colors">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Pending Results</h3>
                <p className="text-sm text-slate-500 mt-1">{data?.pending_results || 0} orders waiting</p>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/technician" className="text-indigo-600" data-testid="view-lab-queue">
                  View <ArrowRight className="w-4 h-4 ml-1" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-slate-200 hover:border-indigo-200 transition-colors">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Total Patients</h3>
                <p className="text-sm text-slate-500 mt-1">{data?.total_patients || 0} registered</p>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/patients" className="text-indigo-600" data-testid="view-patients">
                  View <ArrowRight className="w-4 h-4 ml-1" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-slate-200 hover:border-indigo-200 transition-colors">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Active Tests</h3>
                <p className="text-sm text-slate-500 mt-1">{data?.total_tests || 0} in catalog</p>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/tests" className="text-indigo-600" data-testid="view-tests">
                  View <ArrowRight className="w-4 h-4 ml-1" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      <Card className="border border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold font-heading">Monthly Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-slate-500">Total Revenue</p>
              <p className="text-xl font-bold text-slate-900 font-heading">
                {formatCurrency(data?.month_revenue || 0)}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500">New Patients</p>
              <p className="text-xl font-bold text-slate-900 font-heading">
                {data?.today_patients || 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Pending Samples</p>
              <p className="text-xl font-bold text-slate-900 font-heading">
                {data?.pending_samples || 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Awaiting Approval</p>
              <p className="text-xl font-bold text-slate-900 font-heading">
                {data?.pending_approval || 0}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
