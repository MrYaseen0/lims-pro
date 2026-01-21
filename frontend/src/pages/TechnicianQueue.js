import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { resultAPI, orderAPI } from '../lib/api';
import { formatDateTime, getStatusColor, getPriorityColor, formatStatus } from '../lib/utils';
import {
  Loader2,
  FlaskConical,
  AlertCircle,
  CheckCircle,
  User,
  Clock,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';

export default function TechnicianQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedTest, setSelectedTest] = useState(null);
  const [resultDialogOpen, setResultDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resultForm, setResultForm] = useState({
    value: '',
    unit: '',
    is_abnormal: false,
    technician_notes: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    try {
      const response = await resultAPI.getTechnicianQueue();
      setQueue(response.data);
    } catch (error) {
      toast.error('Failed to fetch queue');
    } finally {
      setLoading(false);
    }
  };

  const openResultDialog = (order, test) => {
    setSelectedOrder(order);
    setSelectedTest(test);
    setResultForm({
      value: '',
      unit: '',
      is_abnormal: false,
      technician_notes: '',
    });
    setResultDialogOpen(true);
  };

  const handleSubmitResult = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await resultAPI.enter({
        order_id: selectedOrder.id,
        test_id: selectedTest.test_id,
        values: {
          value: resultForm.value,
          unit: resultForm.unit,
        },
        is_abnormal: resultForm.is_abnormal,
        technician_notes: resultForm.technician_notes,
      });

      toast.success('Result submitted successfully');
      setResultDialogOpen(false);
      fetchQueue();
    } catch (error) {
      toast.error('Failed to submit result');
    } finally {
      setSaving(false);
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      await orderAPI.updateStatus(orderId, status);
      toast.success('Order status updated');
      fetchQueue();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="technician-queue">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Lab Work Queue</h1>
          <p className="text-slate-500">Enter test results for pending orders</p>
        </div>
        <Badge variant="outline" className="text-indigo-600 border-indigo-200">
          {queue.length} order(s) pending
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
            <FlaskConical className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No pending work</h3>
            <p className="text-slate-500 mt-1">All tests have been processed!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {queue.map((order) => (
            <Card key={order.id} className="border border-slate-200" data-testid={`queue-order-${order.id}`}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <code className="text-sm font-mono text-indigo-600 bg-indigo-50 px-2 py-1 rounded">
                      {order.order_id}
                    </code>
                    <Badge className={getPriorityColor(order.priority)}>
                      {order.priority.toUpperCase()}
                    </Badge>
                    <Badge className={getStatusColor(order.status)}>
                      {formatStatus(order.status)}
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
                    <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                      <User className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{order.patient.name}</p>
                      <p className="text-sm text-slate-500">
                        {order.patient.age} yrs, {order.patient.gender}
                      </p>
                    </div>
                  </div>
                )}

                {/* Tests */}
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 mb-2">Tests to Process:</p>
                  {order.tests?.map((test) => (
                    <div 
                      key={test.test_id} 
                      className="flex items-center justify-between p-3 border border-slate-200 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-slate-900">{test.test_name}</p>
                        <code className="text-xs text-slate-500">{test.test_code}</code>
                      </div>
                      <div className="flex items-center gap-2">
                        {test.status === 'completed' || test.result ? (
                          <Badge className="bg-emerald-100 text-emerald-700">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Result Entered
                          </Badge>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => openResultDialog(order, test)}
                            className="bg-indigo-600 hover:bg-indigo-700"
                            data-testid={`enter-result-${test.test_id}`}
                          >
                            Enter Result
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                {order.status === 'sample_collected' && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <Button
                      variant="outline"
                      onClick={() => updateOrderStatus(order.id, 'in_lab')}
                    >
                      Mark as In Lab
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Result Entry Dialog */}
      <Dialog open={resultDialogOpen} onOpenChange={setResultDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Enter Test Result</DialogTitle>
          </DialogHeader>
          {selectedTest && (
            <form onSubmit={handleSubmitResult} className="space-y-4 mt-4">
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium text-slate-900">{selectedTest.test_name}</p>
                <code className="text-xs text-slate-500">{selectedTest.test_code}</code>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="value">Result Value *</Label>
                  <Input
                    id="value"
                    value={resultForm.value}
                    onChange={(e) => setResultForm(prev => ({ ...prev, value: e.target.value }))}
                    required
                    className="mt-1.5"
                    data-testid="result-value-input"
                  />
                </div>
                <div>
                  <Label htmlFor="unit">Unit</Label>
                  <Input
                    id="unit"
                    value={resultForm.unit}
                    onChange={(e) => setResultForm(prev => ({ ...prev, unit: e.target.value }))}
                    placeholder="e.g., mg/dL"
                    className="mt-1.5"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="abnormal"
                  checked={resultForm.is_abnormal}
                  onCheckedChange={(checked) => setResultForm(prev => ({ ...prev, is_abnormal: checked }))}
                  data-testid="abnormal-checkbox"
                />
                <Label htmlFor="abnormal" className="flex items-center gap-2 cursor-pointer">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  Mark as Abnormal
                </Label>
              </div>

              <div>
                <Label htmlFor="notes">Technician Notes</Label>
                <Textarea
                  id="notes"
                  value={resultForm.technician_notes}
                  onChange={(e) => setResultForm(prev => ({ ...prev, technician_notes: e.target.value }))}
                  placeholder="Any observations or notes..."
                  className="mt-1.5"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setResultDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={saving}
                  data-testid="submit-result-btn"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Submit Result'
                  )}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
