import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api, streamExtraction } from '../api/client'

export const EMPTY_FORM = {
  complaint_source: '',
  customer_name: '',
  customer_contact: '',
  product_name: '',
  product_strength: '',
  batch_number: '',
  manufacturing_date: '',
  expiry_date: '',
  quantity_affected: '',
  quantity_unit: 'kg',
  complaint_type: '',
  complaint_date: '',
  description: '',
  severity: '',
  priority: '',
}

/** Coerce the agent's payload into the shape the controlled form expects. */
function toFormValues(extracted) {
  const next = { ...EMPTY_FORM }
  for (const key of Object.keys(EMPTY_FORM)) {
    const value = extracted?.[key]
    if (value !== undefined && value !== null && value !== '') next[key] = String(value)
  }
  return next
}

export const fetchCapabilities = createAsyncThunk('intake/capabilities', () => api.capabilities())

export const runExtraction = createAsyncThunk(
  'intake/run',
  async ({ file, text, filename }, { dispatch, rejectWithValue }) => {
    try {
      let result = null
      await streamExtraction({
        file,
        text,
        filename,
        onEvent: (event, data) => {
          if (event === 'node') dispatch(nodeCompleted(data))
          else if (event === 'result') result = data
          else if (event === 'error') throw new Error(data.message)
        },
      })
      if (!result) throw new Error('The agent finished without returning a result.')
      return result
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

export const askAssistant = createAsyncThunk(
  'intake/ask',
  async ({ message, complaintId, contextText, history }, { rejectWithValue }) => {
    try {
      return await api.chat({
        message,
        complaint_id: complaintId ?? null,
        context_text: contextText ?? null,
        history: history ?? [],
      })
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

export const saveComplaint = createAsyncThunk(
  'intake/save',
  async (_, { getState, rejectWithValue }) => {
    const { form, analysis, rawText, filename } = getState().intake

    const payload = { analysis, source_text: rawText || null, source_filename: filename || null }
    for (const [key, value] of Object.entries(form)) {
      if (value === '' || value == null) continue
      payload[key] = key === 'quantity_affected' ? Number(value) : value
    }

    try {
      return await api.createComplaint(payload)
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

const GREETING = {
  role: 'assistant',
  content:
    'Upload a complaint document or paste the text above. I will extract the details, populate the form, and assess risk, completeness, duplicates, root cause and CAPA.',
}

const initialState = {
  form: { ...EMPTY_FORM },
  analysis: null,
  rawText: '',
  filename: null,

  status: 'idle', // idle | extracting | ready | error
  progress: 0,
  currentNode: null,
  completedNodes: [],
  error: null,

  saveStatus: 'idle',
  saveError: null,
  savedComplaint: null,

  capabilities: null,
  messages: [GREETING],
  chatPending: false,
}

const intakeSlice = createSlice({
  name: 'intake',
  initialState,
  reducers: {
    fieldChanged: (state, action) => {
      const { name, value } = action.payload
      state.form[name] = value
    },
    nodeCompleted: (state, action) => {
      const { label, progress, node } = action.payload
      state.progress = progress
      state.currentNode = label
      state.completedNodes.push({ node, label })
    },
    resetForm: (state) => {
      state.form = { ...EMPTY_FORM }
      state.analysis = null
      state.rawText = ''
      state.filename = null
      state.status = 'idle'
      state.progress = 0
      state.currentNode = null
      state.completedNodes = []
      state.error = null
      state.saveStatus = 'idle'
      state.saveError = null
      state.savedComplaint = null
      state.messages = [GREETING]
    },
    dismissSaved: (state) => {
      state.savedComplaint = null
      state.saveStatus = 'idle'
    },
    messageAdded: (state, action) => {
      state.messages.push(action.payload)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCapabilities.fulfilled, (state, action) => {
        state.capabilities = action.payload
      })

      .addCase(runExtraction.pending, (state, action) => {
        state.status = 'extracting'
        state.progress = 0
        state.currentNode = 'Reading document'
        state.completedNodes = []
        state.error = null
        state.analysis = null
        state.filename = action.meta.arg.file?.name ?? action.meta.arg.filename ?? null
      })
      .addCase(runExtraction.fulfilled, (state, action) => {
        const { form, analysis, raw_text: rawText, filename } = action.payload
        state.form = toFormValues(form)
        state.analysis = analysis
        state.rawText = rawText
        state.filename = filename ?? state.filename
        state.status = 'ready'
        state.progress = 100
        state.currentNode = null

        const populated = Object.keys(analysis.extracted_fields ?? {}).length
        state.messages.push({
          role: 'assistant',
          content:
            `I extracted ${populated} field${populated === 1 ? '' : 's'} and populated the form. ` +
            `Risk is ${analysis.risk_level ?? 'unassessed'} (${analysis.risk_score ?? '–'}/100) and the record is ` +
            `${analysis.completeness_score ?? '–'}% complete. Review the highlighted fields, then ask me anything about this complaint.`,
        })
      })
      .addCase(runExtraction.rejected, (state, action) => {
        state.status = 'error'
        state.progress = 0
        state.currentNode = null
        state.error = action.payload ?? action.error.message
      })

      .addCase(askAssistant.pending, (state) => {
        state.chatPending = true
      })
      .addCase(askAssistant.fulfilled, (state, action) => {
        state.chatPending = false
        state.messages.push({ role: 'assistant', content: action.payload.reply })
      })
      .addCase(askAssistant.rejected, (state, action) => {
        state.chatPending = false
        state.messages.push({
          role: 'assistant',
          content: `I couldn't answer that: ${action.payload ?? action.error.message}`,
        })
      })

      .addCase(saveComplaint.pending, (state) => {
        state.saveStatus = 'saving'
        state.saveError = null
      })
      .addCase(saveComplaint.fulfilled, (state, action) => {
        state.saveStatus = 'saved'
        state.savedComplaint = action.payload
      })
      .addCase(saveComplaint.rejected, (state, action) => {
        state.saveStatus = 'error'
        state.saveError = action.payload ?? action.error.message
      })
  },
})

export const { fieldChanged, nodeCompleted, resetForm, dismissSaved, messageAdded } =
  intakeSlice.actions
export default intakeSlice.reducer
