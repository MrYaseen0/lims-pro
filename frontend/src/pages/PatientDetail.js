import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { patientAPI } from '../lib/api';
import { formatDate, formatDateTime, getStatusColor, formatStatus, formatCurrency } from '../lib/utils';
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  FileText,
  CreditCard,
  Loader2,
  Plus,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPatient();
  }, [id]);

  const fetchPatient = async () => {
    try {
      const response = await patientAPI.getById(id);
      setPatient(response.data);
    } catch (error) {
      toast.error('Failed to fetch patient details');
      navigate('/patients');
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

  if (!patient) return null;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="patient-detail">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/patients')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center">
              <User className="w-7 h-7 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 font-heading">{patient.name}</h1>
              <p className="text-slate-500">
                <span className="text-xs uppercase tracking-wider mr-1">Serial No</span>
                <code className="text-sm font-mono bg-slate-100 px-2 py-0.5 rounded">{patient.patient_id}</code>
              </p>
            </div>
          </div>
        </div>
        <Button asChild className="bg-indigo-600 hover:bg-indigo-700">
          <Link to={`/orders/new?patient=${patient.id}`} data-testid="create-order-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create Order
          </Link>
        </Button>
      </div>

      {/* Patient Info Card */}
      <Card className="border border-slate-200">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Age / Gender</p>
                <p className="font-medium text-slate-900">
                  {patient.age} years, {patient.gender.charAt(0).toUpperCase() + patient.gender.slice(1)}
                </p>
              </div>
            </div>
            {patient.father_name && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <User className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Father Name</p>
                  <p className="font-medium text-slate-900">{patient.father_name}</p>
                </div>
              </div>
            )}
            {patient.referred_by && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Referred By</p>
                  <p className="font-medium text-slate-900">{patient.referred_by}</p>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                <Phone className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Phone</p>
                <p className="font-medium text-slate-900">{patient.phone}</p>
              </div>
            </div>
            {patient.email && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <Mail className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Email</p>
                  <p className="font-medium text-slate-900">{patient.email}</p>
                </div>
              </div>
            )}
            {patient.address && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Address</p>
                  <p className="font-medium text-slate-900 truncate max-w-xs">{patient.address}</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Orders */}
      <Card className="border border-slate-200">
        <CardHeader className="border-b border-slate-200">
          <CardTitle className="font-heading flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" />
            Order History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {patient.orders && patient.orders.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {patient.orders.map((order) => (
                <Link
                  key={order.id}
                  to={`/orders/${order.id}`}
                  className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
                  data-testid={`order-row-${order.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                      <FileText className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">
                        <code className="font-mono text-sm">{order.order_id}</code>
                      </p>
                      <p className="text-sm text-slate-500">
                        {order.tests?.length || 0} test(s) • {formatDateTime(order.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge className={getStatusColor(order.status)}>
                      {formatStatus(order.status)}
                    </Badge>
                    <span className="font-medium text-slate-900">
                      {formatCurrency(order.net_amount)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500">
              <FileText className="w-12 h-12 text-slate-300 mb-3" />
              <p>No orders yet</p>
              <Button asChild variant="link" className="text-indigo-600 mt-2">
                <Link to={`/orders/new?patient=${patient.id}`}>Create first order</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
