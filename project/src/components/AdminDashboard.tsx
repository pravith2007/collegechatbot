import React, { useState, useEffect } from 'react';
import { 
  RefreshCw, Clock, Database, AlertTriangle, CheckCircle, 
  Settings, Key, ExternalLink, ShieldCheck, FileText, X, ArrowLeft
} from 'lucide-react';

interface SyncState {
  status: 'idle' | 'running' | 'completed' | 'error';
  last_successful_sync: string | null;
  next_scheduled_sync: string | null;
  interval_minutes: number;
  pages_checked: number;
  pages_changed: number;
  pages_failed: number;
  total_chunks: number;
  last_error: string | null;
}

interface SourceDoc {
  url: string;
  title: string;
  content_hash: string;
  retrieved_at: string;
  chunks_count: number;
  doc_type: string;
}

interface SyncHistoryItem {
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  manual: boolean;
  pages_checked: number;
  pages_changed: number;
  pages_new: number;
  pages_unchanged: number;
  pages_failed: number;
  status: string;
  error?: string | null;
}

interface AdminDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl?: string;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ 
  isOpen, 
  onClose,
  apiBaseUrl = "http://localhost:8000"
}) => {
  const [adminKey, setAdminKey] = useState<string>(() => sessionStorage.getItem('kec_admin_key') || 'kec_admin_secure_2026');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string>('');
  
  const [syncState, setSyncState] = useState<SyncState | null>(null);
  const [totalSources, setTotalSources] = useState<number>(0);
  const [sources, setSources] = useState<SourceDoc[]>([]);
  const [history, setHistory] = useState<SyncHistoryItem[]>([]);
  
  const [intervalInput, setIntervalInput] = useState<number>(60);
  const [isUpdatingInterval, setIsUpdatingInterval] = useState<boolean>(false);
  const [isTriggeringSync, setIsTriggeringSync] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Attempt login or verification
  const verifyAndFetchData = async (keyToUse: string) => {
    setAuthError('');
    try {
      const res = await fetch(`${apiBaseUrl}/api/admin/sync/status`, {
        headers: {
          'X-Admin-Key': keyToUse
        }
      });

      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Invalid Administrator API Key. Access denied.');
        }
        throw new Error(`Server returned error status ${res.status}`);
      }

      const data = await res.json();
      setSyncState(data.sync_state);
      setTotalSources(data.total_registered_sources || 0);
      setHistory(data.history || []);
      if (data.sync_state?.interval_minutes) {
        setIntervalInput(data.sync_state.interval_minutes);
      }
      setIsAuthenticated(true);
      sessionStorage.setItem('kec_admin_key', keyToUse);

      // Fetch sources list
      fetchSources(keyToUse);
    } catch (err: any) {
      setIsAuthenticated(false);
      setAuthError(err.message || 'Failed to connect to backend service.');
    }
  };

  const fetchSources = async (keyToUse: string) => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/admin/sources?limit=50`, {
        headers: { 'X-Admin-Key': keyToUse }
      });
      if (res.ok) {
        const data = await res.json();
        setSources(data.sources || []);
      }
    } catch (e) {
      console.error('Failed to fetch sources:', e);
    }
  };

  useEffect(() => {
    if (isOpen && adminKey) {
      verifyAndFetchData(adminKey);
    }
  }, [isOpen]);

  // Polling while synchronization is running
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isOpen && isAuthenticated && syncState?.status === 'running') {
      timer = setInterval(() => {
        verifyAndFetchData(adminKey);
      }, 3000);
    }
    return () => clearInterval(timer);
  }, [isOpen, isAuthenticated, syncState?.status]);

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey.trim()) {
      setAuthError('Please enter an Administrator API key.');
      return;
    }
    verifyAndFetchData(adminKey.trim());
  };

  const handleTriggerSync = async () => {
    setIsTriggeringSync(true);
    setNotification(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/admin/sync/trigger`, {
        method: 'POST',
        headers: { 'X-Admin-Key': adminKey }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({ type: 'success', text: 'Synchronization started in background!' });
        verifyAndFetchData(adminKey);
      } else {
        setNotification({ type: 'error', text: data.message || 'Could not start synchronization.' });
      }
    } catch (err: any) {
      setNotification({ type: 'error', text: err.message || 'Failed to communicate with backend.' });
    } finally {
      setIsTriggeringSync(false);
    }
  };

  const handleUpdateInterval = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingInterval(true);
    setNotification(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/admin/sync/schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey
        },
        body: JSON.stringify({ interval_minutes: Number(intervalInput) })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({ type: 'success', text: `Sync interval successfully updated to ${intervalInput} minutes.` });
        verifyAndFetchData(adminKey);
      } else {
        setNotification({ type: 'error', text: data.detail || 'Failed to update schedule.' });
      }
    } catch (err: any) {
      setNotification({ type: 'error', text: err.message || 'Failed to update schedule.' });
    } finally {
      setIsUpdatingInterval(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-100">
        
        {/* Top Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">KEC Knowledge Base Synchronization</h2>
              <p className="text-xs text-slate-400">Automated Web Scraper & ChromaDB RAG Administration</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Auth Barrier Screen */}
        {!isAuthenticated ? (
          <div className="p-8 max-w-md mx-auto my-auto text-center w-full">
            <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Key className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Administrator Authentication</h3>
            <p className="text-sm text-gray-500 mb-6">
              Please enter your administrator key to access scraper controls and synchronization metrics.
            </p>

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <input
                  type="password"
                  value={adminKey}
                  onChange={(e) => setAdminKey(e.target.value)}
                  placeholder="Enter Administrator API Key"
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                />
              </div>

              {authError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-xl text-xs flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-sm transition shadow-md"
              >
                Authenticate & Access Dashboard
              </button>
            </form>
          </div>
        ) : (
          /* Main Dashboard Content */
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
            
            {/* Notification alert */}
            {notification && (
              <div className={`p-4 rounded-xl text-sm flex items-center justify-between ${
                notification.type === 'success' 
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}>
                <div className="flex items-center space-x-2">
                  {notification.type === 'success' ? (
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-600" />
                  )}
                  <span>{notification.text}</span>
                </div>
                <button onClick={() => setNotification(null)} className="text-xs font-semibold underline">
                  Dismiss
                </button>
              </div>
            )}

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-between">
                  <span>Current Status</span>
                  <span className={`inline-block w-2.5 h-2.5 rounded-full ${
                    syncState?.status === 'running' ? 'bg-amber-500 animate-pulse' :
                    syncState?.status === 'error' ? 'bg-rose-500' : 'bg-emerald-500'
                  }`}></span>
                </div>
                <div className="text-lg font-bold text-slate-900 capitalize">
                  {syncState?.status || 'Idle'}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {syncState?.status === 'running' ? 'Sync in progress...' : 'Ready for queries'}
                </div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                  Indexed Sources
                </div>
                <div className="text-2xl font-bold text-blue-600">
                  {totalSources}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Verified HTML & PDF documents
                </div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                  Total Vector Chunks
                </div>
                <div className="text-2xl font-bold text-indigo-600">
                  {syncState?.total_chunks || 0}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Stored in Persistent ChromaDB
                </div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                  Pages Changed (Last Run)
                </div>
                <div className="text-2xl font-bold text-amber-600">
                  {syncState?.pages_changed || 0}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {syncState?.pages_failed ? `${syncState.pages_failed} failed requests` : '0 errors'}
                </div>
              </div>
            </div>

            {/* Controls Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Trigger Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                <div>
                  <h4 className="font-semibold text-slate-900 mb-1 flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4 text-blue-600" />
                    <span>On-Demand Web Synchronization</span>
                  </h4>
                  <p className="text-xs text-slate-500 mb-4">
                    Crawls official public pages starting from kongu.ac.in, runs SHA-256 change detection, and updates ChromaDB vector embeddings atomically.
                  </p>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                  <div className="text-xs text-slate-500">
                    Last Sync: {syncState?.last_successful_sync 
                      ? new Date(syncState.last_successful_sync).toLocaleTimeString() 
                      : 'Not yet recorded'}
                  </div>
                  <button
                    onClick={handleTriggerSync}
                    disabled={isTriggeringSync || syncState?.status === 'running'}
                    className={`px-4 py-2.5 rounded-xl text-sm font-medium text-white flex items-center space-x-2 transition shadow ${
                      isTriggeringSync || syncState?.status === 'running'
                        ? 'bg-slate-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    <RefreshCw className={`w-4 h-4 ${syncState?.status === 'running' ? 'animate-spin' : ''}`} />
                    <span>{syncState?.status === 'running' ? 'Syncing...' : 'Sync Now'}</span>
                  </button>
                </div>
              </div>

              {/* Schedule Configuration Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h4 className="font-semibold text-slate-900 mb-1 flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-indigo-600" />
                  <span>Automatic Schedule Configuration</span>
                </h4>
                <p className="text-xs text-slate-500 mb-3">
                  Configures the APScheduler interval running in the Python backend service.
                </p>

                <form onSubmit={handleUpdateInterval} className="flex items-center space-x-3">
                  <div className="flex-1">
                    <label className="text-[11px] uppercase tracking-wide text-slate-400 block mb-1">
                      Interval (Minutes)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={1440}
                      value={intervalInput}
                      onChange={(e) => setIntervalInput(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isUpdatingInterval}
                    className="self-end px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg transition"
                  >
                    {isUpdatingInterval ? 'Saving...' : 'Save Interval'}
                  </button>
                </form>

                <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
                  <span>Next scheduled sync:</span>
                  <span className="font-semibold text-slate-700">
                    {syncState?.next_scheduled_sync 
                      ? new Date(syncState.next_scheduled_sync).toLocaleTimeString() 
                      : 'Every ' + (syncState?.interval_minutes || 60) + ' mins'}
                  </span>
                </div>
              </div>
            </div>

            {/* Registered Sources Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center space-x-2">
                  <Database className="w-4 h-4 text-slate-700" />
                  <h4 className="font-semibold text-slate-900 text-sm">Indexed Knowledge Sources ({sources.length})</h4>
                </div>
                <button 
                  onClick={() => fetchSources(adminKey)}
                  className="text-xs text-blue-600 hover:underline flex items-center space-x-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Refresh List</span>
                </button>
              </div>

              <div className="overflow-x-auto max-h-64">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-100 text-slate-700 font-semibold uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="px-4 py-2.5">Title & Source URL</th>
                      <th className="px-4 py-2.5">Content Hash (SHA-256)</th>
                      <th className="px-4 py-2.5">Chunks</th>
                      <th className="px-4 py-2.5">Type</th>
                      <th className="px-4 py-2.5">Last Retrieved</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sources.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                          No sources registered yet. Click "Sync Now" to start indexing official pages.
                        </td>
                      </tr>
                    ) : (
                      sources.map((src, i) => (
                        <tr key={i} className="hover:bg-slate-50 transition">
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-900">{src.title}</div>
                            <a 
                              href={src.url} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-blue-600 hover:underline flex items-center space-x-1 mt-0.5"
                            >
                              <span className="truncate max-w-xs">{src.url}</span>
                              <ExternalLink className="w-3 h-3 flex-shrink-0" />
                            </a>
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                            {src.content_hash ? src.content_hash.slice(0, 16) + '...' : 'N/A'}
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700">
                            {src.chunks_count}
                          </td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-800 text-[10px] uppercase font-bold">
                              {src.doc_type || 'html'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500">
                            {src.retrieved_at ? new Date(src.retrieved_at).toLocaleString() : 'Pre-seeded'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Sync History Logs */}
            {history.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                <h4 className="font-semibold text-slate-900 text-sm mb-3 flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-slate-600" />
                  <span>Recent Synchronization Logs</span>
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                  {history.map((h, idx) => (
                    <div 
                      key={idx}
                      className="p-2.5 rounded-lg border border-slate-100 bg-slate-50 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center space-x-2">
                        <span className={`w-2 h-2 rounded-full ${h.status === 'completed' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
                        <span className="font-medium text-slate-800">
                          {new Date(h.start_time).toLocaleString()}
                        </span>
                        <span className="text-slate-400">({h.manual ? 'Manual' : 'Scheduled'})</span>
                      </div>
                      <div className="flex items-center space-x-3 text-slate-500">
                        <span>Checked: {h.pages_checked}</span>
                        <span className="text-emerald-600 font-semibold">New/Changed: {h.pages_new + h.pages_changed}</span>
                        {h.duration_seconds && <span>{h.duration_seconds}s</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}

        {/* Footer */}
        <div className="bg-white px-6 py-3 border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            KEC Automated Knowledge Engine • Backend: <span className="font-mono text-slate-600">{apiBaseUrl}</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-xl transition"
          >
            Close Dashboard
          </button>
        </div>

      </div>
    </div>
  );
};

export default AdminDashboard;
