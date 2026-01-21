import { useState, useEffect } from 'react';
import { sampleAPI, orderAPI } from '../lib/api';
import { formatDateTime, getStatusColor, formatStatus } from '../lib/utils';
import {
  Search,
  Loader2,
  Droplets,
  Filter,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';

const SAMPLE_STATUSES = [
  { value: 'all', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'collected', label: 'Collected' },
  { value: 'received', label: 'Received' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'rejected', label: 'Rejected' },
];

export default function Samples() {
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    fetchSamples();
  }, [statusFilter]);

  const fetchSamples = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      const response = await sampleAPI.getAll(params);
      setSamples(response.data);
    } catch (error) {
      toast.error('Failed to fetch samples');
    } finally {
      setLoading(false);
    }
  };

  const updateSampleStatus = async (sampleId, newStatus) => {
    setUpdatingId(sampleId);
    try {
      await sampleAPI.updateStatus(sampleId, newStatus);
      toast.success(`Sample status updated to ${formatStatus(newStatus)}`);
      fetchSamples();
    } catch (error) {
      toast.error('Failed to update sample status');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="samples-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Sample Management</h1>
          <p className="text-slate-500">Track and manage laboratory samples</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="sample-status-filter">
            <Filter className="w-4 h-4 mr-2 text-slate-400" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {SAMPLE_STATUSES.map((status) => (
              <SelectItem key={status.value} value={status.value}>
                {status.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Samples List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : samples.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Droplets className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No samples found</h3>
            <p className="text-slate-500 mt-1">
              {statusFilter ? 'Try different filters' : 'Samples will appear here when orders are processed'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Sample ID</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Order</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Patient</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Barcode</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Collected</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {samples.map((sample) => (
                  <tr 
                    key={sample.id} 
                    className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors"
                    data-testid={`sample-row-${sample.id}`}
                  >
                    <td className="px-4 py-3">
                      <code className="text-sm font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                        {sample.sample_id}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-sm font-mono text-slate-600">{sample.order_number}</code>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {sample.patient_name || '-'}
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-600">
                      {sample.sample_type}
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">
                        {sample.barcode}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={getStatusColor(sample.status)}>
                        {formatStatus(sample.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {sample.collection_time ? formatDateTime(sample.collection_time) : '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {sample.status === 'collected' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => updateSampleStatus(sample.id, 'received')}
                            disabled={updatingId === sample.id}
                            data-testid={`receive-sample-${sample.id}`}
                          >
                            {updatingId === sample.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <>
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Receive
                              </>
                            )}
                          </Button>
                        )}
                        {sample.status === 'received' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => updateSampleStatus(sample.id, 'processing')}
                            disabled={updatingId === sample.id}
                          >
                            {updatingId === sample.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              'Start Processing'
                            )}
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
