import { useState, useEffect } from 'react';
import { reportAPI, testAPI, getErrorMessage } from '../lib/api';
import { formatDateTime } from '../lib/utils';
import { Loader2, Printer } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { toast } from 'sonner';

// Urdu label dictionary — system fonts only, no external downloads.
const URDU = {
  'Lab Report': 'لیب رپورٹ',
  'Patient Name': 'مریض کا نام',
  'Patient ID': 'مریض نمبر',
  'Age': 'عمر',
  'Gender': 'جنس',
  'Phone': 'فون',
  'Order ID': 'آرڈر نمبر',
  'Date': 'تاریخ',
  'Test': 'ٹیسٹ',
  'Result': 'نتیجہ',
  'Unit': 'یونٹ',
  'Reference Range': 'نارمل رینج',
  'Flag': 'علامت',
  'Abnormal': 'غیر معمولی',
  'Normal': 'نارمل',
  'Approved By': 'تصدیق کنندہ',
  'Generated On': 'جاری کرنے کی تاریخ',
  'years': 'سال',
  'Code': 'کوڈ',
};

const t = (key, urdu) => (urdu && URDU[key] ? URDU[key] : key);

const fmt = (v) => (v === null || v === undefined || v === '' ? '-' : String(v));

/**
 * Printable lab report preview with an English | اردو toggle.
 * The report body carries .lab-report-print so the print CSS in index.css
 * hides the app chrome when printing.
 */
