import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { patientAPI, doctorAPI, getErrorMessage } from '../lib/api';
import { formatDate, formatDateTime, getStatusColor, formatStatus, debounce } from '../lib/utils';
import {
  Search,
  Plus,
  Loader2,
  User,
  Phone,
  Calendar,
  ChevronRight,
  Users,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [doctors, setDoctors] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    father_name: '',
    age: '',
    gender: 'male',
    phone: '',
    email: '',
    referred_by: 'Self',
    address: '',
    id_type: '',
    id_number: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchPatients();
    fetchDoctors();
  }, []);

  const fetchDoctors = async () => {
    try {
      const response = await doctorAPI.getAll();
      setDoctors(response.data);
    } catch (error) {
      // Doctors list is optional; "Self" is always available
    }
  };

  const fetchPatients = async (searchTerm = '') => {
    setLoading(true);
    try {
      const response = await patientAPI.getAll(searchTerm);
      setPatients(response.data);
    } catch (error) {
      toast.error('Failed to fetch patients');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = debounce((value) => {
    fetchPatients(value);
  }, 300);

  const onSearchChange = (e) => {
    setSearch(e.target.value);
    handleSearch(e.target.value);
  };

  const handleCreatePatient = async (e) => {
    e.preventDefault();
    setCreating(true);

    try {
      // Drop empty optional fields — backend validators (e.g. EmailStr) reject ""
      const payload = {
        ...formData,
        age: parseInt(formData.age),
      };
      ['email', 'address', 'id_type', 'id_number', 'father_name'].forEach((k) => {
        if (payload[k] === '') payload[k] = undefined;
      });
      await patientAPI.create(payload);
      toast.success('Patient registered successfully');
      setDialogOpen(false);
      setFormData({
        name: '',
        father_name: '',
        age: '',
        gender: 'male',
        phone: '',
        email: '',
        referred_by: 'Self',
        address: '',
        id_type: '',
        id_number: '',
      });
      fetchPatients();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to register patient'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="patients-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Patients</h1>
          <p className="text-slate-500">Manage patient records</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-patient-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Patient
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">Register New Patient</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreatePatient} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label htmlFor="name">Full Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="patient-name-input"
                  />
                </div>
                <div className="col-span-2">
                  <Label htmlFor="father_name">Father Name</Label>
                  <Input
                    id="father_name"
                    value={formData.father_name}
                    onChange={(e) => setFormData({ ...formData, father_name: e.target.value })}
                    className="mt-1.5"
                    data-testid="patient-father-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="age">Age *</Label>
                  <Input
                    id="age"
                    type="number"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                    required
                    min="0"
                    max="150"
                    className="mt-1.5"
                    data-testid="patient-age-input"
                  />
                </div>
                <div>
                  <Label htmlFor="gender">Gender *</Label>
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => setFormData({ ...formData, gender: value })}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="patient-gender-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="phone">Phone *</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="patient-phone-input"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="mt-1.5"
                    data-testid="patient-email-input"
                  />
                </div>
                <div>
                  <Label htmlFor="referred_by">Referred By</Label>
                  <Select
                    value={formData.referred_by}
                    onValueChange={(value) => setFormData({ ...formData, referred_by: value })}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="patient-referred-by-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Self">Self</SelectItem>
                      {doctors.map((d) => (
                        <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="mt-1.5"
                    data-testid="patient-address-input"
                  />
                </div>
                <div>
                  <Label htmlFor="id_type">ID Type</Label>
                  <Select
                    value={formData.id_type}
                    onValueChange={(value) => setFormData({ ...formData, id_type: value })}
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue placeholder="Select ID type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="passport">Passport</SelectItem>
                      <SelectItem value="drivers_license">Driver's License</SelectItem>
                      <SelectItem value="national_id">National ID</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="id_number">ID Number</Label>
                  <Input
                    id="id_number"
                    value={formData.id_number}
                    onChange={(e) => setFormData({ ...formData, id_number: e.target.value })}
                    className="mt-1.5"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={creating}
                  data-testid="submit-patient-btn"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Register Patient'
                  )}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder="Search by name, phone, or patient ID..."
          value={search}
          onChange={onSearchChange}
          className="pl-10"
          data-testid="patient-search-input"
        />
      </div>

      {/* Patient List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : patients.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Users className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No patients found</h3>
            <p className="text-slate-500 mt-1">
              {search ? 'Try a different search term' : 'Get started by adding your first patient'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Patient</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Serial No</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Contact</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Registered</th>
                  <th className="text-right px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {patients.map((patient) => (
                  <tr 
                    key={patient.id} 
                    className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/patients/${patient.id}`)}
                    data-testid={`patient-row-${patient.id}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center">
                          <User className="w-4 h-4 text-indigo-600" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{patient.name}</p>
                          <p className="text-sm text-slate-500">
                            {patient.age} yrs, {patient.gender.charAt(0).toUpperCase() + patient.gender.slice(1)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-sm font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                        {patient.patient_id}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Phone className="w-3.5 h-3.5" />
                        {patient.phone}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDate(patient.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-400 inline" />
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
