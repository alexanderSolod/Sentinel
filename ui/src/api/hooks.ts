import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from './client.ts';
import type {
  Anomaly,
  CaseDetailResponse,
  EvidencePacket,
  HealthResponse,
  MetricsResponse,
  PaginatedResponse,
  SentinelCase,
  VoteRequest,
} from './types.ts';

// ---------------------------------------------------------------------------
// Generic data-fetching hook
// ---------------------------------------------------------------------------

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useApi<T>(
  url: string | null,
  options?: { refreshInterval?: number },
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(url !== null);
  const [error, setError] = useState<string | null>(null);

  // Track the latest url in a ref so the refetch callback is always current.
  const urlRef = useRef(url);
  urlRef.current = url;

  // Monotonically-increasing request id to discard stale responses.
  const seqRef = useRef(0);

  const fetchData = useCallback(() => {
    const currentUrl = urlRef.current;
    if (currentUrl === null) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const seq = ++seqRef.current;
    setLoading(true);
    setError(null);

    apiFetch<T>(currentUrl)
      .then((result) => {
        if (seq === seqRef.current) {
          setData(result);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (seq === seqRef.current) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (seq === seqRef.current) {
          setLoading(false);
        }
      });
  }, []);

  // Fetch whenever the url changes.
  useEffect(() => {
    fetchData();
  }, [url, fetchData]);

  // Optional polling.
  useEffect(() => {
    if (url === null || !options?.refreshInterval) return;

    const id = setInterval(fetchData, options.refreshInterval);
    return () => clearInterval(id);
  }, [url, options?.refreshInterval, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// ---------------------------------------------------------------------------
// Query-string builder helper
// ---------------------------------------------------------------------------

function buildQuery(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      sp.set(key, String(value));
    }
  }
  const qs = sp.toString();
  return qs ? `?${qs}` : '';
}

// ---------------------------------------------------------------------------
// Domain-specific hooks
// ---------------------------------------------------------------------------

export function useHealth() {
  return useApi<HealthResponse>('/api/health');
}

export function useAnomalies(params?: {
  classification?: string;
  limit?: number;
  offset?: number;
}) {
  const url = `/api/anomalies${buildQuery({
    classification: params?.classification,
    limit: params?.limit,
    offset: params?.offset,
  })}`;
  return useApi<PaginatedResponse<Anomaly>>(url);
}

export function useCaseDetail(caseId: string | undefined) {
  return useApi<CaseDetailResponse>(caseId ? `/api/cases/${caseId}` : null);
}

export function useIndex(params?: {
  classification?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const url = `/api/index${buildQuery({
    classification: params?.classification,
    status: params?.status,
    search: params?.search,
    limit: params?.limit,
    offset: params?.offset,
  })}`;
  return useApi<PaginatedResponse<SentinelCase>>(url);
}

export function useEvidence(params?: { limit?: number; offset?: number }) {
  const url = `/api/evidence${buildQuery({
    limit: params?.limit,
    offset: params?.offset,
  })}`;
  return useApi<PaginatedResponse<EvidencePacket>>(url);
}

export function useMetrics() {
  return useApi<MetricsResponse>('/api/metrics');
}

// ---------------------------------------------------------------------------
// Mutation hook – submit a vote
// ---------------------------------------------------------------------------

interface UseSubmitVoteResult {
  submit: (req: VoteRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function useSubmitVote(): UseSubmitVoteResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (req: VoteRequest): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      await apiFetch<unknown>('/api/vote', {
        method: 'POST',
        body: JSON.stringify(req),
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { submit, loading, error };
}
