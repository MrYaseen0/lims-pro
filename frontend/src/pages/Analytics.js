import { useState, useEffect } from 'react';
import { analyticsAPI } from '../lib/api';
import { formatCurrency } from '../lib/utils';
import {
  Loader2,
  TrendingUp,
  Users,
  TestTube,
  ClipboardList,
  DollarSign,
  Calendar,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
  AreaChart,
  Area,
} from 'recharts';

const COLORS = ['#4F46E5', '#7C3AED', '#059669', '#D97706', '#E11D48', '#0EA5E9'];

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await analyticsAPI.getDashboard();
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
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

  const summaryCards = [
    { title: 'Monthly Revenue', value: formatCurrency(data?.month_revenue || 0), icon: DollarSign, color: 'text-emerald-600', bgColor: 'bg-emerald-100' },
    { title: "Today's Revenue", value: formatCurrency(data?.today_revenue || 0), icon: TrendingUp, color: 'text-indigo-600', bgColor: 'bg-indigo-100' },
    { title: 'Total Patients', value: data?.total_patients || 0, icon: Users, color: 'text-violet-600', bgColor: 'bg-violet-100' },
    { title: 'Active Tests', value: data?.total_tests || 0, icon: TestTube, color: 'text-amber-600', bgColor: 'bg-amber-100' },
  ];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="analytics-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Analytics</h1>
          <p className="text-slate-500">Monitor lab performance and revenue</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card, index) => (
          <Card key={index} className="border border-slate-200" data-testid={`analytics-card-${index}`}>
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${card.bgColor} flex items-center justify-center`}>
                  <card.icon className={`w-5 h-5 ${card.color}`} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">{card.title}</p>
                  <p className="text-xl font-bold text-slate-900 font-heading">{card.value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Trend */}
        <Card className="border border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold font-heading flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              Revenue Trend (Last 7 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data?.daily_revenue || []}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#4F46E5" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
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
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#4F46E5" 
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRevenue)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Test Volume by Category */}
        <Card className="border border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold font-heading flex items-center gap-2">
              <TestTube className="w-5 h-5 text-indigo-600" />
              Tests by Category
            </CardTitle>
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
                      outerRadius={100}
                      innerRadius={50}
                      label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                    >
                      {data.test_volumes.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400">
                  No data available
                </div>
              )}
            </div>
            {/* Legend */}
            {data?.test_volumes && data.test_volumes.length > 0 && (
              <div className="flex flex-wrap gap-3 justify-center mt-4">
                {data.test_volumes.map((entry, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-slate-600">{entry.category}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Work Summary */}
      <Card className="border border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold font-heading flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-indigo-600" />
            Current Work Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Pending Samples</p>
              <p className="text-3xl font-bold text-slate-900 font-heading mt-1">
                {data?.pending_samples || 0}
              </p>
              <p className="text-xs text-slate-400 mt-1">Awaiting collection</p>
            </div>
            <div className="p-4 bg-amber-50 rounded-lg">
              <p className="text-sm text-amber-700">Pending Results</p>
              <p className="text-3xl font-bold text-amber-700 font-heading mt-1">
                {data?.pending_results || 0}
              </p>
              <p className="text-xs text-amber-600 mt-1">In lab processing</p>
            </div>
            <div className="p-4 bg-violet-50 rounded-lg">
              <p className="text-sm text-violet-700">Awaiting Approval</p>
              <p className="text-3xl font-bold text-violet-700 font-heading mt-1">
                {data?.pending_approval || 0}
              </p>
              <p className="text-xs text-violet-600 mt-1">Need pathologist review</p>
            </div>
            <div className="p-4 bg-emerald-50 rounded-lg">
              <p className="text-sm text-emerald-700">Today's Orders</p>
              <p className="text-3xl font-bold text-emerald-700 font-heading mt-1">
                {data?.today_orders || 0}
              </p>
              <p className="text-xs text-emerald-600 mt-1">New orders today</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
