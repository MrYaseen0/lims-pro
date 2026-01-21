import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { invoiceAPI } from '../lib/api';
import { formatDateTime, getStatusColor, formatStatus, formatCurrency } from '../lib/utils';
import {
  ArrowLeft,
  Loader2,
  CreditCard,
  User,
  FileText,
  DollarSign,
  CheckCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    payment_mode: 'cash',
    reference: '',
  });

  useEffect(() => {
    fetchInvoice();
  }, [id]);

  const fetchInvoice = async () => {
    try {
      const response = await invoiceAPI.getById(id);
      setInvoice(response.data);
    } catch (error) {
      toast.error('Failed to fetch invoice');
      navigate('/billing');
    } finally {
      setLoading(false);
    }
  };

  const calculatePaid = () => {
    return (invoice?.payments || []).reduce((sum, p) => sum + p.amount, 0);
  };

  const calculateDue = () => {
    return (invoice?.net_amount || 0) - calculatePaid();
  };

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await invoiceAPI.recordPayment({
        invoice_id: invoice.id,
        amount: parseFloat(paymentForm.amount),
        payment_mode: paymentForm.payment_mode,
        reference: paymentForm.reference,
      });

      toast.success('Payment recorded successfully');
      setPaymentDialogOpen(false);
      setPaymentForm({ amount: '', payment_mode: 'cash', reference: '' });
      fetchInvoice();
    } catch (error) {
      toast.error('Failed to record payment');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!invoice) return null;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="invoice-detail">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/billing')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 font-heading">
                <code className="font-mono">{invoice.invoice_id}</code>
              </h1>
              <Badge className={getStatusColor(invoice.payment_status)}>
                {formatStatus(invoice.payment_status)}
              </Badge>
            </div>
            <p className="text-slate-500">Created {formatDateTime(invoice.created_at)}</p>
          </div>
        </div>
        {invoice.payment_status !== 'paid' && (
          <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-emerald-600 hover:bg-emerald-700" data-testid="record-payment-btn">
                <DollarSign className="w-4 h-4 mr-2" />
                Record Payment
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="font-heading">Record Payment</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleRecordPayment} className="space-y-4 mt-4">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Amount Due</span>
                    <span className="font-bold text-slate-900">{formatCurrency(calculateDue())}</span>
                  </div>
                </div>

                <div>
                  <Label htmlFor="amount">Payment Amount *</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    min="0"
                    max={calculateDue()}
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
                    required
                    className="mt-1.5"
                    data-testid="payment-amount-input"
                  />
                </div>

                <div>
                  <Label htmlFor="mode">Payment Mode</Label>
                  <Select
                    value={paymentForm.payment_mode}
                    onValueChange={(value) => setPaymentForm(prev => ({ ...prev, payment_mode: value }))}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="payment-mode-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cash">Cash</SelectItem>
                      <SelectItem value="card">Card</SelectItem>
                      <SelectItem value="upi">UPI</SelectItem>
                      <SelectItem value="online">Online</SelectItem>
                      <SelectItem value="insurance">Insurance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="reference">Reference Number</Label>
                  <Input
                    id="reference"
                    value={paymentForm.reference}
                    onChange={(e) => setPaymentForm(prev => ({ ...prev, reference: e.target.value }))}
                    placeholder="Transaction ID, Check Number, etc."
                    className="mt-1.5"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setPaymentDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    className="bg-emerald-600 hover:bg-emerald-700"
                    disabled={saving}
                    data-testid="submit-payment-btn"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      'Record Payment'
                    )}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Details */}
          {invoice.order && (
            <Card className="border border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  Order Details
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Order ID</span>
                    <code className="font-mono text-indigo-600">{invoice.order.order_id}</code>
                  </div>
                  <Separator />
                  {invoice.order.tests?.map((test) => (
                    <div key={test.test_id} className="flex justify-between">
                      <span className="text-slate-700">{test.test_name}</span>
                      <span className="font-medium">{formatCurrency(test.price)}</span>
                    </div>
                  ))}
                  <Separator />
                  <div className="flex justify-between">
                    <span className="text-slate-500">Subtotal</span>
                    <span>{formatCurrency(invoice.amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Discount</span>
                    <span className="text-emerald-600">-{formatCurrency(invoice.discount)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total</span>
                    <span>{formatCurrency(invoice.net_amount)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Payment History */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-indigo-600" />
                Payment History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.payments && invoice.payments.length > 0 ? (
                <div className="space-y-3">
                  {invoice.payments.map((payment, index) => (
                    <div 
                      key={index} 
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                          <CheckCircle className="w-4 h-4 text-emerald-600" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900 capitalize">{payment.mode}</p>
                          <p className="text-sm text-slate-500">
                            {formatDateTime(payment.recorded_at)}
                            {payment.reference && ` • Ref: ${payment.reference}`}
                          </p>
                        </div>
                      </div>
                      <span className="font-bold text-emerald-600">
                        +{formatCurrency(payment.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <CreditCard className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                  <p>No payments recorded yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Patient Info */}
          {invoice.patient && (
            <Card className="border border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <User className="w-4 h-4 text-indigo-600" />
                  Patient
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium text-slate-900">{invoice.patient.name}</p>
                <p className="text-sm text-slate-500">{invoice.patient.phone}</p>
                <Button 
                  variant="link" 
                  className="p-0 h-auto text-indigo-600 mt-2"
                  onClick={() => navigate(`/patients/${invoice.patient.id}`)}
                >
                  View Profile
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Payment Summary */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Payment Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Amount</span>
                  <span className="font-medium">{formatCurrency(invoice.net_amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Paid</span>
                  <span className="font-medium text-emerald-600">{formatCurrency(calculatePaid())}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-lg font-bold">
                  <span>Balance Due</span>
                  <span className={calculateDue() > 0 ? 'text-amber-600' : 'text-emerald-600'}>
                    {formatCurrency(calculateDue())}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
