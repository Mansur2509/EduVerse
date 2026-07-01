"use client";

import { useCallback, useEffect, useState } from "react";

type LeaveAction = () => void | Promise<unknown>;

export function useUnsavedChangesGuard({
  isDirty,
  browserMessage
}: {
  isDirty: boolean;
  browserMessage: string;
}) {
  const [pendingLeaveAction, setPendingLeaveAction] = useState<LeaveAction | null>(null);

  useEffect(() => {
    if (!isDirty) return;

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = browserMessage;
      return browserMessage;
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [browserMessage, isDirty]);

  const requestLeave = useCallback(
    (action: LeaveAction) => {
      if (!isDirty) {
        void action();
        return;
      }
      setPendingLeaveAction(() => action);
    },
    [isDirty]
  );

  const stay = useCallback(() => {
    setPendingLeaveAction(null);
  }, []);

  const leaveWithoutSaving = useCallback(async () => {
    const action = pendingLeaveAction;
    setPendingLeaveAction(null);
    await action?.();
  }, [pendingLeaveAction]);

  const clearPrompt = useCallback(() => {
    setPendingLeaveAction(null);
  }, []);

  return {
    clearPrompt,
    isPromptOpen: Boolean(pendingLeaveAction),
    leaveWithoutSaving,
    requestLeave,
    stay
  };
}
