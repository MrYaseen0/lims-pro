import { useState, useEffect, useCallback } from 'react';
import { qcAPI, testAPI, getErrorMessage } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../lib/utils';
import {
  Loader2,
  Activity,
  Plus,
  Edit,
  Trash2,
  FlaskConical,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
} from '../components/ui/dialog';
import { toast } from 'sonner';

const SEVERE_RULES = ['1_3s', '2_2s', 'R_4s', '4_1s', '10_x'];

/**
 * Inline SVG Levey-Jennings chart (no chart libs).
 * x = run date order, y scaled to mean ± 3.2sd.
 */
function LeveyJenningsChart({ chartData }) {
  if (!chartData || !chartData.points || chartData.points.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        No QC runs yet — log a run to build the chart.
      </div>
    );
  }

  const { points, mean, sd, lines } = chartData;
  const W = 820;
  const H = 340;
  const M = { top: 20, right: 24, bottom: 44, left: 64 };
  const plotW = W - M.left - M.right;
  const plotH = H - M.top - M.bottom;

  const yMin = mean - 3.2 * sd;
  const yMax = mean + 3.2 * sd;
  const yScale = (v) => M.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
  const xStep = points.length > 1 ? plotW / (points.length - 1) : 0;
  const xScale = (i) => M.left + i * xStep;

  const fmt = (v) => {
    if (v == null || Number.isNaN(Number(v))) return '-';
    const n = Number(v);
    return Number.isInteger(n) ? String(n) : n.toFixed(2);
  };

  const hlines = [
    { value: lines?.minus3sd ?? mean - 3 * sd, label: '-3SD', color: '#e11d48', dashed: true },
    { value: lines?.minus2sd ?? mean - 2 * sd, label: '-2SD', color: '#e11d48', dashed: true },
    { value: lines?.minus1sd ?? mean - 1 * sd, label: '-1SD', color: '#94a3b8', dashed: true },
    { value: lines?.mean ?? mean, label: 'Mean', color: '#0f172a', dashed: false },
    { value: lines?.plus1sd ?? mean + 1 * sd, label: '+1SD', color: '#94a3b8', dashed: true },
    { value: lines?.plus2sd ?? mean + 2 * sd, label: '+2SD', color: '#e11d48', dashed: true },
    { value: lines?.plus3sd ?? mean + 3 * sd, label: '+3SD', color: '#e11d48', dashed: true },
  ];

  const pointColor = (p) => {
    const v = p.violations || [];
    if (v.some((r) => SEVERE_RULES.includes(r))) return '#e11d48';
    if (v.includes('1_2s')) return '#f59e0b';
    return '#64748b';
  };

  // X-axis date labels: show at most ~8 labels
  const labelEvery = Math.max(1, Math.ceil(points.length / 8));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-auto"
      role="img"
      aria-label="Levey-Jennings QC chart"
      data-testid="lj-chart"
    >
      {/* Grid + SD lines */}
      {hlines.map((l) => (
        <g key={l.label}>
          <line
            x1={M.left}
            x2={M.left + plotW}
            y1={yScale(l.value)}
            y2={yScale(l.value)}
            stroke={l.color}
            strokeWidth={l.label === 'Mean' ? 2 : 1.2}
            strokeDasharray={l.dashed ? '6 4' : 'none'}
            opacity={l.label === 'Mean' ? 1 : 0.75}
          />
          <text
            x={M.left - 8}
            y={yScale(l.value) + 4}
            textAnchor="end"
            fontSize="11"
            fill="#64748b"
          >
            {l.label}
          </text>
          <text
            x={M.left - 8}
            y={yScale(l.value) - 8}
            textAnchor="end"
            fontSize="10"
            fill="#94a3b8"
          >
            {fmt(l.value)}
          </text>
        </g>
      ))}

      {/* Run connector line */}
      {points.length > 1 && (
        <polyline
          points={points.map((p, i) => `${xScale(i)},${yScale(Number(p.value))}`).join(' ')}
          fill="none"
          stroke="#cbd5e1"
          strokeWidth="1.5"
        />
      )}

      {/* Points */}
      {points.map((p, i) => (
        <g key={i}>
          <circle
            cx={xScale(i)}
            cy={yScale(Number(p.value))}
            r={6}
            fill={pointColor(p)}
            stroke="#fff"
            strokeWidth="1.5"
          >
            <title>
              {formatDate(p.date)} — value {fmt(p.value)}
              {(p.violations || []).length > 0 ? ` — ${(p.violations || []).join(', ')}` : ''}
            </title>
          </circle>
          {i % labelEvery === 0 && (
            <text
              x={xScale(i)}
              y={H - 12}
              textAnchor="middle"
              fontSize="10"
              fill="#64748b"
            >
              {formatDate(p.date)}
            </text>
          )}
        </g>
      ))}

      {/* Axes */}
      <line x1={M.left} x2={M.left} y1={M.top} y2={M.top + plotH} stroke="#94a3b8" strokeWidth="1" />
      <line
        x1={M.left}
        x2={M.left + plotW}
        y1={M.top + plotH}
        y2={M.top + plotH}
        stroke="#94a3b8"
        strokeWidth="1"
      />
    </svg>
  );
}

