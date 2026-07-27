import { configureStore } from '@reduxjs/toolkit'
import intakeReducer from './intakeSlice'
import registerReducer from './registerSlice'

export const store = configureStore({
  reducer: {
    intake: intakeReducer,
    register: registerReducer,
  },
})
