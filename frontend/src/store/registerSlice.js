import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const fetchComplaints = createAsyncThunk('register/list', (filters = {}) =>
  api.listComplaints(filters),
)
export const fetchStats = createAsyncThunk('register/stats', () => api.stats())
export const fetchComplaint = createAsyncThunk('register/get', (id) => api.getComplaint(id))
export const updateStatus = createAsyncThunk('register/status', ({ id, status }) =>
  api.updateComplaint(id, { status }),
)
export const removeComplaint = createAsyncThunk('register/remove', async (id) => {
  await api.deleteComplaint(id)
  return id
})

const registerSlice = createSlice({
  name: 'register',
  initialState: {
    items: [],
    stats: null,
    selected: null,
    filters: { q: '', status: '', severity: '' },
    listStatus: 'idle',
    detailStatus: 'idle',
    error: null,
  },
  reducers: {
    filterChanged: (state, action) => {
      state.filters[action.payload.name] = action.payload.value
    },
    selectionCleared: (state) => {
      state.selected = null
      state.detailStatus = 'idle'
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.listStatus = 'loading'
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.listStatus = 'ready'
        state.items = action.payload
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.listStatus = 'error'
        state.error = action.error.message
      })

      .addCase(fetchStats.fulfilled, (state, action) => {
        state.stats = action.payload
      })

      .addCase(fetchComplaint.pending, (state) => {
        state.detailStatus = 'loading'
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.detailStatus = 'ready'
        state.selected = action.payload
      })
      .addCase(fetchComplaint.rejected, (state, action) => {
        state.detailStatus = 'error'
        state.error = action.error.message
      })

      .addCase(updateStatus.fulfilled, (state, action) => {
        state.selected = action.payload
        const index = state.items.findIndex((c) => c.id === action.payload.id)
        if (index !== -1) state.items[index] = { ...state.items[index], status: action.payload.status }
      })

      .addCase(removeComplaint.fulfilled, (state, action) => {
        state.items = state.items.filter((c) => c.id !== action.payload)
        if (state.selected?.id === action.payload) state.selected = null
      })
  },
})

export const { filterChanged, selectionCleared } = registerSlice.actions
export default registerSlice.reducer