const EMPTY_CONTROL_FORM = {
  name: '',
  test_id: '',
  target_mean: '',
  sd: '',
  unit: '',
};

export default function QC() {
  const { user } = useAuth();
  const [controls, setControls] = useState([]);
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState('');
  const [chartData, setChartData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [controlDialogOpen, setControlDialogOpen] = useState(false);
  const [editingControl, setEditingControl] = useState(null);
  const [controlForm, setControlForm] = useState(EMPTY_CONTROL_FORM);
  const [savingControl, setSavingControl] = useState(false);
  const [deleteControlId, setDeleteControlId] = useState(null);
  const [runValue, setRunValue] = useState('');
  const [runDate, setRunDate] = useState('');
  const [loggingRun, setLoggingRun] = useState(false);

  const canManageControls = ['admin', 'lab_manager'].includes(user?.role);
  const canLogRuns = ['admin', 'lab_manager', 'technician'].includes(user?.role);

  const fetchControls = useCallback(async () => {
    setLoading(true);
    try {
      const [controlsRes, testsRes] = await Promise.all([
        qcAPI.getControls(),
        testAPI.getAll({ page: 1, page_size: 200 }).catch(() => ({ data: [] })),
      ]);
      setControls(controlsRes.data);
      setTests(testsRes.data || []);
      if (!selectedId && controlsRes.data.length > 0) {
        setSelectedId(controlsRes.data[0].id);
      }
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to fetch QC controls'));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchChart = useCallback(async () => {
    if (!selectedId) {
      setChartData(null);
      setRuns([]);
      return;
    }
    setChartLoading(true);
    try {
      const [chartRes, runsRes] = await Promise.all([
        qcAPI.getChartData(selectedId),
        qcAPI.getRuns(selectedId),
      ]);
      setChartData(chartRes.data);
      setRuns(runsRes.data);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to fetch QC chart'));
      setChartData(null);
      setRuns([]);
    } finally {
      setChartLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    fetchControls();
  }, [fetchControls]);

  useEffect(() => {
    fetchChart();
  }, [fetchChart]);

  const openAddControl = () => {
    setEditingControl(null);
    setControlForm(EMPTY_CONTROL_FORM);
    setControlDialogOpen(true);
  };

  const openEditControl = (control) => {
    setEditingControl(control);
    setControlForm({
      name: control.name || '',
      test_id: control.test_id || '',
      target_mean: control.target_mean ?? '',
      sd: control.sd ?? '',
      unit: control.unit || '',
    });
    setControlDialogOpen(true);
  };

  const handleSaveControl = async (e) => {
    e.preventDefault();
    const sdNum = Number(controlForm.sd);
    if (!(sdNum > 0)) {
      toast.error('SD must be greater than 0');
      return;
    }
    setSavingControl(true);
    try {
      const payload = {
        name: controlForm.name,
        target_mean: Number(controlForm.target_mean),
        sd: sdNum,
        test_id: controlForm.test_id || null,
        unit: controlForm.unit || null,
      };
      if (editingControl) {
        await qcAPI.updateControl(editingControl.id, payload);
        toast.success('Control updated');
      } else {
        const res = await qcAPI.createControl(payload);
        toast.success('Control added');
        if (res.data?.id) setSelectedId(res.data.id);
      }
      setControlDialogOpen(false);
      fetchControls();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save control'));
    } finally {
      setSavingControl(false);
    }
  };

  const handleDeleteControl = async () => {
    if (!deleteControlId) return;
    try {
      await qcAPI.deleteControl(deleteControlId);
      toast.success('Control deleted');
      setDeleteControlId(null);
      setSelectedId('');
      fetchControls();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to delete control'));
    }
  };

  const handleLogRun = async (e) => {
    e.preventDefault();
    if (!selectedId) return;
    setLoggingRun(true);
    try {
      await qcAPI.logRun(selectedId, {
        measured_value: Number(runValue),
        ...(runDate ? { date: runDate } : {}),
      });
      toast.success('QC run logged');
      setRunValue('');
      setRunDate('');
      fetchChart();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to log run'));
    } finally {
      setLoggingRun(false);
    }
  };

  const selectedControl = controls.find((c) => c.id === selectedId);
  const violatedRuns = runs.filter((r) => (r.violations || []).length > 0);

  return (
    <div className="space-y-6 animate-fade-in" data-testid="qc-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-heading">Quality Control</h1>
          <p className="text-slate-500">Levey-Jennings charts and Westgard rule monitoring</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {canManageControls && (
            <Button onClick={openAddControl} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-control-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Control
            </Button>
          )}
        </div>
      </div>

      {/* Control selector */}
      <Card className="border border-slate-200">
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <Label>QC Control</Label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger className="mt-1.5 max-w-md" data-testid="qc-control-select">
                  <SelectValue placeholder="Select a control" />
                </SelectTrigger>
                <SelectContent>
                  {controls.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                      {c.unit ? ` (${c.unit})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedControl && canManageControls && (
              <div className="flex gap-2 mt-2 sm:mt-6">
                <Button variant="outline" size="sm" onClick={() => openEditControl(selectedControl)}>
                  <Edit className="w-3.5 h-3.5 mr-1" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-rose-600 hover:text-rose-700"
                  onClick={() => setDeleteControlId(selectedControl.id)}
                >
                  <Trash2 className="w-3.5 h-3.5 mr-1" />
                  Delete
                </Button>
              </div>
            )}
          </div>
          {selectedControl && (
            <div className="flex flex-wrap gap-2 mt-3">
              {selectedControl.unit && <Badge variant="outline">{selectedControl.unit}</Badge>}
              {selectedControl.target_mean != null && (
                <Badge variant="outline">
                  Target {selectedControl.target_mean} ± {selectedControl.sd}
                </Badge>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : controls.length === 0 ? (
        <Card className="border border-slate-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Activity className="w-12 h-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No QC controls</h3>
            <p className="text-slate-500 mt-1">Add a control to start tracking quality runs</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Chart */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-indigo-600" />
                Levey-Jennings Chart
                <span className="text-xs font-normal text-slate-500 ml-2">
                  Red: ±2SD / ±3SD &nbsp;•&nbsp; Red dot: rule violation &nbsp;•&nbsp; Amber: 1_2s warning
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {chartLoading ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                </div>
              ) : (
                <LeveyJenningsChart chartData={chartData} />
              )}
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Log run */}
            {canLogRuns && (
              <Card className="border border-slate-200">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Log QC Run</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleLogRun} className="space-y-4">
                    <div>
                      <Label htmlFor="run-value">Measured Value *</Label>
                      <Input
                        id="run-value"
                        type="number"
                        step="any"
                        value={runValue}
                        onChange={(e) => setRunValue(e.target.value)}
                        required
                        className="mt-1.5"
                        data-testid="qc-run-value"
                      />
                    </div>
                    <div>
                      <Label htmlFor="run-date">Date</Label>
                      <Input
                        id="run-date"
                        type="date"
                        value={runDate}
                        onChange={(e) => setRunDate(e.target.value)}
                        className="mt-1.5"
                        data-testid="qc-run-date"
                      />
                    </div>
                    <Button
                      type="submit"
                      className="w-full bg-indigo-600 hover:bg-indigo-700"
                      disabled={loggingRun || !selectedId}
                      data-testid="log-run-btn"
                    >
                      {loggingRun ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Logging...
                        </>
                      ) : (
                        'Log Run'
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* Violations */}
            <Card className={`border border-slate-200 ${canLogRuns ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Rule Violations</CardTitle>
              </CardHeader>
              <CardContent>
                {violatedRuns.length === 0 ? (
                  <p className="text-sm text-slate-500 py-8 text-center">
                    No rule violations for this control.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200">
                          <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                          <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Value</th>
                          <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Rules</th>
                        </tr>
                      </thead>
                      <tbody>
                        {violatedRuns.map((r, i) => (
                          <tr key={r.id || i} className="border-b border-slate-100 hover:bg-slate-50/50">
                            <td className="px-4 py-2.5 text-sm text-slate-600">{formatDate(r.date)}</td>
                            <td className="px-4 py-2.5 text-sm font-medium text-slate-900">
                              {r.measured_value ?? r.value}
                            </td>
                            <td className="px-4 py-2.5">
                              <div className="flex flex-wrap gap-1">
                                {(r.violations || []).map((rule) => (
                                  <Badge
                                    key={rule}
                                    className={
                                      SEVERE_RULES.includes(rule)
                                        ? 'bg-rose-100 text-rose-700'
                                        : 'bg-amber-100 text-amber-700'
                                    }
                                  >
                                    {rule}
                                  </Badge>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* Add/Edit control dialog */}
      <Dialog open={controlDialogOpen} onOpenChange={setControlDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingControl ? 'Edit QC Control' : 'Add QC Control'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveControl} className="space-y-4 mt-4">
            <div>
              <Label htmlFor="qc-name">Name *</Label>
              <Input
                id="qc-name"
                value={controlForm.name}
                onChange={(e) => setControlForm({ ...controlForm, name: e.target.value })}
                required
                className="mt-1.5"
                placeholder="e.g. Glucose Control Level 1"
                data-testid="qc-name-input"
              />
            </div>
            <div>
              <Label>Test (optional)</Label>
              <Select
                value={controlForm.test_id || 'none'}
                onValueChange={(v) => setControlForm({ ...controlForm, test_id: v === 'none' ? '' : v })}
              >
                <SelectTrigger className="mt-1.5" data-testid="qc-test-select">
                  <SelectValue placeholder="Link to a test" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No linked test</SelectItem>
                  {tests.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name} ({t.test_code || t.code || ''})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="qc-mean">Target Mean *</Label>
                <Input
                  id="qc-mean"
                  type="number"
                  step="any"
                  value={controlForm.target_mean}
                  onChange={(e) => setControlForm({ ...controlForm, target_mean: e.target.value })}
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="qc-sd">SD *</Label>
                <Input
                  id="qc-sd"
                  type="number"
                  step="any"
                  min="0"
                  value={controlForm.sd}
                  onChange={(e) => setControlForm({ ...controlForm, sd: e.target.value })}
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="qc-unit">Unit</Label>
                <Input
                  id="qc-unit"
                  value={controlForm.unit}
                  onChange={(e) => setControlForm({ ...controlForm, unit: e.target.value })}
                  className="mt-1.5"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setControlDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-700"
                disabled={savingControl}
                data-testid="save-control-btn"
              >
                {savingControl ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : editingControl ? (
                  'Save Changes'
                ) : (
                  'Add Control'
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete control confirm */}
      <Dialog open={!!deleteControlId} onOpenChange={(open) => !open && setDeleteControlId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-heading">Delete Control</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600 mt-2">
            Delete this QC control and all its runs? This cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setDeleteControlId(null)}>
              Cancel
            </Button>
            <Button className="bg-rose-600 hover:bg-rose-700" onClick={handleDeleteControl}>
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
