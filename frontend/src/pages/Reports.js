import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { orderAPI } from '../lib/api';
import { formatDateTime, getStatusColor, formatStatus, formatCurrency } from '../lib/utils';
import {
  Loader2,
  FileText,
  Download,
  ChevronRight,
  Send,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

export default function Reports() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      // Get orders that are approved or report_released
      const [approvedRes, releasedRes] = await Promise.all([
        orderAPI.getAll({ status: 'approved' }),
        orderAPI.getAll({ status: 'report_released' }),
      ]);
      setOrders([...approvedRes.data, ...releasedRes.data]);
    } catch (error) {
      toast.error('Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="reports-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Reports</h1>
          <p className="text-slate-500">View and manage lab reports</p>
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : orders.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No reports available</h3>
            <p className="text-slate-500 mt-1">Reports will appear here once orders are approved</p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Order ID</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Patient</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Tests</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr 
                    key={order.id} 
                    className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors"
                    data-testid={`report-row-${order.id}`}
                  >
                    <td className="px-4 py-3">
                      <code className="text-sm font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                        {order.order_id}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{order.patient_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-600">{order.tests?.length || 0} test(s)</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={getStatusColor(order.status)}>
                        {formatStatus(order.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDateTime(order.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          asChild
                        >
                          <Link to={`/orders/${order.id}`} data-testid={`view-report-${order.id}`}>
                            View
                          </Link>
                        </Button>
                        {order.status === 'report_released' && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            data-testid={`download-report-${order.id}`}
                          >
                            <Download className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
