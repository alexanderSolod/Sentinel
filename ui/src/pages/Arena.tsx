import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Users, ThumbsUp, ThumbsDown, HelpCircle } from 'lucide-react';
import { useIndex, useSubmitVote, useCaseDetail } from '../api/hooks.ts';
import type { VoteValue, SentinelCase } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import ScoreBar from '../components/ui/ScoreBar.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import VoteDonut from '../components/charts/VoteDonut.tsx';
import { formatRelativeTime } from '../lib/formatters.ts';
import { SCORE_DEFINITIONS } from '../lib/scoreDefinitions.ts';

// ---------------------------------------------------------------------------
// Vote button config
// ---------------------------------------------------------------------------

const VOTE_BUTTONS: Array<{
  value: VoteValue;
  label: string;
  icon: typeof ThumbsUp;
  color: string;
  borderColor: string;
}> = [
  {
    value: 'agree',
    label: 'Agree',
    icon: ThumbsUp,
    color: '#00FF88',
    borderColor: '#00FF88',
  },
  {
    value: 'disagree',
    label: 'Disagree',
    icon: ThumbsDown,
    color: '#FF2D55',
    borderColor: '#FF2D55',
  },
  {
    value: 'uncertain',
    label: 'Uncertain',
    icon: HelpCircle,
    color: '#FFB800',
    borderColor: '#FFB800',
  },
];

// ---------------------------------------------------------------------------
// Arena page
// ---------------------------------------------------------------------------