export default function LabReportPreview({ orderId }) {
  const [report, setReport] = useState(null);
  const [rangeMap, setRangeMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [urdu, setUrdu] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await reportAPI.get(orderId);
        if (cancelled) return;
        setReport(response.data);
        // Pull reference ranges from the test catalog for the range column
        const tests = response.data?.order?.tests || [];
        const maps = {};
        await Promise.all(
          tests.map(async (test) => {
            if (!test.test_id) return;
            try {
              const res = await testAPI.getById(test.test_id);
              (res.data.reference_ranges || []).forEach((r) => {
                maps[`${test.test_id}:${r.parameter}`] = r;
              });
            } catch {
              // range column stays empty for this test
            }
          })
        );
        if (!cancelled) setRangeMap(maps);
      } catch (error) {
        if (!cancelled) toast.error(getErrorMessage(error, 'Failed to load report'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const handlePrint = () => {
    document.body.classList.add('print-lab-report');
    window.print();
    setTimeout(() => document.body.classList.remove('print-lab-report'), 500);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!report) return null;

  const { order, patient, lab_name, lab_address, lab_phone, generated_at } = report;
  const rtl = urdu;

  const resultRows = [];
  (order.tests || []).forEach((test) => {
    const result = test.result || {};
    const values = result.values || {};
    const flags = result.flags || {};
    if (values && typeof values === 'object' && Object.keys(values).length > 0) {
      Object.entries(values).forEach(([param, val]) => {
        const ref = rangeMap[`${test.test_id}:${param}`] || {};
        resultRows.push({
          testName: test.test_name,
          parameter: param,
          value: val,
          unit: ref.unit || '',
          range: ref.normal_range || '',
          flag: flags[param] || (result.is_abnormal ? 'A' : ''),
        });
      });
    } else {
      resultRows.push({
        testName: test.test_name,
        parameter: '',
        value: result.value ?? '',
        unit: result.unit ?? '',
        range: '',
        flag: result.is_abnormal ? 'A' : '',
      });
    }
  });

  return (
    <div>
      {/* Toolbar (screen only) */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div
          className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-1"
          data-testid="report-lang-toggle"
        >
          <button
            type="button"
            onClick={() => setUrdu(false)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              !urdu ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
            data-testid="report-lang-en"
          >
            English
          </button>
          <button
            type="button"
            onClick={() => setUrdu(true)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              urdu ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
            data-testid="report-lang-ur"
          >
            اردو
          </button>
        </div>
        <Button variant="outline" onClick={handlePrint} data-testid="print-report-btn">
          <Printer className="w-4 h-4 mr-2" />
          Print
        </Button>
      </div>

      {/* Printable report */}
      <Card className="lab-report-print border border-slate-200">
        <CardContent className="p-6 sm:p-8" dir={rtl ? 'rtl' : 'ltr'}>
          {/* Lab header */}
          <div className="text-center border-b-2 border-slate-900 pb-4 mb-6">
            <h1 className="text-2xl font-bold text-slate-900">{lab_name || 'LIMS.Pro Diagnostic Laboratory'}</h1>
            <p className="text-sm text-slate-600 mt-1">{lab_address}</p>
            {lab_phone && <p className="text-sm text-slate-600">{lab_phone}</p>}
            <p className="text-lg font-bold text-indigo-700 mt-3 tracking-wide">
              {t('Lab Report', rtl)}
            </p>
          </div>

          {/* Patient + order info */}
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 mb-6 text-sm">
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Patient Name', rtl)}:</span>
              <span className="text-slate-900">{fmt(patient?.name)}</span>
            </div>
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Patient ID', rtl)}:</span>
              <span className="text-slate-900 font-mono">{fmt(patient?.patient_id || patient?.id)}</span>
            </div>
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Age', rtl)}:</span>
              <span className="text-slate-900">
                {fmt(patient?.age)} {patient?.age ? t('years', rtl) : ''}
              </span>
            </div>
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Gender', rtl)}:</span>
              <span className="text-slate-900 capitalize">{fmt(patient?.gender)}</span>
            </div>
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Order ID', rtl)}:</span>
              <span className="text-slate-900 font-mono">{fmt(order?.order_id)}</span>
            </div>
            <div className="flex gap-2">
              <span className="font-semibold text-slate-700 min-w-[110px]">{t('Date', rtl)}:</span>
              <span className="text-slate-900">{order?.created_at ? formatDateTime(order.created_at) : '-'}</span>
            </div>
          </div>

          {/* Results table */}
          <table className="w-full mb-6 text-sm">
            <thead>
              <tr className="border-y-2 border-slate-900">
                <th className={`py-2.5 px-3 font-bold text-slate-900 ${rtl ? 'text-right' : 'text-left'}`}>
                  {t('Test', rtl)}
                </th>
                <th className={`py-2.5 px-3 font-bold text-slate-900 ${rtl ? 'text-right' : 'text-left'}`}>
                  {t('Result', rtl)}
                </th>
                <th className={`py-2.5 px-3 font-bold text-slate-900 ${rtl ? 'text-right' : 'text-left'}`}>
                  {t('Unit', rtl)}
                </th>
                <th className={`py-2.5 px-3 font-bold text-slate-900 ${rtl ? 'text-right' : 'text-left'}`}>
                  {t('Reference Range', rtl)}
                </th>
                <th className={`py-2.5 px-3 font-bold text-slate-900 ${rtl ? 'text-right' : 'text-left'}`}>
                  {t('Flag', rtl)}
                </th>
              </tr>
            </thead>
            <tbody>
              {resultRows.map((row, i) => (
                <tr key={i} className="border-b border-slate-200">
                  <td className="py-2.5 px-3 font-medium text-slate-900">
                    {row.testName}
                    {row.parameter && <span className="block text-xs text-slate-500">{row.parameter}</span>}
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{fmt(row.value)}</td>
                  <td className="py-2.5 px-3 text-slate-600">{fmt(row.unit)}</td>
                  <td className="py-2.5 px-3 text-slate-600">{fmt(row.range)}</td>
                  <td className="py-2.5 px-3">
                    {row.flag ? (
                      <span className="font-bold text-rose-700">{row.flag}</span>
                    ) : (
                      <span className="text-slate-500">{row.value !== '' ? t('Normal', rtl) : '-'}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Footer */}
          <div className="flex flex-col sm:flex-row justify-between gap-4 pt-4 border-t border-slate-200 text-sm">
            <div>
              <span className="font-semibold text-slate-700">{t('Generated On', rtl)}: </span>
              <span className="text-slate-600">{generated_at ? formatDateTime(generated_at) : '-'}</span>
            </div>
            <div className="text-slate-600">
              <span className="font-semibold text-slate-700">{t('Approved By', rtl)}: </span>
              {fmt(order?.tests?.map((tt) => tt.result?.approved_by_name).find(Boolean))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
