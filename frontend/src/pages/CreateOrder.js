import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { orderAPI, patientAPI, testAPI, doctorAPI } from '../lib/api';
import { formatCurrency } from '../lib/utils';
import {
  ArrowLeft,
  Search,
  Plus,
  Minus,
  Loader2,
  User,
  TestTube,
  ShoppingCart,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

export default function CreateOrder() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const preSelectedPatient = searchParams.get('patient');

  const [patients, setPatients] = useState([]);
  const [tests, setTests] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [patientSearch, setPatientSearch] = useState('');
  const [testSearch, setTestSearch] = useState('');

  const [formData, setFormData] = useState({
    patient_id: preSelectedPatient || '',
    tests: [],
    priority: 'normal',
    referring_doctor: '',
    notes: '',
  });

  const [selectedPatient, setSelectedPatient] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (preSelectedPatient) {
      fetchPatient(preSelectedPatient);
    }
  }, [preSelectedPatient]);

  const fetchInitialData = async () => {
    try {
      const [patientsRes, testsRes, doctorsRes] = await Promise.all([
        patientAPI.getAll(),
        testAPI.getAll({ active_only: true }),
        doctorAPI.getAll().catch(() => ({ data: [] })),
      ]);
      setPatients(patientsRes.data);
      setTests(testsRes.data);
      setDoctors(doctorsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const fetchPatient = async (patientId) => {
    try {
      const response = await patientAPI.getById(patientId);
      setSelectedPatient(response.data);
      setFormData(prev => ({ ...prev, patient_id: patientId }));
    } catch (error) {
      console.error('Failed to fetch patient');
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient);
    setFormData(prev => ({ ...prev, patient_id: patient.id }));
    setPatientSearch('');
  };

  const addTest = (test) => {
    if (formData.tests.find(t => t.test_id === test.id)) {
      toast.info('Test already added');
      return;
    }
    setFormData(prev => ({
      ...prev,
      tests: [...prev.tests, {
        test_id: test.id,
        test_name: test.name,
        test_code: test.code,
        price: test.price,
      }],
    }));
    setTestSearch('');
  };

  const removeTest = (testId) => {
    setFormData(prev => ({
      ...prev,
      tests: prev.tests.filter(t => t.test_id !== testId),
    }));
  };

  const calculateTotal = () => {
    return formData.tests.reduce((sum, test) => sum + test.price, 0);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.patient_id) {
      toast.error('Please select a patient');
      return;
    }
    if (formData.tests.length === 0) {
      toast.error('Please add at least one test');
      return;
    }

    setCreating(true);
    try {
      const response = await orderAPI.create(formData);
      toast.success('Order created successfully');
      navigate(`/orders/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create order');
    } finally {
      setCreating(false);
    }
  };

  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(patientSearch.toLowerCase()) ||
    p.phone.includes(patientSearch) ||
    p.patient_id.toLowerCase().includes(patientSearch.toLowerCase())
  ).slice(0, 5);

  const filteredTests = tests.filter(t =>
    t.name.toLowerCase().includes(testSearch.toLowerCase()) ||
    t.code.toLowerCase().includes(testSearch.toLowerCase())
  ).slice(0, 8);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="create-order-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/orders')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Create Order</h1>
          <p className="text-slate-500">Add tests for a patient</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Patient Selection */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <User className="w-4 h-4 text-indigo-600" />
                Select Patient
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedPatient ? (
                <div className="flex items-center justify-between p-3 bg-indigo-50 rounded-lg">
                  <div>
                    <p className="font-medium text-slate-900">{selectedPatient.name}</p>
                    <p className="text-sm text-slate-500">
                      {selectedPatient.age} yrs, {selectedPatient.gender} • {selectedPatient.phone}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => { setSelectedPatient(null); setFormData(prev => ({ ...prev, patient_id: '' })); }}>
                    Change
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    placeholder="Search by name, phone, or patient ID..."
                    value={patientSearch}
                    onChange={(e) => setPatientSearch(e.target.value)}
                    className="pl-10"
                    data-testid="patient-search"
                  />
                  {patientSearch && filteredPatients.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-10 overflow-hidden">
                      {filteredPatients.map((patient) => (
                        <button
                          key={patient.id}
                          type="button"
                          onClick={() => selectPatient(patient)}
                          className="w-full px-4 py-3 text-left hover:bg-slate-50 border-b border-slate-100 last:border-0"
                          data-testid={`patient-option-${patient.id}`}
                        >
                          <p className="font-medium text-slate-900">{patient.name}</p>
                          <p className="text-sm text-slate-500">
                            {patient.patient_id} • {patient.phone}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Test Selection */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <TestTube className="w-4 h-4 text-indigo-600" />
                Add Tests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search tests..."
                  value={testSearch}
                  onChange={(e) => setTestSearch(e.target.value)}
                  className="pl-10"
                  data-testid="test-search"
                />
                {testSearch && filteredTests.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
                    {filteredTests.map((test) => (
                      <button
                        key={test.id}
                        type="button"
                        onClick={() => addTest(test)}
                        className="w-full px-4 py-3 text-left hover:bg-slate-50 border-b border-slate-100 last:border-0 flex items-center justify-between"
                        data-testid={`test-option-${test.id}`}
                      >
                        <div>
                          <p className="font-medium text-slate-900">{test.name}</p>
                          <p className="text-sm text-slate-500">
                            {test.code} • {test.category}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-emerald-600">{formatCurrency(test.price)}</span>
                          <Plus className="w-4 h-4 text-indigo-600" />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected Tests */}
              {formData.tests.length > 0 ? (
                <div className="space-y-2">
                  {formData.tests.map((test) => (
                    <div 
                      key={test.test_id} 
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                      data-testid={`selected-test-${test.test_id}`}
                    >
                      <div>
                        <p className="font-medium text-slate-900">{test.test_name}</p>
                        <code className="text-xs text-slate-500">{test.test_code}</code>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-slate-900">{formatCurrency(test.price)}</span>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                          onClick={() => removeTest(test.test_id)}
                        >
                          <Minus className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <TestTube className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                  <p>No tests selected. Search and add tests above.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Additional Info */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Additional Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Priority</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, priority: value }))}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="priority-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                      <SelectItem value="stat">STAT</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Referring Doctor</Label>
                  <Select
                    value={formData.referring_doctor}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, referring_doctor: value }))}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="referring-doctor-select">
                      <SelectValue placeholder="Select doctor" />
                    </SelectTrigger>
                    <SelectContent>
                      {doctors.map((d) => (
                        <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label>Notes</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Any special instructions..."
                  className="mt-1.5"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Summary */}
        <div>
          <Card className="border border-slate-200 sticky top-20">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-indigo-600" />
                Order Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 mb-4">
                {formData.tests.map((test) => (
                  <div key={test.test_id} className="flex justify-between text-sm">
                    <span className="text-slate-600">{test.test_name}</span>
                    <span className="font-medium">{formatCurrency(test.price)}</span>
                  </div>
                ))}
                {formData.tests.length === 0 && (
                  <p className="text-sm text-slate-500 text-center py-4">No tests added</p>
                )}
              </div>

              <div className="border-t border-slate-200 pt-3 mb-4">
                <div className="flex justify-between font-semibold">
                  <span>Total</span>
                  <span className="text-lg">{formatCurrency(calculateTotal())}</span>
                </div>
              </div>

              <Button 
                className="w-full bg-indigo-600 hover:bg-indigo-700"
                disabled={creating || !formData.patient_id || formData.tests.length === 0}
                onClick={handleSubmit}
                data-testid="create-order-submit"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Order'
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
