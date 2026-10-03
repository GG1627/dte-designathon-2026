import { createContext, use, useState, type ReactNode } from 'react';
import { devices, type Joint } from '@/data/demo';

type DemoState = {
  online: Record<string, boolean>;
  setOnline: (id: string, value: boolean) => void;
  placementChecked: string[];
  checkPlacement: (id: string) => void;
};
const DemoContext = createContext<DemoState | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [online, setOnlineState] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(devices.map((device) => [device.id, true])),
  );
  const [placementChecked, setPlacementChecked] = useState<string[]>([]);
  return (
    <DemoContext
      value={{
        online,
        setOnline: (id, value) =>
          setOnlineState((current) => ({ ...current, [id]: value })),
        placementChecked,
        checkPlacement: (id) =>
          setPlacementChecked((current) =>
            current.includes(id) ? current : [...current, id],
          ),
      }}>
      {children}
    </DemoContext>
  );
}

export function useDemo() {
  const state = use(DemoContext);
  if (!state) throw new Error('DemoProvider is required');
  return state;
}

export function isOnline(joint: Joint, online: Record<string, boolean>) {
  return joint.monitored && joint.devices.every((id) => online[id]);
}
