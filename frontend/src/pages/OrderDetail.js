import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { orderAPI, sampleAPI, reportAPI } from '../lib/api';
import { formatDateTime, getStatusColor, getPriorityColor, formatStatus, formatCurrency } from '../lib/utils';
import {
  ArrowLeft,
  Loader2,
  User,
  TestTube,
  Droplets,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Download,
  Send,
  FileDown,
  Eye,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';

const STATUS_STEPS = [
  { key: 'registered', label: 'Registered', icon: FileText },
  { key: 'sample_collected', label: 'Sample Collected', icon: Droplets },
  { key: 'in_lab', label: 'In Lab', icon: TestTube },
  { key: 'under_review', label: 'Under Review', icon: Clock },
  { key: 'approved', label: 'Approved', icon: CheckCircle },
  { key: 'report_released', label: 'Report Released', icon: Send },
];

export default function OrderDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collectingSample, setCollectingSample] = useState(false);
  const [releasingReport, setReleasingReport] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  useEffect(() => {
    fetchOrder();
  }, [id]);

  const fetchOrder = async () => {
    try {
      const response = await orderAPI.getById(id);
      setOrder(response.data);
    } catch (error) {
      toast.error('Failed to fetch order details');
      navigate('/orders');
    } finally {
      setLoading(false);
    }
  };

  const handleCollectSample = async () => {
    setCollectingSample(true);
    try {
      // Get unique sample types from tests
      const sampleTypes = [...new Set(order.tests.map(t => 'blood'))]; // Default to blood for now
      
      for (const sampleType of sampleTypes) {
        await sampleAPI.create({
          order_id: order.id,
          sample_type: sampleType,
        });
      }
      
      toast.success('Sample collected successfully');
      fetchOrder();
    } catch (error) {
      toast.error('Failed to collect sample');
    } finally {
      setCollectingSample(false);
    }
  };

  const handleReleaseReport = async () => {
    setReleasingReport(true);
    try {
      await reportAPI.release(order.id);
      toast.success('Report released successfully');
      fetchOrder();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to release report');
    } finally {
      setReleasingReport(false);
    }
  };

  const getCurrentStepIndex = () => {
    return STATUS_STEPS.findIndex(step => step.key === order?.status);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!order) return null;

  const currentStepIndex = getCurrentStepIndex();

  return (
    <div className="space-y-6 animate-fade-in" data-testid="order-detail">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/orders')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 font-heading">
                <code className="font-mono">{order.order_id}</code>
              </h1>
              <Badge className={getStatusColor(order.status)}>
                {formatStatus(order.status)}
              </Badge>
              <Badge className={getPriorityColor(order.priority)}>
                {order.priority.toUpperCase()}
              </Badge>
            </div>
            <p className="text-slate-500">Created {formatDateTime(order.created_at)}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {order.status === 'registered' && (
            <Button 
              onClick={handleCollectSample}
              disabled={collectingSample}
              className="bg-indigo-600 hover:bg-indigo-700"
              data-testid="collect-sample-btn"
            >
              {collectingSample ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Droplets className="w-4 h-4 mr-2" />}
              Collect Sample
            </Button>
          )}
          {order.status === 'approved' && (
            <Button 
              onClick={handleReleaseReport}
              disabled={releasingReport}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="release-report-btn"
            >
              {releasingReport ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Release Report
            </Button>
          )}
          {order.status === 'report_released' && (
            <Button variant="outline" data-testid="download-report-btn">
              <Download className="w-4 h-4 mr-2" />
              Download Report
            </Button>
          )}
        </div>
      </div>

      {/* Status Timeline */}
      <Card className="border border-slate-200">
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            {STATUS_STEPS.map((step, index) => {
              const isCompleted = index <= currentStepIndex;
              const isCurrent = index === currentStepIndex;
              const Icon = step.icon;
              
              return (
                <div key={step.key} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      isCompleted 
                        ? 'bg-indigo-600 text-white' 
                        : 'bg-slate-100 text-slate-400'
                    } ${isCurrent ? 'ring-4 ring-indigo-100' : ''}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-xs mt-2 ${isCompleted ? 'text-indigo-600 font-medium' : 'text-slate-400'}`}>
                      {step.label}
                    </span>
                  </div>
                  {index < STATUS_STEPS.length - 1 && (
                    <div className={`w-16 sm:w-24 h-0.5 mx-2 ${
                      index < currentStepIndex ? 'bg-indigo-600' : 'bg-slate-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Tests */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <TestTube className="w-4 h-4 text-indigo-600" />
                Tests ({order.tests?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {order.tests?.map((test, index) => (
                  <div 
                    key={index} 
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    data-testid={`order-test-${test.test_id}`}
                  >
                    <div>
                      <p className="font-medium text-slate-900">{test.test_name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <code className="text-xs text-slate-500">{test.test_code}</code>
                        <Badge className={getStatusColor(test.status || 'pending')}>
                          {formatStatus(test.status || 'pending')}
                        </Badge>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-slate-900">{formatCurrency(test.price)}</p>
                      {test.result?.is_abnormal && (
                        <Badge className="bg-rose-100 text-rose-700 mt-1">
                          <AlertCircle className="w-3 h-3 mr-1" />
                          Abnormal
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Samples */}
          {order.samples && order.samples.length > 0 && (
            <Card className="border border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-indigo-600" />
                  Samples
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {order.samples.map((sample) => (
                    <div 
                      key={sample.id} 
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-slate-900">
                          <code className="font-mono">{sample.sample_id}</code>
                        </p>
                        <p className="text-sm text-slate-500 capitalize">
                          {sample.sample_type} • Barcode: {sample.barcode}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge className={getStatusColor(sample.status)}>
                          {formatStatus(sample.status)}
                        </Badge>
                        {sample.collection_time && (
                          <p className="text-xs text-slate-500 mt-1">
                            Collected: {formatDateTime(sample.collection_time)}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Status History */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-600" />
                Status History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {order.status_history?.map((entry, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-2 h-2 rounded-full bg-indigo-600 mt-2" />
                    <div>
                      <p className="font-medium text-slate-900">{formatStatus(entry.status)}</p>
                      <p className="text-sm text-slate-500">{formatDateTime(entry.timestamp)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Patient Info */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <User className="w-4 h-4 text-indigo-600" />
                Patient
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-medium text-slate-900">{order.patient_name}</p>
              <Button 
                variant="link" 
                className="p-0 h-auto text-indigo-600"
                onClick={() => navigate(`/patients/${order.patient_id}`)}
              >
                View Patient Profile
              </Button>
            </CardContent>
          </Card>

          {/* Billing Summary */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Billing Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Subtotal</span>
                  <span>{formatCurrency(order.total_amount)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Discount</span>
                  <span>-{formatCurrency(order.discount)}</span>
                </div>
                <Separator className="my-2" />
                <div className="flex justify-between font-semibold">
                  <span>Total</span>
                  <span className="text-lg">{formatCurrency(order.net_amount)}</span>
                </div>
              </div>
              {order.invoice && (
                <div className="mt-4 pt-4 border-t border-slate-200">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Invoice</span>
                    <code className="font-mono text-indigo-600">{order.invoice.invoice_id}</code>
                  </div>
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-slate-600">Payment Status</span>
                    <Badge className={getStatusColor(order.invoice.payment_status)}>
                      {formatStatus(order.invoice.payment_status)}
                    </Badge>
                  </div>
                  <Button 
                    variant="outline" 
                    className="w-full mt-3"
                    onClick={() => navigate(`/billing/${order.invoice.id}`)}
                  >
                    View Invoice
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notes */}
          {order.notes && (
            <Card className="border border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600">{order.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
