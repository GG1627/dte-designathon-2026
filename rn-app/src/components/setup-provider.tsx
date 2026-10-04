import { createContext, use, useState, type ReactNode, type Dispatch, type SetStateAction } from 'react';
import { createMockSetup, type SetupData } from '@/data/setup';
const SetupContext = createContext<{ setup: SetupData; setSetup: Dispatch<SetStateAction<SetupData>> } | null>(null);
export function SetupProvider({ children }: { children: ReactNode }) {
  const [setup, setSetup] = useState(createMockSetup);
  return <SetupContext value={{ setup, setSetup }}>{children}</SetupContext>;
}
export function useSetup() {
  const state = use(SetupContext);
  if (!state) throw new Error('SetupProvider is required');
  return state;
}
