import { useState, useEffect, useCallback } from 'react';
import { inventoryAPI, getErrorMessage } from '../lib/api';
import { formatDate } from '../lib/utils';
import {
  Search,
  Loader2,
  Package,
  Plus,
  Edit,
  Trash2,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
import Pagination from '../components/Pagination';
import { toast } from 'sonner';

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'All Categories' },
  { value: 'reagent', label: 'Reagent' },
  { value: 'consumable', label: 'Consumable' },
];

const EMPTY_FORM = {
  name: '',
  category: 'reagent',
  lot_number: '',
  quantity: '',
  unit: '',
  min_stock: '',
  expiry_date: '',
  supplier: '',
};

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [alerts, setAlerts] = useState({ expired: [], expiring_soon: [], low_stock: [] });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (category && category !== 'all') params.category = category;
      const response = await inventoryAPI.getAll(params);
      setItems(response.data);
      setTotal(parseInt(response.headers['x-total-count'] || '0', 10));
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to fetch inventory'));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, category]);

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await inventoryAPI.getAlerts();
      setAlerts({
        expired: response.data.expired || [],
        expiring_soon: response.data.expiring_soon || [],
        low_stock: response.data.low_stock || [],
      });
    } catch {
      // Alerts are nice-to-have; don't toast on failure
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const openAdd = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      name: item.name || '',
      category: item.category || 'reagent',
      lot_number: item.lot_number || '',
      quantity: item.quantity ?? '',
      unit: item.unit || '',
      min_stock: item.min_stock ?? '',
      expiry_date: item.expiry_date ? String(item.expiry_date).slice(0, 10) : '',
      supplier: item.supplier || '',
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        quantity: form.quantity === '' ? 0 : Number(form.quantity),
        min_stock: form.min_stock === '' ? 0 : Number(form.min_stock),
        expiry_date: form.expiry_date || null,
      };
      if (editing) {
        await inventoryAPI.update(editing.id, payload);
        toast.success('Item updated');
      } else {
        await inventoryAPI.create(payload);
        toast.success('Item added');
      }
      setDialogOpen(false);
      fetchItems();
      fetchAlerts();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save item'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await inventoryAPI.remove(deleteId);
      toast.success('Item deleted');
      setDeleteId(null);
      fetchItems();
      fetchAlerts();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to delete item'));
    } finally {
      setDeleting(false);
    }
  };

  const lowStockIds = new Set(alerts.low_stock.map((i) => i.id));
  const expiredIds = new Set(alerts.expired.map((i) => i.id));
  const expiringIds = new Set(alerts.expiring_soon.map((i) => i.id));

  const rowClass = (item) => {
    if (expiredIds.has(item.id)) return 'bg-rose-50 hover:bg-rose-100/60';
    if (expiringIds.has(item.id)) return 'bg-amber-50/70 hover:bg-amber-100/60';
    if (lowStockIds.has(item.id)) return 'bg-amber-50/50 hover:bg-amber-100/50';
    return 'hover:bg-slate-50/50';
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="inventory-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Inventory</h1>
          <p className="text-slate-500">Track reagents and consumables</p>
        </div>
        <Button onClick={openAdd} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-item-btn">
          <Plus className="w-4 h-4 mr-2" />
          Add Item
        </Button>
      </div>

      {/* Alerts banner */}
      {(alerts.expired.length > 0 || alerts.expiring_soon.length > 0 || alerts.low_stock.length > 0) && (
        <div className="space-y-2" data-testid="inventory-alerts">
          {alerts.expired.length > 0 && (
            <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-lg">
              <XCircle className="w-5 h-5 text-rose-600 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-rose-800">
                  {alerts.expired.length} expired item{alerts.expired.length > 1 ? 's' : ''}
                </p>
                <p className="text-sm text-rose-700">
                  {alerts.expired.slice(0, 5).map((i) => i.name).join(', ')}
                  {alerts.expired.length > 5 ? ` and ${alerts.expired.length - 5} more` : ''}
                </p>
              </div>
            </div>
          )}
          {alerts.expiring_soon.length > 0 && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-amber-800">
                  {alerts.expiring_soon.length} item{alerts.expiring_soon.length > 1 ? 's' : ''} expiring soon
                </p>
                <p className="text-sm text-amber-700">
                  {alerts.expiring_soon.slice(0, 5).map((i) => i.name).join(', ')}
                  {alerts.expiring_soon.length > 5 ? ` and ${alerts.expiring_soon.length - 5} more` : ''}
                </p>
              </div>
            </div>
          )}
          {alerts.low_stock.length > 0 && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-amber-800">
                  {alerts.low_stock.length} item{alerts.low_stock.length > 1 ? 's' : ''} low on stock
                </p>
                <p className="text-sm text-amber-700">
                  {alerts.low_stock.slice(0, 5).map((i) => `${i.name} (${i.quantity} left)`).join(', ')}
                  {alerts.low_stock.length > 5 ? ` and ${alerts.low_stock.length - 5} more` : ''}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name, lot number, supplier..."
            className="pl-10"
            data-testid="inventory-search"
          />
        </div>
        <Select
          value={category}
          onValueChange={(v) => {
            setCategory(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-full sm:w-[180px]" data-testid="inventory-category-filter">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORY_OPTIONS.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : items.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Package className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No inventory items</h3>
            <p className="text-slate-500 mt-1">Add reagents and consumables to track stock</p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Lot #</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Qty</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Min Stock</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Expiry</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Supplier</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className={`border-b border-slate-100 transition-colors ${rowClass(item)}`}
                    data-testid={`inventory-row-${item.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {item.name}
                      {expiredIds.has(item.id) && (
                        <Badge className="ml-2 bg-rose-100 text-rose-700">Expired</Badge>
                      )}
                      {lowStockIds.has(item.id) && !expiredIds.has(item.id) && (
                        <Badge className="ml-2 bg-amber-100 text-amber-700">Low stock</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={item.category === 'reagent' ? 'bg-violet-100 text-violet-700' : 'bg-blue-100 text-blue-700'}>
                        {item.category}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">{item.lot_number || '-'}</code>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700 font-medium">
                      {item.quantity} {item.unit}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">{item.min_stock}</td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {item.expiry_date ? formatDate(item.expiry_date) : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">{item.supplier || '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(item)} data-testid={`edit-item-${item.id}`}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-rose-600 hover:text-rose-700"
                          onClick={() => setDeleteId(item.id)}
                          data-testid={`delete-item-${item.id}`}
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
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
            onPageSizeChange={(s) => {
              setPageSize(s);
              setPage(1);
            }}
          />
        </div>
      )}

      {/* Add/Edit modal */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">{editing ? 'Edit Item' : 'Add Inventory Item'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <div>
              <Label htmlFor="inv-name">Name *</Label>
              <Input
                id="inv-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                className="mt-1.5"
                data-testid="inventory-name-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Category *</Label>
                <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                  <SelectTrigger className="mt-1.5" data-testid="inventory-category-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reagent">Reagent</SelectItem>
                    <SelectItem value="consumable">Consumable</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="inv-lot">Lot Number</Label>
                <Input
                  id="inv-lot"
                  value={form.lot_number}
                  onChange={(e) => setForm({ ...form, lot_number: e.target.value })}
                  className="mt-1.5"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="inv-qty">Quantity *</Label>
                <Input
                  id="inv-qty"
                  type="number"
                  min="0"
                  step="any"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="inv-unit">Unit</Label>
                <Input
                  id="inv-unit"
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                  placeholder="e.g. mL, vials"
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="inv-min">Min Stock</Label>
                <Input
                  id="inv-min"
                  type="number"
                  min="0"
                  step="any"
                  value={form.min_stock}
                  onChange={(e) => setForm({ ...form, min_stock: e.target.value })}
                  className="mt-1.5"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="inv-expiry">Expiry Date</Label>
                <Input
                  id="inv-expiry"
                  type="date"
                  value={form.expiry_date}
                  onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="inv-supplier">Supplier</Label>
                <Input
                  id="inv-supplier"
                  value={form.supplier}
                  onChange={(e) => setForm({ ...form, supplier: e.target.value })}
                  className="mt-1.5"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" disabled={saving} data-testid="save-item-btn">
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : editing ? (
                  'Save Changes'
                ) : (
                  'Add Item'
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-heading">Delete Item</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600 mt-2">
            Are you sure you want to delete this inventory item? This cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              className="bg-rose-600 hover:bg-rose-700"
              onClick={handleDelete}
              disabled={deleting}
              data-testid="confirm-delete-item-btn"
            >
              {deleting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
