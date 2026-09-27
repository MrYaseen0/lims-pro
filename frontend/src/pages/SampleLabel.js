import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { sampleAPI, getErrorMessage } from '../lib/api';
import { formatDateTime } from '../lib/utils';
import { Loader2, Printer, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Printable sample barcode label.
 * Rendered OUTSIDE the Layout chrome (see App.js) with minimal markup.
 * Print CSS in index.css hides the toolbar and sizes the page to 4in x 2in.
 */
export default function SampleLabel() {
  const { id } = useParams();
  const [sample, setSample] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // No GET /samples/{id} endpoint exists — fetch the list and find by id.
        const response = await sampleAPI.getAll({ page: 1, page_size: 100 });
        const found = (response.data || []).find((s) => s.id === id);
        if (!cancelled) {
          if (found) {
            setSample(found);
          } else {
            toast.error('Sample not found');
          }
        }
      } catch (error) {
        if (!cancelled) toast.error(getErrorMessage(error, 'Failed to load sample'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!sample) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-white">
        <p className="text-slate-600">Sample not found.</p>
        <Link to="/samples" className="text-indigo-600 hover:underline text-sm">
          Back to samples
        </Link>
      </div>
    );
  }

  return (
    <div className="label-print-page min-h-screen bg-slate-100 p-6 flex flex-col items-center">
      {/* Toolbar — hidden when printing */}
      <div className="no-print w-full max-w-md flex items-center justify-between mb-6">
        <Link
          to="/samples"
          className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to samples
        </Link>
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
          data-testid="print-label-btn"
        >
          <Printer className="w-4 h-4" />
          Print
        </button>
      </div>

      {/* Label */}
      <div
        className="bg-white border-2 border-slate-900 rounded p-4 w-full max-w-md"
        data-testid="sample-label"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">Patient</p>
            <p className="text-lg font-bold text-slate-900 leading-tight truncate">
              {sample.patient_name || '-'}
            </p>
            <p className="text-xs text-slate-600 mt-0.5">
              Sample: <span className="font-mono font-semibold text-slate-900">{sample.sample_id}</span>
            </p>
            <p className="text-xs text-slate-600 capitalize">
              {sample.sample_type}
              {sample.order_number ? ` • Order ${sample.order_number}` : ''}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">Collected</p>
            <p className="text-xs font-medium text-slate-900">
              {sample.collection_time ? formatDateTime(sample.collection_time) : '-'}
            </p>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t-2 border-dashed border-slate-300 text-center">
          <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Barcode</p>
          <p className="font-mono text-3xl font-bold tracking-widest text-slate-900 break-all">
            {sample.barcode || sample.sample_id}
          </p>
        </div>
      </div>

      <p className="no-print text-xs text-slate-400 mt-4">
        Print on a 4" × 2" label printer for best results.
      </p>
    </div>
  );
}