export default function Arena() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [confirmationMsg, setConfirmationMsg] = useState<string | null>(null);

  // Load ALL cases (not just UNDER_REVIEW)
  const {
    data: casesPage,
    loading: casesLoading,
    error: casesError,
  } = useIndex({ limit: 100 });

  const cases = casesPage?.items ?? [];

  // Auto-select first case when loaded
  const activeCaseId = selectedCaseId ?? cases[0]?.case_id;

  // Load full case detail
  const {
    data: detail,
    loading: detailLoading,
    refetch: refetchDetail,
  } = useCaseDetail(activeCaseId);

  // Vote mutation
  const { submit, loading: voteLoading, error: voteError } = useSubmitVote();

  const caseData = detail?.case ?? null;
  const anomaly = detail?.anomaly ?? null;

  // Handle vote
  const handleVote = useCallback(
    async (vote: VoteValue) => {
      if (!activeCaseId) return;
      setConfirmationMsg(null);
      try {
        await submit({ case_id: activeCaseId, vote });
        setConfirmationMsg(`Vote "${vote}" submitted successfully.`);
        refetchDetail();
      } catch {
        // error is surfaced via voteError
      }
    },
    [activeCaseId, submit, refetchDetail],
  );

  // ---------------------------------------------------------------------------
  // Empty state
  // ---------------------------------------------------------------------------

  if (!casesLoading && !casesError && cases.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <p className="overline mb-1">// ARENA</p>
          <h1 className="font-display text-2xl font-bold text-text-primary flex items-center gap-2">
            <Users size={24} className="text-accent" />
            Arena
          </h1>
        </div>
        <Card>
          <div className="py-20 text-center">
            <Users size={48} className="mx-auto mb-4 text-text-tertiary" />
            <p className="font-mono text-sm text-text-tertiary">
              No cases awaiting review
            </p>
          </div>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// ARENA</p>
        <h1 className="font-display text-2xl font-bold text-text-primary flex items-center gap-2">
          <Users size={24} className="text-accent" />
          Arena
          {cases.length > 0 && (
            <span className="font-mono text-xs text-text-tertiary font-normal ml-2">
              {cases.length} cases
            </span>
          )}
        </h1>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* ---- Case List (left column) ---- */}
        <div className="xl:col-span-1 space-y-2" style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
          <p className="overline mb-2 sticky top-0 bg-bg-primary py-1 z-10">ALL CASES</p>
          {casesLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg mb-2" />
            ))
          ) : (
            cases.map((c: SentinelCase) => {
              const isActive = c.case_id === activeCaseId;
              return (
                <motion.div
                  key={c.case_id}
                  onClick={() => { setSelectedCaseId(c.case_id); setConfirmationMsg(null); }}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  style={{
                    padding: '10px 12px',
                    background: isActive ? '#ff6b0012' : '#0a0a0a',
                    border: isActive ? '1px solid #ff8c00' : '1px solid #ffffff0a',
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    if (!isActive) e.currentTarget.style.borderColor = '#ff6b0055';
                  }}
                  onMouseLeave={e => {
                    if (!isActive) e.currentTarget.style.borderColor = '#ffffff0a';
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <ClassificationBadge classification={c.classification} />
                    <span className="font-mono text-[10px] text-text-tertiary uppercase">
                      {c.status}
                    </span>
                    {c.vote_count > 0 && (
                      <span className="font-mono text-[10px] text-accent ml-auto">
                        {c.vote_count} vote{c.vote_count !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-xs text-text-primary leading-snug" style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {c.market_name ?? c.case_id}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="font-mono text-[10px] text-text-tertiary">
                      BSS {c.bss_score}
                    </span>
                    <span className="font-mono text-[10px] text-text-tertiary">
                      PES {c.pes_score}
                    </span>
                    {c.temporal_gap_hours != null && (
                      <span className="font-mono text-[10px] text-text-tertiary">
                        {c.temporal_gap_hours.toFixed(1)}h gap
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })
          )}
        </div>

        {/* ---- Case Detail + Voting (right columns) ---- */}
        <div className="xl:col-span-2 space-y-6">
          {/* ---- Case Summary Card ---- */}
          <Card title="CASE SUMMARY">
            {detailLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : !caseData ? (
              <p className="font-mono text-sm text-text-tertiary">Select a case to review</p>
            ) : (
              <div className="space-y-5">
                {/* Market name + badge */}
                <div className="flex items-start gap-3 flex-wrap">
                  <ClassificationBadge classification={caseData.classification} />
                  <h2 className="font-mono text-sm text-text-primary flex-1">
                    {caseData.market_name ?? 'Unknown Market'}
                  </h2>
                  <span className="font-mono text-xs text-text-tertiary shrink-0">
                    {formatRelativeTime(caseData.created_at)}
                  </span>
                </div>

                {/* Scores */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                  <ScoreBar label="BSS" score={caseData.bss_score} tooltip={SCORE_DEFINITIONS.BSS.long} />
                  <ScoreBar label="PES" score={caseData.pes_score} tooltip={SCORE_DEFINITIONS.PES.long} />
                </div>

                {/* AI Analysis */}
                {(caseData.xai_summary || anomaly?.xai_narrative) && (
                  <div className="border border-border-subtle rounded-lg p-4 bg-bg-tertiary">
                    <p className="overline mb-2">AI ANALYSIS</p>
                    <p className="font-mono text-xs text-text-secondary leading-relaxed">
                      {caseData.xai_summary ?? anomaly?.xai_narrative}
                    </p>
                  </div>
                )}

                {/* OSINT signal count */}
                {caseData.evidence?.osint_signals &&
                  caseData.evidence.osint_signals.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="overline">OSINT SIGNALS</span>
                      <span className="font-mono text-sm font-semibold text-accent">
                        {caseData.evidence.osint_signals.length}
                      </span>
                    </div>
                  )}

                {/* Temporal gap */}
                {caseData.temporal_gap_hours != null && (
                  <div className="flex items-center gap-2">
                    <span className="overline">TEMPORAL GAP</span>
                    <span className="font-mono text-sm text-text-secondary">
                      {caseData.temporal_gap_hours.toFixed(1)}h before news
                    </span>
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* ---- Voting + Consensus Row ---- */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Voting Card */}
            <Card title="CAST YOUR VOTE">
              <div className="space-y-4">
                {/* Vote buttons */}
                <div className="flex gap-3">
                  {VOTE_BUTTONS.map((btn) => {
                    const Icon = btn.icon;
                    return (
                      <motion.button
                        key={btn.value}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        disabled={voteLoading || !activeCaseId}
                        onClick={() => handleVote(btn.value)}
                        className="flex-1 flex flex-col items-center justify-center gap-2 rounded-lg border-2 bg-transparent transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        style={{
                          height: 60,
                          borderColor: `${btn.borderColor}33`,
                          color: btn.color,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = btn.borderColor;
                          e.currentTarget.style.backgroundColor = `${btn.color}0A`;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = `${btn.borderColor}33`;
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <Icon size={20} />
                        <span className="font-mono text-[11px] font-semibold uppercase tracking-wider">
                          {btn.label}
                        </span>
                      </motion.button>
                    );
                  })}
                </div>

                {/* Status messages */}
                {voteLoading && (
                  <p className="font-mono text-xs text-text-tertiary text-center">
                    Submitting vote...
                  </p>
                )}
                {voteError && (
                  <p className="font-mono text-xs text-threat-critical text-center">
                    Error: {voteError}
                  </p>
                )}
                {confirmationMsg && !voteError && (
                  <motion.p
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="font-mono text-xs text-status-online text-center"
                  >
                    {confirmationMsg}
                  </motion.p>
                )}
              </div>
            </Card>

            {/* Consensus Card */}
            <Card title="VOTE CONSENSUS">
              {detailLoading ? (
                <div className="flex justify-center py-6">
                  <Skeleton className="h-[180px] w-[180px] rounded-full" />
                </div>
              ) : !caseData ? (
                <p className="font-mono text-xs text-text-tertiary text-center py-8">
                  Select a case
                </p>
              ) : (
                <div className="flex flex-col items-center py-2">
                  <VoteDonut
                    votes_agree={caseData.votes_agree}
                    votes_disagree={caseData.votes_disagree}
                    votes_uncertain={caseData.votes_uncertain}
                  />
                  <p className="mt-3 font-mono text-xs text-text-tertiary">
                    Total votes: {caseData.vote_count}
                  </p>
                  {caseData.consensus_score != null && (
                    <p className="mt-1 font-mono text-xs text-text-secondary">
                      Consensus score:{' '}
                      <span className="text-accent font-semibold">
                        {caseData.consensus_score.toFixed(1)}
                      </span>
                    </p>
                  )}
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>

      {/* ---- Error display ---- */}
      {casesError && (
        <Card>
          <p className="font-mono text-sm text-threat-critical text-center py-4">
            Failed to load cases: {casesError}
          </p>
        </Card>
      )}
    </div>
  );
}
