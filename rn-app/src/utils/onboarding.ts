import './onboarding-storage';

// One device-local preference, versioned separately from measurement data.
const completionKey = 'kintra.knee-guide.v1.completed';
let completedThisLaunch = false;

export function hasCompletedOnboarding() {
  if (completedThisLaunch) return true;
  try {
    return globalThis.localStorage.getItem(completionKey) === 'true';
  } catch {
    return false;
  }
}

export function completeOnboarding() {
  completedThisLaunch = true;
  try {
    globalThis.localStorage.setItem(completionKey, 'true');
  } catch {
    // A blocked/full local store must not prevent entry into the app.
    // Completion still lasts for this launch; the guide may recur next launch.
  }
}
