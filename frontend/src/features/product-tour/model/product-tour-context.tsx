"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

import { useAuth } from "@/features/auth";

type ProductTourContextValue = {
  isOpen: boolean;
  dismiss: () => void;
  reopen: () => void;
};

const ProductTourContext = createContext<ProductTourContextValue | null>(null);

export function ProductTourProvider({ children }: { children: ReactNode }) {
  const { user, updateUser } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (user && !user.product_tour_dismissed) {
      setIsOpen(true);
    }
  }, [user]);

  const dismiss = useCallback(() => {
    setIsOpen(false);
    // Best-effort: the modal must not reappear this session even if the
    // network write fails, so the local close always happens first above.
    void updateUser({ product_tour_dismissed: true }).catch(() => {});
  }, [updateUser]);

  const reopen = useCallback(() => {
    setIsOpen(true);
  }, []);

  const value = useMemo<ProductTourContextValue>(
    () => ({ isOpen, dismiss, reopen }),
    [isOpen, dismiss, reopen]
  );

  return <ProductTourContext.Provider value={value}>{children}</ProductTourContext.Provider>;
}

export function useProductTour() {
  const context = useContext(ProductTourContext);
  if (!context) {
    throw new Error("useProductTour must be used within ProductTourProvider.");
  }
  return context;
}
