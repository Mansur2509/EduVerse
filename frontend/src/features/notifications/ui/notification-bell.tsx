"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import type { Notification } from "@/entities/notification";
import {
  getNotificationsRequest,
  getNotificationUnreadCountRequest,
  markAllNotificationsReadRequest,
  updateNotificationStatusRequest
} from "@/features/notifications";
import { useI18n } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { AppIcon } from "@/shared/ui/icon";

const DROPDOWN_ITEM_LIMIT = 8;

export function NotificationBell() {
  const { locale, t } = useI18n();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  // Tracked separately from `notifications.length`: the dropdown list is
  // capped at DROPDOWN_ITEM_LIMIT for display, but the badge must reflect
  // the real total (the paginated envelope's `count`), not the slice size.
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadCount = useCallback(async () => {
    try {
      const response = await getNotificationUnreadCountRequest();
      setUnreadCount(response.count);
    } catch {
      // A failed background fetch shouldn't break the shell chrome -- the
      // bell just keeps showing its last-known count until the next attempt.
    }
  }, []);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getNotificationsRequest({ status: "unread" });
      setNotifications(response.results.slice(0, DROPDOWN_ITEM_LIMIT));
      setUnreadCount(response.count);
    } catch {
      // Same as loadCount: keep showing the last-known state.
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Mount only needs the cheap count for the badge -- the full item list
    // is fetched lazily when the dropdown is actually opened.
    void loadCount();
  }, [loadCount]);

  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleOpen = () => {
    setIsOpen((current) => {
      const next = !current;
      if (next) void load();
      return next;
    });
  };

  const handleItemClick = async (notification: Notification) => {
    setNotifications((current) => current.filter((item) => item.id !== notification.id));
    setUnreadCount((current) => Math.max(0, current - 1));
    setIsOpen(false);
    try {
      await updateNotificationStatusRequest(notification.id, "read");
    } catch {
      void loadCount();
    }
  };

  const handleMarkAllRead = async () => {
    setNotifications([]);
    setUnreadCount(0);
    try {
      await markAllNotificationsReadRequest();
    } catch {
      void loadCount();
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        aria-controls="notification-bell-panel"
        aria-expanded={isOpen}
        aria-label={t("notifications.bell.ariaLabel")}
        className="relative grid size-10 place-items-center rounded-sm border text-muted-foreground transition-colors hover:border-primary/35 hover:text-foreground"
        onClick={toggleOpen}
        title={t("notifications.bell.ariaLabel")}
        type="button"
      >
        <AppIcon icon={Bell} />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-danger text-[0.6rem] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          className="absolute right-0 top-full z-40 mt-2 w-80 max-w-[90vw] rounded-sm border bg-card shadow-card"
          id="notification-bell-panel"
        >
          <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {t("notifications.bell.title")}
            </p>
            {unreadCount > 0 ? (
              <button
                className="text-xs font-semibold text-primary-hover hover:underline"
                onClick={() => void handleMarkAllRead()}
                type="button"
              >
                {t("notifications.bell.markAllRead")}
              </button>
            ) : null}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {isLoading ? (
              <p className="px-3 py-4 text-xs text-muted-foreground">{t("notifications.bell.loading")}</p>
            ) : notifications.length === 0 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground">{t("notifications.bell.empty")}</p>
            ) : (
              <ul>
                {notifications.map((notification) => (
                  <li className="border-b last:border-b-0" key={notification.id}>
                    <Link
                      className="block px-3 py-2.5 hover:bg-elevated"
                      href={notification.action_url || "/notifications"}
                      onClick={() => void handleItemClick(notification)}
                    >
                      <p className="line-clamp-2 text-sm font-semibold leading-5">{notification.title}</p>
                      <p className="mt-1 text-[0.68rem] text-muted-foreground">
                        {formatDateTime(notification.created_at, locale)}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Link
            className="block border-t px-3 py-2 text-center text-xs font-semibold text-primary-hover hover:underline"
            href="/notifications"
            onClick={() => setIsOpen(false)}
          >
            {t("notifications.bell.viewAll")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
