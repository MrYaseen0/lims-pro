import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pathologistAPI } from '../lib/api';
import { formatDateTime, getStatusColor, getPriorityColor, formatStatus } from '../lib/utils';
import {
  Loader2,
  FileCheck,
  User,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';

export default function PathologistQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedTest, setSelectedTest] = useState(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    try {
      const response = await pathologistAPI.getQueue();
      setQueue(response.data);
    } catch (error) {
      toast.error('Failed to fetch review queue');
    } finally {
      setLoading(false);
    }
  };

  const openReviewDialog = (order, test) => {
    setSelectedOrder(order);
    setSelectedTest(test);
    setNotes('');
    setReviewDialogOpen(true);
  };

  const handleApprove = async (approved) => {
    setSaving(true);
    try {
      await pathologistAPI.approve({
        order_id: selectedOrder.id,
        test_id: selectedTest.test_id,
        approved,
        pathologist_notes: notes,
      });

      toast.success(approved ? 'Result approved' : 'Result rejected');
      setReviewDialogOpen(false);
      fetchQueue();
    } catch (error) {
      toast.error('Failed to process review');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="pathologist-queue">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Review Queue</h1>
          <p className="text-slate-500">Approve or reject test results</p>
        </div>
        <Badge variant="outline" className="text-violet-600 border-violet-200">
          {queue.length} order(s) pending review
        </Badge>
      </div>

      {/* Queue */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : queue.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileCheck className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No pending reviews</h3>
            <p className="text-slate-500 mt-1">All results have been reviewed!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {queue.map((order) => (
            <Card key={order.id} className="border border-slate-200" data-testid={`review-order-${order.id}`}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <code className="text-sm font-mono text-indigo-600 bg-indigo-50 px-2 py-1 rounded">
                      {order.order_id}
                    </code>
                    <Badge className={getPriorityColor(order.priority)}>
                      {order.priority.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Clock className="w-4 h-4" />
                    {formatDateTime(order.created_at)}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Patient Info */}
                {order.patient && (
                  <div className="flex items-center gap-3 mb-4 p-3 bg-slate-50 rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-violet-100 flex items-center justify-center">
                      <User className="w-5 h-5 text-violet-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{order.patient.name}</p>
                      <p className="text-sm text-slate-500">
                        {order.patient.age} yrs, {order.patient.gender}
                      </p>
                    </div>
                  </div>
                )}

                {/* Tests to Review */}
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 mb-2">Results to Review:</p>
                  {order.tests?.filter(t => t.result && t.status !== 'approved').map((test) => (
                    <div 
                      key={test.test_id} 
                      className="flex items-center justify-between p-4 border border-slate-200 rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-slate-900">{test.test_name}</p>
                          {test.result?.is_abnormal && (
                            <Badge className="bg-rose-100 text-rose-700">
                              <AlertCircle className="w-3 h-3 mr-1" />
                              Abnormal
                            </Badge>
                          )}
                        </div>
                        <code className="text-xs text-slate-500">{test.test_code}</code>
                        
                        {/* Result Values */}
                        {test.result && (
                          <div className="mt-2 p-2 bg-slate-50 rounded text-sm">
                            <p className="font-medium">
                              Result: {test.result.values?.value} {test.result.values?.unit}
                            </p>
                            {test.result.technician_notes && (
                              <p className="text-slate-500 mt-1">
                                Tech Notes: {test.result.technician_notes}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="ml-4">
                        <Button
                          size="sm"
                          onClick={() => openReviewDialog(order, test)}
                          className="bg-violet-600 hover:bg-violet-700"
                          data-testid={`review-test-${test.test_id}`}
                        >
                          Review
                        </Button>
                      </div>
                    </div>
                  ))}

                  {/* Already approved tests */}
                  {order.tests?.filter(t => t.status === 'approved').map((test) => (
                    <div 
                      key={test.test_id} 
                      className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-slate-900">{test.test_name}</p>
                        <code className="text-xs text-slate-500">{test.test_code}</code>
                      </div>
                      <Badge className="bg-emerald-100 text-emerald-700">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Approved
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Dialog */}
      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Review Test Result</DialogTitle>
          </DialogHeader>
          {selectedTest && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium text-slate-900">{selectedTest.test_name}</p>
                <code className="text-xs text-slate-500">{selectedTest.test_code}</code>
              </div>

              {/* Result Display */}
              {selectedTest.result && (
                <div className="p-4 border border-slate-200 rounded-lg">
                  <p className="text-sm text-slate-500 mb-1">Result Value</p>
                  <p className="text-2xl font-bold text-slate-900 font-heading">
                    {selectedTest.result.values?.value} 
                    <span className="text-base font-normal text-slate-500 ml-1">
                      {selectedTest.result.values?.unit}
                    </span>
                  </p>
                  {selectedTest.result.is_abnormal && (
                    <Badge className="bg-rose-100 text-rose-700 mt-2">
                      <AlertCircle className="w-3 h-3 mr-1" />
                      Marked as Abnormal
                    </Badge>
                  )}
                  {selectedTest.result.technician_notes && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <p className="text-sm text-slate-500">Technician Notes:</p>
                      <p className="text-sm text-slate-700">{selectedTest.result.technician_notes}</p>
                    </div>
                  )}
                </div>
              )}

              <div>
                <Label htmlFor="notes">Pathologist Notes</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add your review comments..."
                  className="mt-1.5"
                  rows={3}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <Button 
                  variant="outline"
                  className="flex-1 border-rose-200 text-rose-600 hover:bg-rose-50"
                  onClick={() => handleApprove(false)}
                  disabled={saving}
                  data-testid="reject-result-btn"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
                  Reject
                </Button>
                <Button 
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => handleApprove(true)}
                  disabled={saving}
                  data-testid="approve-result-btn"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                  Approve
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
