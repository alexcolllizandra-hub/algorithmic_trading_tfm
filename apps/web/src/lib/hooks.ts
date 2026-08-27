"use client";

import useSWR from "swr";

import { fetcher, qs } from "@/lib/api";
import type {
  ArtifactsResponse,
  CandidatesResponse,
  ComparisonResponse,
  EdaFiguresResponse,
  EdaSummaryResponse,
  EquityResponse,
  FoldsResponse,
  HealthResponse,
  MarketCoverageResponse,
  MethodologyResponse,
  OhlcvResponse,
  PerformanceResponse,
  ResearchSummaryResponse,
  RunDetailResponse,
  RunListResponse,
  RunValidityResponse,
  SearchAnalyticsResponse,
  StudyFamilyDetail,
  StudyHoldoutResponse,
  StudyRegimesResponse,
  StudySummaryResponse,
  TimelineResponse,
  TradesResponse,
} from "@/lib/api-types";

const opts = { revalidateOnFocus: false, shouldRetryOnError: false };

export function useHealth() {
  return useSWR<HealthResponse>("/health", fetcher, opts);
}

export function useRuns(params: { family?: string; kind?: string; algorithm?: string } = {}) {
  return useSWR<RunListResponse>(`/runs${qs({ limit: 200, ...params })}`, fetcher, opts);
}

export function useRun(runId: string | null) {
  return useSWR<RunDetailResponse>(runId ? `/runs/${runId}` : null, fetcher, opts);
}

export function useComparison(runId: string | null) {
  return useSWR<ComparisonResponse>(runId ? `/runs/${runId}/comparison` : null, fetcher, opts);
}

export function useCandidates(runId: string | null, method: string, limit = 50) {
  return useSWR<CandidatesResponse>(
    runId ? `/runs/${runId}/candidates${qs({ method, limit })}` : null,
    fetcher,
    opts
  );
}

export function useFolds(runId: string | null) {
  return useSWR<FoldsResponse>(runId ? `/runs/${runId}/folds` : null, fetcher, opts);
}

export function useAnalytics(runId: string | null) {
  return useSWR<SearchAnalyticsResponse>(runId ? `/runs/${runId}/analytics` : null, fetcher, opts);
}

export function usePerformance(runId: string | null) {
  return useSWR<PerformanceResponse>(runId ? `/runs/${runId}/performance` : null, fetcher, opts);
}

/** Equity series; default limit 10000 or explicit override from summary.n_points_total. */
export function useEquity(runId: string | null, method: string, fold: number, limit?: number) {
  const effectiveLimit = limit ?? 10000;
  return useSWR<EquityResponse>(
    runId ? `/runs/${runId}/equity${qs({ method, fold, limit: effectiveLimit })}` : null,
    fetcher,
    opts
  );
}

export function useTrades(
  runId: string | null,
  method: string,
  fold: number,
  limit = 25,
  offset = 0
) {
  return useSWR<TradesResponse>(
    runId ? `/runs/${runId}/trades${qs({ method, fold, limit, offset })}` : null,
    fetcher,
    opts
  );
}

export function useArtifacts(runId: string | null) {
  return useSWR<ArtifactsResponse>(runId ? `/runs/${runId}/artifacts` : null, fetcher, opts);
}

export function useMarketCoverage() {
  return useSWR<MarketCoverageResponse>("/market/coverage", fetcher, opts);
}

export function useOhlcv(symbol: string, timeframe: string, limit = 1500) {
  return useSWR<OhlcvResponse>(`/market/ohlcv${qs({ symbol, timeframe, limit })}`, fetcher, opts);
}

export function useResearchSummary() {
  return useSWR<ResearchSummaryResponse>("/research/summary", fetcher, opts);
}

export function useTimeline(runId: string | null) {
  return useSWR<TimelineResponse>(
    runId ? `/research/timeline${qs({ run_id: runId })}` : null,
    fetcher,
    opts
  );
}

export function useValidity(runId: string | null) {
  return useSWR<RunValidityResponse>(runId ? `/runs/${runId}/validity` : null, fetcher, opts);
}

export function useEdaSummary() {
  return useSWR<EdaSummaryResponse>("/eda/summary", fetcher, opts);
}

export function useEdaFigures(params: { key_only?: boolean; theme?: string; limit?: number } = {}) {
  const keyOnly =
    params.key_only === true ? "true" : params.key_only === false ? "false" : undefined;
  return useSWR<EdaFiguresResponse>(
    `/eda/figures${qs({ limit: params.limit ?? 200, key_only: keyOnly, theme: params.theme })}`,
    fetcher,
    opts
  );
}

export function useMethodology() {
  return useSWR<MethodologyResponse>("/methodology/features", fetcher, opts);
}

export function useStudySummary() {
  return useSWR<StudySummaryResponse>("/study/summary", fetcher, opts);
}

/** Family detail; `key` is `family|SYMBOL` and must be percent-encoded. */
export function useStudyFamily(key: string | null) {
  return useSWR<StudyFamilyDetail>(
    key ? `/study/families/${encodeURIComponent(key)}` : null,
    fetcher,
    opts
  );
}

export function useStudyRegimes() {
  return useSWR<StudyRegimesResponse>("/study/regimes", fetcher, opts);
}

export function useStudyHoldout() {
  return useSWR<StudyHoldoutResponse>("/study/holdout", fetcher, opts);
}
