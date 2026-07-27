export const COMPLAINT_SOURCES = [
  'Email',
  'Phone',
  'Customer Portal',
  'Field Alert',
  'Distributor',
  'Regulatory Body',
  'Sales Representative',
  'Other',
]

export const COMPLAINT_TYPES = [
  'Product Quality',
  'Packaging Defect',
  'Labelling Error',
  'Contamination',
  'Adverse Event',
  'Lack of Efficacy',
  'Appearance / Physical Defect',
  'Quantity / Shortage',
  'Documentation Discrepancy',
  'Other',
]

export const SEVERITIES = ['Critical', 'Major', 'Minor']
export const PRIORITIES = ['P1 - Urgent', 'P2 - High', 'P3 - Medium', 'P4 - Low']
export const STATUSES = [
  'Pending Triage',
  'Under Investigation',
  'CAPA Assigned',
  'Closed',
  'Rejected',
]
export const UNITS = ['kg', 'g', 'mg', 'units', 'tablets', 'vials', 'bottles', 'strips', 'L', 'mL']

export const riskTone = (level) =>
  ({ Critical: 'badge-risk', High: 'badge-warn', Medium: 'badge-info', Low: 'badge-ok' })[level] ??
  'badge-neutral'

export const severityTone = (severity) =>
  ({ Critical: 'badge-risk', Major: 'badge-warn', Minor: 'badge-neutral' })[severity] ??
  'badge-neutral'

export const statusTone = (status) =>
  ({
    'Pending Triage': 'badge-warn',
    'Under Investigation': 'badge-info',
    'CAPA Assigned': 'badge-brand',
    Closed: 'badge-ok',
    Rejected: 'badge-neutral',
  })[status] ?? 'badge-neutral'

export const riskColor = (level) =>
  ({ Critical: '#b91c1c', High: '#b45309', Medium: '#0369a1', Low: '#15803d' })[level] ?? '#64748b'
