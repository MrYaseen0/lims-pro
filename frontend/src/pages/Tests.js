import { useState, useEffect } from 'react';
import { testAPI, getErrorMessage } from '../lib/api';
import { formatCurrency, formatDate } from '../lib/utils';
import {
  Search,
  Plus,
  Loader2,
  TestTube,
  Clock,
  DollarSign,
  Edit,
  ToggleLeft,
  ToggleRight,
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
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';

const SAMPLE_TYPES = ['blood', 'urine', 'stool', 'saliva', 'swab', 'tissue', 'other'];
const CATEGORIES = ['Hematology', 'Biochemistry', 'Microbiology', 'Immunology', 'Endocrinology', 'Clinical Pathology', 'Molecular Biology'];

export default function Tests() {
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTest, setEditingTest] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    category: '',
    sample_type: 'blood',
    price: '',
    turn_around_time: '',
    description: '',
    is_active: true,
  });

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      const response = await testAPI.getAll({ active_only: false });
      setTests(response.data);
    } catch (error) {
      toast.error('Failed to fetch tests');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const payload = {
        ...formData,
        price: parseFloat(formData.price),
        turn_around_time: parseInt(formData.turn_around_time),
      };

      if (editingTest) {
        await testAPI.update(editingTest.id, payload);
        toast.success('Test updated successfully');
      } else {
        await testAPI.create(payload);
        toast.success('Test created successfully');
      }

      setDialogOpen(false);
      resetForm();
      fetchTests();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save test'));
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      category: '',
      sample_type: 'blood',
      price: '',
      turn_around_time: '',
      description: '',
      is_active: true,
    });
    setEditingTest(null);
  };

  const openEditDialog = (test) => {
    setEditingTest(test);
    setFormData({
      name: test.name,
      code: test.code,
      category: test.category,
      sample_type: test.sample_type,
      price: test.price.toString(),
      turn_around_time: test.turn_around_time.toString(),
      description: test.description || '',
      is_active: test.is_active,
    });
    setDialogOpen(true);
  };

  const toggleTestStatus = async (test) => {
    try {
      await testAPI.update(test.id, { is_active: !test.is_active });
      toast.success(`Test ${test.is_active ? 'disabled' : 'enabled'}`);
      fetchTests();
    } catch (error) {
      toast.error('Failed to update test status');
    }
  };

  const filteredTests = tests.filter(
    (test) =>
      test.name.toLowerCase().includes(search.toLowerCase()) ||
      test.code.toLowerCase().includes(search.toLowerCase()) ||
      test.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in" data-testid="tests-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Test Catalog</h1>
          <p className="text-slate-500">Manage laboratory tests and pricing</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-test-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Test
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">
                {editingTest ? 'Edit Test' : 'Create New Test'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label htmlFor="name">Test Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="test-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="code">Test Code *</Label>
                  <Input
                    id="code"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    required
                    disabled={!!editingTest}
                    className="mt-1.5 uppercase"
                    data-testid="test-code-input"
                  />
                </div>
                <div>
                  <Label htmlFor="category">Category *</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(value) => setFormData({ ...formData, category: value })}
                  >
                    <SelectTrigger className="mt-1.5" data-testid="test-category-select">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((cat) => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="sample_type">Sample Type *</Label>
                  <Select
                    value={formData.sample_type}
                    onValueChange={(value) => setFormData({ ...formData, sample_type: value })}
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SAMPLE_TYPES.map((type) => (
                        <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="price">Price ($) *</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="test-price-input"
                  />
                </div>
                <div>
                  <Label htmlFor="tat">TAT (hours) *</Label>
                  <Input
                    id="tat"
                    type="number"
                    min="1"
                    value={formData.turn_around_time}
                    onChange={(e) => setFormData({ ...formData, turn_around_time: e.target.value })}
                    required
                    className="mt-1.5"
                    data-testid="test-tat-input"
                  />
                </div>
                <div className="col-span-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="mt-1.5"
                    rows={3}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={saving}
                  data-testid="submit-test-btn"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    editingTest ? 'Update Test' : 'Create Test'
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
          placeholder="Search tests..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
          data-testid="test-search-input"
        />
      </div>

      {/* Tests Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : filteredTests.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <TestTube className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No tests found</h3>
            <p className="text-slate-500 mt-1">
              {search ? 'Try a different search term' : 'Get started by adding your first test'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTests.map((test) => (
            <Card 
              key={test.id} 
              className={`border ${test.is_active ? 'border-slate-200 hover:border-indigo-200' : 'border-slate-200 bg-slate-50 opacity-75'} transition-colors`}
              data-testid={`test-card-${test.id}`}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                        {test.code}
                      </code>
                      {!test.is_active && (
                        <Badge variant="outline" className="text-slate-500">Disabled</Badge>
                      )}
                    </div>
                    <h3 className="font-semibold text-slate-900 mt-2">{test.name}</h3>
                    <p className="text-sm text-slate-500">{test.category}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-sm text-slate-600 mb-4">
                  <div className="flex items-center gap-1.5">
                    <DollarSign className="w-4 h-4 text-emerald-600" />
                    {formatCurrency(test.price)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-amber-600" />
                    {test.turn_around_time}h TAT
                  </div>
                </div>

                {test.reference_ranges && test.reference_ranges.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                      Reference Ranges
                    </p>
                    <div className="max-h-48 overflow-y-auto border border-slate-100 rounded">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-slate-50">
                          <tr className="text-left text-xs text-slate-400">
                            <th className="py-1.5 px-2 font-medium">Parameter</th>
                            <th className="py-1.5 px-2 font-medium">Unit</th>
                            <th className="py-1.5 px-2 font-medium">Normal Range</th>
                          </tr>
                        </thead>
                        <tbody>
                          {test.reference_ranges.map((r, i) => (
                            <tr key={i} className="border-t border-slate-100">
                              <td className="py-1.5 px-2 text-slate-700">{r.parameter}</td>
                              <td className="py-1.5 px-2 text-slate-500">{r.unit}</td>
                              <td className="py-1.5 px-2 text-slate-600 whitespace-nowrap">{r.normal_range}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex-1"
                    onClick={() => openEditDialog(test)}
                  >
                    <Edit className="w-3.5 h-3.5 mr-1.5" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleTestStatus(test)}
                    className={test.is_active ? 'text-rose-600 hover:text-rose-700' : 'text-emerald-600 hover:text-emerald-700'}
                  >
                    {test.is_active ? (
                      <ToggleRight className="w-5 h-5" />
                    ) : (
                      <ToggleLeft className="w-5 h-5" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
