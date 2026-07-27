import { riskColor, riskTone } from '../constants'

const completenessColor = (score) =>
  score >= 85 ? '#15803d' : score >= 60 ? '#b45309' : '#b91c1c'

export function RootCauseList({ causes }) {
  if (!causes?.length) return null
  return (
    <ul className="rc-list">
      {causes.map((rc, index) => (
        <li key={index} className={(rc.likelihood ?? 'medium').toLowerCase()}>
          <div>{rc.cause}</div>
          <div className="meta">
            <span className="badge badge-neutral">{rc.likelihood ?? 'Medium'} likelihood</span>
            {rc.area && <span className="badge badge-neutral">{rc.area}</span>}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function CapaList({ actions }) {
  if (!actions?.length) return null
  const tone = { Correction: 'badge-risk', Corrective: 'badge-brand', Preventive: 'badge-ok' }
  return (
    <ul className="capa-list">
      {actions.map((item, index) => (
        <li key={index} className={(item.type ?? 'corrective').toLowerCase()}>
          <div>{item.action}</div>
          <div className="meta">
            <span className={`badge ${tone[item.type] ?? 'badge-neutral'}`}>{item.type}</span>
            <span className="badge badge-neutral">Owner: {item.owner}</span>
            <span className="badge badge-neutral">Due in {item.due_days} days</span>
          </div>
        </li>
      ))}
    </ul>
  )
}

/**
 * Renders one AI analysis payload. Shared by the intake screen and the
 * complaint drawer so both show identical insight formatting.
 */
export default function AIInsights({ analysis, onOpenDuplicate }) {
  if (!analysis) return null

  const {
    summary,
    risk_level: riskLevel,
    risk_score: riskScore,
    risk_rationale: riskRationale,
    regulatory_reportable: reportable,
    completeness_score: completeness,
    missing_fields: missing,
    completeness_notes: completenessNotes,
    duplicate_candidates: duplicates,
    root_causes: rootCauses,
    capa_recommendations: capa,
  } = analysis

  return (
    <div className="card insights">
      <div className="card-head">
        <div>
          <h2>
            <span style={{ color: 'var(--ai-600)' }}>✦</span> AI Analysis
          </h2>
          <p>Risk, duplicates, root cause and CAPA for this complaint</p>
        </div>
      </div>

      <div className="card-body">
        <div className="insight-grid">
          <div className="stat">
            <div className="k">Risk Classification</div>
            <div className="v" style={{ color: riskColor(riskLevel) }}>
              {riskLevel ?? '—'}
            </div>
            <div className="sub">{riskScore ?? '—'} / 100</div>
            <div className="meter">
              <span style={{ width: `${riskScore ?? 0}%`, background: riskColor(riskLevel) }} />
            </div>
          </div>

          <div className="stat">
            <div className="k">Completeness</div>
            <div className="v" style={{ color: completenessColor(completeness ?? 0) }}>
              {completeness ?? '—'}%
            </div>
            <div className="sub">
              {missing?.length ? `${missing.length} field(s) outstanding` : 'All fields captured'}
            </div>
            <div className="meter">
              <span
                style={{
                  width: `${completeness ?? 0}%`,
                  background: completenessColor(completeness ?? 0),
                }}
              />
            </div>
          </div>

          <div className="stat">
            <div className="k">Regulatory</div>
            <div className="v" style={{ color: reportable ? '#b91c1c' : '#15803d', fontSize: 17 }}>
              {reportable ? 'Reportable' : 'Not reportable'}
            </div>
            <div className="sub">
              {reportable
                ? 'Assess expedited reporting (e.g. Field Alert)'
                : 'No expedited trigger identified'}
            </div>
          </div>

          <div className="stat">
            <div className="k">Duplicates</div>
            <div className="v" style={{ color: duplicates?.length ? '#b45309' : '#15803d' }}>
              {duplicates?.length ?? 0}
            </div>
            <div className="sub">
              {duplicates?.length ? 'Possible repeat of an open complaint' : 'No matches in register'}
            </div>
          </div>
        </div>

        {summary && (
          <div className="insight-block">
            <h3>📄 Complaint Summary</h3>
            <p>{summary}</p>
          </div>
        )}

        {riskRationale && (
          <div className="insight-block">
            <h3>
              ⚠ Risk Rationale
              <span className={`badge ${riskTone(riskLevel)}`}>{riskLevel}</span>
            </h3>
            <p>{riskRationale}</p>
          </div>
        )}

        {completenessNotes && (
          <div className="insight-block">
            <h3>☑ Completeness Check</h3>
            <p>{completenessNotes}</p>
            {missing?.length > 0 && (
              <div className="missing-tags">
                {missing.map((field) => (
                  <span key={field} className="badge badge-warn">
                    {field}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {duplicates?.length > 0 && (
          <div className="insight-block">
            <h3>⧉ Possible Duplicates</h3>
            <ul className="dup-list">
              {duplicates.map((dup) => (
                <li key={dup.complaint_number}>
                  <strong>{dup.complaint_number}</strong>
                  <span style={{ flex: 1 }}>{dup.reason}</span>
                  <span className="badge badge-warn">{Math.round(dup.similarity * 100)}% match</span>
                  {onOpenDuplicate && dup.complaint_id && (
                    <button
                      type="button"
                      className="chip"
                      onClick={() => onOpenDuplicate(dup.complaint_id)}
                    >
                      Open
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {rootCauses?.length > 0 && (
          <div className="insight-block">
            <h3>🔍 Probable Root Causes</h3>
            <p style={{ fontSize: 12, color: 'var(--ink-500)' }}>
              Hypotheses to investigate — not conclusions.
            </p>
            <RootCauseList causes={rootCauses} />
          </div>
        )}

        {capa?.length > 0 && (
          <div className="insight-block">
            <h3>🛠 Recommended CAPA Plan</h3>
            <CapaList actions={capa} />
          </div>
        )}

      </div>
    </div>
  )
}
