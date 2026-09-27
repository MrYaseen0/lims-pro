import { useState, useEffect } from 'react';
import { userAPI, branchAPI, getErrorMessage } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime, getInitials } from '../lib/utils';
import {
  Loader2,
  Settings as SettingsIcon,
  Users,
  Shield,
  Building,
  Plus,
  Edit,
  CheckCircle,
  XCircle,
  Trash2,
  MapPin,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { toast } from 'sonner';

const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'lab_manager', label: 'Lab Manager' },
  { value: 'technician', label: 'Technician' },
  { value: 'pathologist', label: 'Pathologist' },
  { value: 'receptionist', label: 'Receptionist' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'collection_staff', label: 'Collection Staff' },
];

const EMPTY_BRANCH_FORM = { name: '', code: '', address: '', phone: '' };

export default function Settings() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'technician',
    phone: '',
  });
  const { user: currentUser } = useAuth();

  // Branches (admin only — this page is admin-gated by the nav)
  const [branches, setBranches] = useState([]);
  const [branchesLoading, setBranchesLoading] = useState(true);
  const [branchDialogOpen, setBranchDialogOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [branchForm, setBranchForm] = useState(EMPTY_BRANCH_FORM);
  const [savingBranch, setSavingBranch] = useState(false);
  const [deleteBranchId, setDeleteBranchId] = useState(null);

  useEffect(() => {
    fetchUsers();
    fetchBranches();
  }, []);

  const fetchBranches = async () => {
    try {
      const response = await branchAPI.getAll();
      setBranches(response.data);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to fetch branches'));
    } finally {
      setBranchesLoading(false);
    }
  };

  const openAddBranch = () => {
    setEditingBranch(null);
    setBranchForm(EMPTY_BRANCH_FORM);
    setBranchDialogOpen(true);
  };

  const openEditBranch = (branch) => {
    setEditingBranch(branch);
    setBranchForm({
      name: branch.name || '',
      code: branch.code || '',
      address: branch.address || '',
      phone: branch.phone || '',
    });
    setBranchDialogOpen(true);
  };

  const handleSaveBranch = async (e) => {
    e.preventDefault();
    setSavingBranch(true);
    try {
      if (editingBranch) {
        await branchAPI.update(editingBranch.id, branchForm);
        toast.success('Branch updated');
      } else {
        await branchAPI.create(branchForm);
        toast.success('Branch created');
      }
      setBranchDialogOpen(false);
      fetchBranches();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save branch'));
    } finally {
      setSavingBranch(false);
    }
  };

  const handleDeleteBranch = async () => {
    if (!deleteBranchId) return;
    try {
      await branchAPI.remove(deleteBranchId);
      toast.success('Branch deleted');
      setDeleteBranchId(null);
      fetchBranches();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to delete branch'));
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await userAPI.getAll();
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      // Using the auth register endpoint for creating users
      // (auth travels via the httpOnly cookie)
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create user');
      }

      toast.success('User created successfully');
      setDialogOpen(false);
      setFormData({
        email: '',
        password: '',
        name: '',
        role: 'technician',
        phone: '',
      });
      fetchUsers();
    } catch (error) {
      toast.error(error.message || 'Failed to create user');
    } finally {
      setSaving(false);
    }
  };

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await userAPI.update(userId, { is_active: !isActive });
      toast.success(`User ${isActive ? 'deactivated' : 'activated'}`);
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update user status');
    }
  };

  const getRoleBadgeColor = (role) => {
    const colors = {
      admin: 'bg-rose-100 text-rose-700',
      lab_manager: 'bg-violet-100 text-violet-700',
      technician: 'bg-blue-100 text-blue-700',
      pathologist: 'bg-emerald-100 text-emerald-700',
      receptionist: 'bg-amber-100 text-amber-700',
      doctor: 'bg-indigo-100 text-indigo-700',
      collection_staff: 'bg-slate-100 text-slate-700',
    };
    return colors[role] || 'bg-slate-100 text-slate-700';
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="settings-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Settings</h1>
          <p className="text-slate-500">Manage users and system configuration</p>
        </div>
      </div>

      <Tabs defaultValue="users" className="space-y-6">
        <TabsList>
          <TabsTrigger value="users" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Users
          </TabsTrigger>
          <TabsTrigger value="branches" className="flex items-center gap-2">
            <MapPin className="w-4 h-4" />
            Branches
          </TabsTrigger>
          <TabsTrigger value="lab" className="flex items-center gap-2">
            <Building className="w-4 h-4" />
            Lab Info
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-6">
          {/* User Management */}
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold font-heading">User Management</h2>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-user-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add User
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle className="font-heading">Create New User</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleCreateUser} className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="name">Full Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                      className="mt-1.5"
                      data-testid="user-name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                      className="mt-1.5"
                      data-testid="user-email-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                      className="mt-1.5"
                      data-testid="user-password-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="role">Role *</Label>
                    <Select
                      value={formData.role}
                      onValueChange={(value) => setFormData({ ...formData, role: value })}
                    >
                      <SelectTrigger className="mt-1.5" data-testid="user-role-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            {role.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="mt-1.5"
                    />
                  </div>
                  <div className="flex justify-end gap-3 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button 
                      type="submit" 
                      className="bg-indigo-600 hover:bg-indigo-700"
                      disabled={saving}
                      data-testid="submit-user-btn"
                    >
                      {saving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create User'
                      )}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">User</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Created</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr 
                        key={user.id} 
                        className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors"
                        data-testid={`user-row-${user.id}`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <Avatar className="w-9 h-9 bg-indigo-100">
                              <AvatarFallback className="bg-indigo-100 text-indigo-600 text-sm">
                                {getInitials(user.name)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-slate-900">{user.name}</p>
                              <p className="text-sm text-slate-500">{user.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={getRoleBadgeColor(user.role)}>
                            {user.role.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          {user.is_active ? (
                            <Badge className="bg-emerald-100 text-emerald-700">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Active
                            </Badge>
                          ) : (
                            <Badge className="bg-slate-100 text-slate-600">
                              <XCircle className="w-3 h-3 mr-1" />
                              Inactive
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">
                          {formatDateTime(user.created_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {user.id !== currentUser?.id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleUserStatus(user.id, user.is_active)}
                              className={user.is_active ? 'text-rose-600 hover:text-rose-700' : 'text-emerald-600 hover:text-emerald-700'}
                            >
                              {user.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="branches" className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold font-heading">Branch Management</h2>
            <Button onClick={openAddBranch} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-branch-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Branch
            </Button>
          </div>

          {branchesLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
          ) : branches.length === 0 ? (
            <Card className="border border-slate-200">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <MapPin className="w-12 h-12 text-slate-300 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900">No branches yet</h3>
                <p className="text-slate-500 mt-1">Add your first lab branch</p>
              </CardContent>
            </Card>
          ) : (
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Name</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Code</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Address</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Phone</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {branches.map((branch) => (
                      <tr
                        key={branch.id}
                        className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors"
                        data-testid={`branch-row-${branch.id}`}
                      >
                        <td className="px-4 py-3 font-medium text-slate-900">{branch.name}</td>
                        <td className="px-4 py-3">
                          <code className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">
                            {branch.code || '-'}
                          </code>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">{branch.address || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-500">{branch.phone || '-'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditBranch(branch)} data-testid={`edit-branch-${branch.id}`}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-rose-600 hover:text-rose-700"
                              onClick={() => setDeleteBranchId(branch.id)}
                              data-testid={`delete-branch-${branch.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Add/Edit branch dialog */}
          <Dialog open={branchDialogOpen} onOpenChange={setBranchDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="font-heading">
                  {editingBranch ? 'Edit Branch' : 'Add Branch'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSaveBranch} className="space-y-4 mt-4">
                <div>
                  <Label htmlFor="branch-name">Name *</Label>
                  <Input
                    id="branch-name"
                    value={branchForm.name}
                    onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="branch-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="branch-code">Code *</Label>
                  <Input
                    id="branch-code"
                    value={branchForm.code}
                    onChange={(e) => setBranchForm({ ...branchForm, code: e.target.value })}
                    placeholder="e.g. MAIN, NORTH"
                    required
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="branch-address">Address</Label>
                  <Input
                    id="branch-address"
                    value={branchForm.address}
                    onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="branch-phone">Phone</Label>
                  <Input
                    id="branch-phone"
                    value={branchForm.phone}
                    onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
                    className="mt-1.5"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setBranchDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-indigo-600 hover:bg-indigo-700"
                    disabled={savingBranch}
                    data-testid="save-branch-btn"
                  >
                    {savingBranch ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : editingBranch ? (
                      'Save Changes'
                    ) : (
                      'Add Branch'
                    )}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>

          {/* Delete branch confirm */}
          <Dialog open={!!deleteBranchId} onOpenChange={(open) => !open && setDeleteBranchId(null)}>
            <DialogContent className="max-w-sm">
              <DialogHeader>
                <DialogTitle className="font-heading">Delete Branch</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-slate-600 mt-2">
                Are you sure you want to delete this branch? This cannot be undone.
              </p>
              <div className="flex justify-end gap-3 pt-4">
                <Button variant="outline" onClick={() => setDeleteBranchId(null)}>
                  Cancel
                </Button>
                <Button className="bg-rose-600 hover:bg-rose-700" onClick={handleDeleteBranch}>
                  Delete
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="lab" className="space-y-6">
          <Card className="border border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Building className="w-5 h-5 text-indigo-600" />
                Laboratory Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Lab Name</Label>
                  <Input value="LIMS.Pro Diagnostic Laboratory" className="mt-1.5" disabled />
                </div>
                <div>
                  <Label>Registration Number</Label>
                  <Input value="LAB-2024-001" className="mt-1.5" disabled />
                </div>
                <div className="md:col-span-2">
                  <Label>Address</Label>
                  <Input value="123 Medical Center, Healthcare City" className="mt-1.5" disabled />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input value="+1-234-567-8900" className="mt-1.5" disabled />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input value="info@lims.pro" className="mt-1.5" disabled />
                </div>
              </div>
              <p className="text-sm text-slate-500 mt-4">
                Contact your administrator to update laboratory information.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
